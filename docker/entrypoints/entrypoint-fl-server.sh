#!/bin/bash
# Entrypoint script for FL Server container

# Make script more error-tolerant for critical sections
set -e  # Exit on errors initially (for setup)
trap 'echo "Error on line $LINENO"; exit 1' ERR

# Setup logging
LOGS_DIR="/app/logs"
mkdir -p "$LOGS_DIR"
LOG_FILE="$LOGS_DIR/fl-server.log"
touch $LOG_FILE
chmod 777 "$LOG_FILE"
chmod -R 777 /app/logs

# Make script more tolerant to errors after initial setup
set +e

# Log function
log() {
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  local level=${1:-INFO}
  local message=$2
  if [ "$#" -eq 1 ]; then
    message=$level
    level="INFO"
  fi
  echo "[$timestamp] [FL-SERVER] [$level] $message" | tee -a "$LOG_FILE"
}

# Function to check if an IP is valid (not empty, not loopback, not link-local)
is_valid_ip() {
  local ip="$1"
  # Check if IP is empty
  if [ -z "$ip" ]; then
    return 1
  fi
  
  # Check if IP is loopback (127.x.x.x)
  if [[ "$ip" =~ ^127\. ]]; then
    return 1
  fi
  
  # Check if IP is link-local (169.254.x.x)
  if [[ "$ip" =~ ^169\.254\. ]]; then
    return 1
  fi
  
  return 0
}

# Validation function for IP addresses
validate_ip() {
  local ip=$1
  if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    IFS='.' read -r -a segments <<< "$ip"
    for segment in "${segments[@]}"; do
      if (( segment > 255 )); then
        return 1
      fi
    done
    return 0
  else
    return 1
  fi
}

# Function to update hosts file
update_hosts_entry() {
  local ip=$1
  local hostname=$2
  
  # Skip if IP is invalid
  if ! validate_ip "$ip"; then
    log "WARNING" "Invalid IP for hosts entry: $ip, skipping"
    return 1
  fi
  
  # Create a temp file for hosts updates to avoid "device busy" errors
  TEMP_HOSTS=$(mktemp)
  
  # Check if entry already exists with exact match
  if grep -q "^$ip[[:space:]].*$hostname\($\|[[:space:]]\)" /etc/hosts; then
    # Entry exists with this IP and hostname, do nothing
    log "INFO" "Hosts entry already exists for $hostname -> $ip"
    rm -f "$TEMP_HOSTS"
    return 0
  fi
  
  # Remove any existing entries for this hostname
  grep -v "[[:space:]]$hostname\($\|[[:space:]]\)" /etc/hosts > "$TEMP_HOSTS"
  
  # Add the new entry
  echo "$ip $hostname" >> "$TEMP_HOSTS"
  
  # Replace the hosts file atomically
  cat "$TEMP_HOSTS" > /etc/hosts
  
  # Clean up
  rm -f "$TEMP_HOSTS"
  
  log "Added/updated hosts entry: $ip -> $hostname"
  return 0
}

# Function to find container's IP address
get_container_ip() {
  local interface="${1:-eth0}"
  local network_mode="${2:-docker}"
  
  # Return only the first IP address with no additional output
  if [ "$network_mode" = "host" ]; then
    # In host mode, use the loopback interface
    ip -4 addr show lo | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v "127.0.0.1" | head -n 1 | tr -d '\n'
  else
    # In container mode, get the primary interface IP
    ip -4 addr show $interface 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n 1 | tr -d '\n'
  fi
}

# IP handling function to safely assign IPs
assign_ip() {
  local ip=$1
  local interface=$2
  local subnet=${3:-24}
  
  # First try to remove any existing IPs with error suppression
  existing_ip=$(ip -4 addr show $interface 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
  if [ -n "$existing_ip" ] && [ "$existing_ip" != "127.0.0.1" ]; then
    log "Removing existing IP $existing_ip from $interface"
    { ip addr del $existing_ip/16 dev $interface; } 2>/dev/null || { ip addr del $existing_ip/24 dev $interface; } 2>/dev/null || true
  fi
  
  # Then add the new IP with error suppression
  log "Adding IP $ip/$subnet to $interface"
  { ip addr add $ip/$subnet dev $interface; } 2>/dev/null || { ip address add $ip/$subnet dev $interface; } 2>/dev/null || {
    log "ERROR" "Failed to assign IP $ip to $interface, trying alternative method"
    # Last resort, try with ip command with different syntax
    eval "ip addr add $ip/$subnet dev $interface" 2>/dev/null || eval "ip addr add $ip/$subnet dev '$interface'" 2>/dev/null || 
    log "CRITICAL" "All methods to assign IP $ip to $interface failed"
    return 1
  }
  
  # Make sure interface is up
  log "Setting $interface up"
  { ip link set $interface up; } 2>/dev/null || { ip link set dev $interface up; } 2>/dev/null || {
    log "WARNING" "Failed to bring up $interface"
    return 1
  }
  
  return 0
}

# Function to wait for service with timeout and fallback
wait_for_service() {
  local service="$1"
  local url="$2"
  local timeout="${3:-10}"
  local max_retries="${4:-5}"
  local required="${5:-false}"
  local retry=0
  local wait_time=2
  
  log "INFO" "Waiting for $service at $url (timeout: ${timeout}s, required: $required)"
  
  while [ $retry -lt $max_retries ]; do
    if curl -s -m "$timeout" -o /dev/null "$url"; then
      log "SUCCESS" "$service is available at $url"
      return 0
    fi
    
    retry=$((retry + 1))
    log "WARNING" "$service not available at $url (attempt $retry/$max_retries)"
    
    # Exponential backoff
    wait_time=$((wait_time * 2))
    sleep $wait_time
  done
  
  if [ "$required" = "true" ]; then
    log "ERROR" "$service not available after $max_retries attempts. This service is required."
    return 1
  else
    log "WARNING" "$service not available after $max_retries attempts. Continuing without it."
    return 0
  fi
}

# Add the function to fetch a fallback model for training
fetch_fallback_model() {
  local model_dir="$1"
  
  # Create the model directory if it doesn't exist
  mkdir -p "$model_dir"
  
  log "INFO" "Setting up a fallback model for FL training"
  
  # Simple model for testing purposes - creates a JSON file with model description
  cat > "$model_dir/fallback_model.json" << EOF
{
  "model_type": "fallback",
  "description": "Simple fallback model for testing",
  "parameters": {
    "learning_rate": 0.01,
    "momentum": 0.9,
    "batch_size": 32
  },
  "layers": [
    {"type": "input", "shape": [28, 28, 1]},
    {"type": "conv2d", "filters": 32, "kernel_size": 3},
    {"type": "max_pooling2d", "pool_size": 2},
    {"type": "flatten"},
    {"type": "dense", "units": 10, "activation": "softmax"}
  ]
}
EOF
  
  log "SUCCESS" "Created fallback model at $model_dir/fallback_model.json"
}

log "Starting FL Server entrypoint script"

# Get container information
HOSTNAME=${HOSTNAME:-$(hostname)}
CONTAINER_ID=$(cat /etc/hostname)

# Set default values for environment variables
: "${SERVICE_TYPE:=fl-server}"
: "${SERVICE_ID:=fl-server-1}"
: "${HOST:=0.0.0.0}"
: "${SERVER_PORT:=8080}"
: "${METRICS_PORT:=9090}"
: "${LOG_LEVEL:=INFO}"
: "${NETWORK_MODE:=docker}"
: "${GNS3_NETWORK:=false}"
: "${USE_STATIC_IP:=false}"
: "${WAIT_FOR_SERVICES_TIMEOUT:=30}"
: "${MIN_CLIENTS:=2}"
: "${MIN_AVAILABLE_CLIENTS:=2}"
: "${ROUNDS:=10}"
: "${STRICT_POLICY_MODE:=false}"
: "${POLICY_ENGINE_PORT:=5000}" # Default Policy Engine port
: "${WAIT_FOR_POLICY_ENGINE:=true}"
: "${STAY_ALIVE_AFTER_TRAINING:=true}" # Default to staying alive after training

log "Service type: $SERVICE_TYPE"
log "Service ID: $SERVICE_ID"
log "Logging level: $LOG_LEVEL"
log "Network mode: $NETWORK_MODE"
log "GNS3 network: $GNS3_NETWORK"
log "Static IP mode: $USE_STATIC_IP"
log "FL Server host: $HOST"
log "FL Server port: $SERVER_PORT"
log "Metrics port: $METRICS_PORT"
log "Min clients: $MIN_CLIENTS"
log "Min available clients: $MIN_AVAILABLE_CLIENTS"
log "Rounds: $ROUNDS"
log "Stay alive after training: $STAY_ALIVE_AFTER_TRAINING"
log "Strict policy mode: $STRICT_POLICY_MODE"

# Get the appropriate server IP variable
SERVER_IP_VAR="NODE_IP_FL_SERVER"
SERVER_IP=${!SERVER_IP_VAR}

if [ -z "$SERVER_IP" ]; then
  log "WARNING" "No IP found for $SERVER_IP_VAR environment variable"
  log "INFO" "Will attempt to discover IP address"
fi

# Determine the interface to use
INTERFACE="eth0"
if [ -n "$NETWORK_INTERFACE" ]; then
  INTERFACE="$NETWORK_INTERFACE"
fi

# GNS3 specific or Static IP mode
# Trigger static IP assignment if USE_STATIC_IP is true
if [ "$USE_STATIC_IP" = "true" ]; then
  log "INFO" "Static IP mode enabled, performing special network initialization"
  
  # Determine the interface to use (default to eth0)
  TARGET_IFACE="eth0"
  if [ -n "$NETWORK_INTERFACE" ]; then
      TARGET_IFACE="$NETWORK_INTERFACE"
      log "INFO" "Using specified network interface: $TARGET_IFACE"
  else
      # Verify eth0 exists, otherwise try finding another eth interface
      if ! ip link show eth0 > /dev/null 2>&1; then
          log "WARNING" "Default interface eth0 not found, searching for another ethX..."
          FOUND_IFACE=$(ip link show | grep -oP '^\d+:\s+\Keth[0-9]+' | head -n 1)
          if [ -n "$FOUND_IFACE" ]; then
              TARGET_IFACE="$FOUND_IFACE"
              log "INFO" "Found alternative interface: $TARGET_IFACE"
          else
              log "ERROR" "Cannot find a suitable ethX interface. Exiting."
              exit 1
          fi
      else
          log "INFO" "Using default network interface: $TARGET_IFACE"
      fi
  fi
    
  # Check if we have a server IP to assign
  if [ -z "$SERVER_IP" ]; then
    log "ERROR" "USE_STATIC_IP is true, but NODE_IP_FL_SERVER is not set. Cannot assign static IP."
    exit 1
  fi
  
  # Ensure interface is up
  log "INFO" "Bringing up interface $TARGET_IFACE..."
  ip link set "$TARGET_IFACE" up || {
      log "ERROR" "Failed to bring up interface $TARGET_IFACE. Exiting."
      exit 1
  }
  
  # Flush existing IP addresses from the interface
  log "INFO" "Flushing existing IP addresses from $TARGET_IFACE..."
  ip addr flush dev "$TARGET_IFACE" scope global || log "WARNING" "Failed to flush interface $TARGET_IFACE (may have had no IP)"
  sleep 1 # Give a moment for the flush to settle
  
  # Simple static IP assignment
  log "INFO" "Assigning static IP $SERVER_IP/24 to $TARGET_IFACE"
  if assign_ip "$SERVER_IP" "$TARGET_IFACE"; then
    log "SUCCESS" "IP assignment succeeded"
    MY_IP="$SERVER_IP"
    
    # Set up routing if we have a valid IP
    IFS='.' read -r -a IP_PARTS <<< "$MY_IP"
    SUBNET="${IP_PARTS[0]}.${IP_PARTS[1]}.${IP_PARTS[2]}"
    log "INFO" "Subnet: $SUBNET.0/24"
    
    # Set up routes properly
    if ! ip route | grep -q "default"; then
      log "INFO" "Setting up default route via $SUBNET.1"
      ip route add default via $SUBNET.1 dev "$TARGET_IFACE" || log "WARNING" "Failed to add default route"
    fi
    
    # Try to ping gateway to verify connectivity
    if ping -c 1 -W 2 $SUBNET.1 >/dev/null 2>&1; then
      log "SUCCESS" "Network gateway at $SUBNET.1 is reachable"
    else 
      log "WARNING" "Cannot ping gateway at $SUBNET.1"
    fi
  else
    log "ERROR" "Static IP assignment failed for $SERVER_IP on $TARGET_IFACE. Exiting."
    exit 1
  fi
else
  # Standard Docker network mode or dynamic IP
  log "INFO" "Using dynamic IP discovery"
  INTERFACE="eth0" # Default to eth0 for dynamic
  MY_IP=$(get_container_ip "$INTERFACE" "$NETWORK_MODE")
  log "INFO" "Detected IP address: $MY_IP on $INTERFACE"
  
  # Validate the discovered IP
  if ! is_valid_ip "$MY_IP"; then
    log "ERROR" "Invalid IP address detected: $MY_IP"
    # Try another method to get a valid IP
    MY_IP=$(hostname -I | awk '{print $1}')
    if ! is_valid_ip "$MY_IP"; then
      log "CRITICAL" "Failed to obtain a valid dynamic IP address. Exiting."
      exit 1
    else
      log "INFO" "Obtained alternative dynamic IP: $MY_IP"
    fi
  fi
fi

log "Using IP address: $MY_IP"

# Update hosts entries for well-known services
# This helps containers find each other by hostname
if [ -n "$NODE_IP_FL_SERVER" ]; then
  update_hosts_entry "$NODE_IP_FL_SERVER" "fl-server"
fi

if [ -n "$NODE_IP_POLICY_ENGINE" ]; then
  update_hosts_entry "$NODE_IP_POLICY_ENGINE" "policy-engine"
fi

if [ -n "$NODE_IP_COLLECTOR" ]; then
  update_hosts_entry "$NODE_IP_COLLECTOR" "metrics-collector"
fi

if [ -n "$NODE_IP_SDN_CONTROLLER" ]; then
  update_hosts_entry "$NODE_IP_SDN_CONTROLLER" "sdn-controller"
fi

# Create necessary directories
mkdir -p /app/logs
mkdir -p /app/config/fl_server
mkdir -p /app/data/models
mkdir -p /app/data/results
chmod -R 777 /app/logs
chmod -R 777 /app/config
chmod -R 777 /app/data

# Setup Python environment
export PYTHONUNBUFFERED=1
export PYTHONPATH=$PYTHONPATH:/app

# Get the CONFIG_DIR from environment or use default
CONFIG_DIR=${CONFIG_DIR:-"/app/config"}
SERVER_CONFIG_DIR=${SERVER_CONFIG_DIR:-"${CONFIG_DIR}/fl_server"}
mkdir -p "$SERVER_CONFIG_DIR"

# Dynamic config generation
GENERATED_CONFIG_PATH="${SERVER_CONFIG_DIR}/server_config.json"
log "INFO" "Generating dynamic server configuration at $GENERATED_CONFIG_PATH"

# Create a temporary config file for building
TEMP_CONFIG_FILE=$(mktemp)

# Start building the JSON configuration
cat > "$TEMP_CONFIG_FILE" << EOF
{
  "server_id": "${SERVICE_ID}",
  "host": "${HOST}",
  "port": ${SERVER_PORT},
  "min_clients": ${MIN_CLIENTS},
  "min_available_clients": ${MIN_AVAILABLE_CLIENTS},
  "log_level": "${LOG_LEVEL}",
  "log_file": "${LOG_FILE}",
  "data_dir": "${DATA_DIR}",
  "strict_policy_mode": ${STRICT_POLICY_MODE}
}
EOF

# Add known hostnames from environment variables
if [ -n "$POLICY_ENGINE_HOST" ]; then
  log "INFO" "Adding policy_engine_host: $POLICY_ENGINE_HOST to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg k "policy_engine_host" --arg v "$POLICY_ENGINE_HOST" '. + {($k): $v}' "$TEMP_CONFIG_FILE" > "${TEMP_CONFIG_FILE}.tmp" && mv "${TEMP_CONFIG_FILE}.tmp" "$TEMP_CONFIG_FILE"
  else
    sed -i '$ s/}$/,\n  "policy_engine_host": "'"$POLICY_ENGINE_HOST"'"\n}/' "$TEMP_CONFIG_FILE"
  fi
fi

if [ -n "$COLLECTOR_HOST" ] || [ -n "$NODE_IP_COLLECTOR" ]; then
  COLLECTOR_HOSTNAME=${COLLECTOR_HOST:-"metrics-collector"}
  log "INFO" "Adding collector_host: $COLLECTOR_HOSTNAME to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg k "collector_host" --arg v "$COLLECTOR_HOSTNAME" '. + {($k): $v}' "$TEMP_CONFIG_FILE" > "${TEMP_CONFIG_FILE}.tmp" && mv "${TEMP_CONFIG_FILE}.tmp" "$TEMP_CONFIG_FILE"
  else
    sed -i '$ s/}$/,\n  "collector_host": "'"$COLLECTOR_HOSTNAME"'"\n}/' "$TEMP_CONFIG_FILE"
  fi
fi

# Add FL server IP to configuration
if [ -n "$CLEAN_IP" ]; then
  if command -v jq >/dev/null 2>&1; then
    jq --arg ip "$CLEAN_IP" '. + {"server_ip": $ip}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp"
    if [ $? -eq 0 ]; then
      mv "$TEMP_CONFIG_FILE.tmp" "$TEMP_CONFIG_FILE"
    else
      log "ERROR" "Failed to add server_ip to config with jq"
    fi
  else
    # Fallback method without jq - use # as delimiter
    sed -i '$ s#}$#,"server_ip":"'"$CLEAN_IP"'"}#' "$TEMP_CONFIG_FILE"
  fi
fi

# Process NODE_IP_ variables
if command -v jq >/dev/null 2>&1; then
  # More reliable method using jq
  for var in $(env | grep "^NODE_IP_" | sort); do
    varname=$(echo "$var" | cut -d= -f1)
    ip_value=$(echo "$var" | cut -d= -f2)
    
    # Skip if invalid IP
    if ! validate_ip "$ip_value"; then
      log "WARNING" "Invalid IP in $varname: $ip_value, skipping"
      continue
    fi
    
    # Convert variable name to lowercase with underscores (node_ip_xxx)
    key="node_ip_$(echo "${varname#NODE_IP_}" | tr '[:upper:]' '[:lower:]' | tr '-' '_')"
    
    # Add to config with jq
    jq --arg k "$key" --arg v "$ip_value" '. + {($k): $v}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp"
    if [ $? -eq 0 ]; then
      mv "$TEMP_CONFIG_FILE.tmp" "$TEMP_CONFIG_FILE"
    else
      log "ERROR" "Failed to add $key to config with jq"
    fi
  done
else
  # Simple fallback without jq - use # as delimiter
  for var in $(env | grep "^NODE_IP_" | sort); do
    varname=$(echo "$var" | cut -d= -f1)
    ip_value=$(echo "$var" | cut -d= -f2)
    
    # Skip if invalid IP
    if ! validate_ip "$ip_value"; then
      log "WARNING" "Invalid IP in $varname: $ip_value, skipping"
      continue
    fi
    
    # Convert variable name to lowercase with underscores
    key="node_ip_$(echo "${varname#NODE_IP_}" | tr '[:upper:]' '[:lower:]' | tr '-' '_')"
    
    # Add to config - use # as delimiter
    sed -i '$ s#}$#,"'"$key"'":"'"$ip_value"'"}#' "$TEMP_CONFIG_FILE"
  done
fi

# Add any custom configuration environments with SERVER_CONFIG_ prefix
for var in $(env | grep "^SERVER_CONFIG_"); do
  key=$(echo "$var" | cut -d= -f1 | sed 's/^SERVER_CONFIG_//' | tr '[:upper:]' '[:lower:]')
  value=$(echo "$var" | cut -d= -f2)
  
  if command -v jq >/dev/null 2>&1; then
    # Try to determine if value is numeric, boolean, or string
    if [[ "$value" =~ ^[0-9]+$ ]]; then
      # Integer value - no quotes
      jq --arg k "$key" --arg v "$value" '. + {($k): ($v|tonumber)}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp"
    elif [[ "$value" =~ ^(true|false)$ ]]; then
      # Boolean value - no quotes
      jq --arg k "$key" --arg v "$value" '. + {($k): ($v=="true")}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp"
    else
      # String value - add quotes
      jq --arg k "$key" --arg v "$value" '. + {($k): $v}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp"
    fi
    
    if [ $? -eq 0 ]; then
      mv "$TEMP_CONFIG_FILE.tmp" "$TEMP_CONFIG_FILE"
    else
      log "ERROR" "Failed to add $key to config with jq"
    fi
  else
    # Simple fallback without jq - use # as delimiter
    if [[ "$value" =~ ^[0-9]+$ ]]; then
      # Integer value - no quotes
      sed -i '$ s#}$#,"'"$key"'":'"$value"'}#' "$TEMP_CONFIG_FILE"
    elif [[ "$value" =~ ^(true|false)$ ]]; then
      # Boolean value - no quotes
      sed -i '$ s#}$#,"'"$key"'":'"$value"'}#' "$TEMP_CONFIG_FILE"
    else
      # String value - add quotes
      sed -i '$ s#}$#,"'"$key"'":"'"$value"'"}#' "$TEMP_CONFIG_FILE"
    fi
  fi
done

# Initialize POLICY_URL variable
POLICY_URL=""

# Add policy engine URL to config - prefer hostname over IP
if [ -n "$POLICY_ENGINE_HOST" ]; then
  POLICY_ENGINE_PORT=${POLICY_ENGINE_PORT:-5000}
  POLICY_URL="http://$POLICY_ENGINE_HOST:${POLICY_ENGINE_PORT}"
  log "INFO" "Setting policy engine URL to $POLICY_URL using hostname"
elif [ -n "$NODE_IP_POLICY_ENGINE" ]; then
  POLICY_ENGINE_PORT=${POLICY_ENGINE_PORT:-5000}
  POLICY_URL="http://$NODE_IP_POLICY_ENGINE:${POLICY_ENGINE_PORT}"
  log "INFO" "Setting policy engine URL to $POLICY_URL using IP address"
else
  log "WARNING" "No policy engine host or IP found, policy checks may not work"
fi

# Add to config if we have a URL
if [ -n "$POLICY_URL" ]; then
  # Add to config
  if command -v jq >/dev/null 2>&1; then
    jq --arg url "$POLICY_URL" '. + {"policy_engine_url": $url}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp"
    if [ $? -eq 0 ]; then
      mv "$TEMP_CONFIG_FILE.tmp" "$TEMP_CONFIG_FILE"
    else
      log "ERROR" "Failed to add policy_engine_url to config with jq"
    fi
  else
    # Fallback without jq - use # as delimiter
    sed -i '$ s#}$#,"policy_engine_url":"'"$POLICY_URL"'"}#' "$TEMP_CONFIG_FILE"
  fi
  
  # Wait for policy engine to be available
  log "INFO" "Waiting for Policy Engine to be available at $POLICY_URL"
  POLICY_HEALTH_URL="$POLICY_URL/health" # Use /health endpoint
  
  retry_count=0
  max_retries=10
  
  while [ $retry_count -lt $max_retries ]; do
    log "DEBUG" "Checking Policy Engine health at $POLICY_HEALTH_URL (Attempt $((retry_count + 1))/$max_retries)"
    # Use curl with a timeout and fail-fast option
    if curl --connect-timeout 5 -s -f "$POLICY_HEALTH_URL" > /dev/null 2>&1; then
      log "SUCCESS" "Policy Engine is available at $POLICY_HEALTH_URL"
      break
    else
      log "INFO" "Policy Engine not available yet at $POLICY_HEALTH_URL, retrying in 5 seconds... ($((retry_count + 1))/$max_retries)"
      sleep 5
      retry_count=$((retry_count + 1))
    fi
  done
  
  if [ $retry_count -eq $max_retries ]; then
    log "WARNING" "Policy Engine not available after $max_retries attempts, continuing anyway"
    # Depending on strict mode, we might exit later in the Python script
  fi
fi

# Final validation of the config
if command -v jq >/dev/null 2>&1; then
  if ! jq . "$TEMP_CONFIG_FILE" > /dev/null 2>&1; then
    log "ERROR" "Final JSON config is invalid. Dumping content:"
    cat "$TEMP_CONFIG_FILE" | tee -a "$LOG_FILE"
    log "ERROR" "Using simplified fallback format."
    # If JSON is invalid, try to create a simple valid JSON
    echo "{}" > "$TEMP_CONFIG_FILE"
    
    # Add essential parameters
    jq --arg id "${SERVICE_ID}" '. + {"service_id": $id}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp" && mv "$TEMP_CONFIG_FILE.tmp" "$TEMP_CONFIG_FILE"
    jq --arg host "${HOST:-"0.0.0.0"}" '. + {"host": $host}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp" && mv "$TEMP_CONFIG_FILE.tmp" "$TEMP_CONFIG_FILE"
    jq --arg port "${SERVER_PORT:-8080}" '. + {"port": ($port|tonumber)}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp" && mv "$TEMP_CONFIG_FILE.tmp" "$TEMP_CONFIG_FILE"
    jq --arg ip "$MY_IP" '. + {"server_ip": $ip}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp" && mv "$TEMP_CONFIG_FILE.tmp" "$TEMP_CONFIG_FILE"
    
    if [ -n "$POLICY_URL" ]; then
      jq --arg url "$POLICY_URL" '. + {"policy_engine_url": $url}' "$TEMP_CONFIG_FILE" > "$TEMP_CONFIG_FILE.tmp" && mv "$TEMP_CONFIG_FILE.tmp" "$TEMP_CONFIG_FILE"
    fi
  fi
  
  # Format the final config for better readability
  jq . "$TEMP_CONFIG_FILE" > "$GENERATED_CONFIG_PATH"
else
  # Without jq, just use the temp file directly
  cat "$TEMP_CONFIG_FILE" > "$GENERATED_CONFIG_PATH"
fi

# Log the generated config
log "INFO" "Generated server configuration:"
if command -v jq >/dev/null 2>&1; then
  jq . "$GENERATED_CONFIG_PATH" | tee -a "$LOG_FILE"
else
  cat "$GENERATED_CONFIG_PATH" | tee -a "$LOG_FILE"
fi

# Cleanup
rm -f "$TEMP_CONFIG_FILE" "$TEMP_CONFIG_FILE.tmp" 2>/dev/null || true

# Set environment variables for the server (redundant if Python reads from config, but good practice)
export SERVER_HOST="$HOST"
export SERVER_PORT="$SERVER_PORT"
export SERVER_IP="$MY_IP"
export LOG_LEVEL="$LOG_LEVEL"
export SERVICE_ID="$SERVICE_ID"
export METRICS_PORT="$METRICS_PORT"
export STRICT_POLICY_MODE="$STRICT_POLICY_MODE"
if [ -n "$POLICY_URL" ]; then 
  export POLICY_ENGINE_URL="$POLICY_URL"
fi

# Determine the server entrypoint script to run
if [ -f "/app/src/fl/server/fl_server.py" ]; then
  FL_SERVER_ENTRYPOINT="/app/src/fl/server/fl_server.py"
elif [ -f "/app/src/server/main.py" ]; then
  FL_SERVER_ENTRYPOINT="/app/src/server/main.py"
elif [ -f "/app/main.py" ]; then
  FL_SERVER_ENTRYPOINT="/app/main.py"
  SERVER_ARGS="--server"
else
  log "ERROR" "FL Server entry point not found. Checked: /app/src/fl/server/fl_server.py, /app/src/server/main.py, /app/main.py"
  exit 1
fi

# Change to the app directory
cd /app || {
  log "ERROR" "Failed to change to /app directory"
  exit 1
}

# Wait for required services if specified
log "INFO" "Setting policy engine URL to $POLICY_ENGINE_URL using ${POLICY_ENGINE_HOST}:${POLICY_ENGINE_PORT}"

# Check if we should wait for Policy Engine
if [ "$WAIT_FOR_POLICY_ENGINE" = "true" ]; then
  log "INFO" "Waiting for Policy Engine to be available at $POLICY_ENGINE_URL"
  wait_for_service "Policy Engine" "${POLICY_ENGINE_URL}/health" 5 6 false
  policy_available=$?
else
  log "INFO" "Policy Engine waiting is disabled"
  policy_available=0
fi

# Create model directory and ensure we have a fallback model
MODEL_DIR=${MODEL_DIR:-"/app/data/models"}
fetch_fallback_model "$MODEL_DIR"

# Modify the part where we launch the FL server to use correct parameters
log "INFO" "Starting FL Server with command: python ${FL_SERVER_ENTRYPOINT} --config ${GENERATED_CONFIG_PATH}"
set -x

# Check if the script has required parameters
HAS_BYPASS_PARAM=false
if python "$FL_SERVER_ENTRYPOINT" --help 2>&1 | grep -q "\-\-bypass-policy-engine"; then
  HAS_BYPASS_PARAM=true
fi

# Check if the script has model-dir parameter
HAS_MODEL_DIR_PARAM=false
if python "$FL_SERVER_ENTRYPOINT" --help 2>&1 | grep -q "\-\-model-dir"; then
  HAS_MODEL_DIR_PARAM=true
fi

# Build the command with available parameters
CMD="python -u \"$FL_SERVER_ENTRYPOINT\" --config \"$GENERATED_CONFIG_PATH\""

# Add stay alive parameter if enabled
if [ "$STAY_ALIVE_AFTER_TRAINING" = "true" ]; then
  CMD="$CMD --stay-alive-after-training"
  log "INFO" "Adding --stay-alive-after-training flag to command"
fi

# Add bypass parameter if available and needed
if [ "$HAS_BYPASS_PARAM" = "true" ]; then
  if [ "$WAIT_FOR_POLICY_ENGINE" != "true" ]; then
    CMD="$CMD --bypass-policy-engine"
    log "WARNING" "Adding --bypass-policy-engine flag (policy checks will be skipped!)"
  fi
fi

# Add model-dir parameter if available
if [ "$HAS_MODEL_DIR_PARAM" = "true" ]; then
  CMD="$CMD --model-dir \"/app/data/models\""
  log "INFO" "Adding --model-dir parameter with /app/data/models"
fi

# Launch with constructed command
log "INFO" "Executing command: $CMD"
eval $CMD || {
  log "ERROR" "FL Server failed to start. Attempting to start with minimal configuration."
  
  # Try again with minimal configuration - just host and port
  python "$FL_SERVER_ENTRYPOINT" --host "0.0.0.0" --port "$FL_SERVER_PORT" || {
    log "CRITICAL" "FL Server failed to start even with minimal configuration. Exiting."
    exit 1
  }
}

# Code below this line will never execute due to the exec command above
log "ERROR" "FL Server exited unexpectedly"
exit 1
