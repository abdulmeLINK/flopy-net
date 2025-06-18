#!/bin/bash
# Entrypoint script for FL Client container

# Make script more error-tolerant for critical sections
set -e  # Exit on errors initially (for setup)
trap 'echo "Error on line $LINENO"; exit 1' ERR

# Setup logging
LOGS_DIR="/app/logs"
mkdir -p "$LOGS_DIR"
LOG_FILE="$LOGS_DIR/fl-client-${CLIENT_ID:-unknown}.log"
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
  echo "[$timestamp] [FL-CLIENT] [$level] $message" | tee -a "$LOG_FILE"
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

log "Starting FL Client entrypoint script"

# Get container information
HOSTNAME=${HOSTNAME:-$(hostname)}
CONTAINER_ID=$(cat /etc/hostname)

# Set default values for environment variables
: "${SERVICE_TYPE:=fl-client}"
: "${SERVICE_ID:=${CLIENT_ID:-client-1}}"
: "${HOST:=0.0.0.0}"
: "${CLIENT_PORT:=8080}"
: "${LOG_LEVEL:=INFO}"
: "${NETWORK_MODE:=docker}"
: "${GNS3_NETWORK:=false}"
: "${USE_STATIC_IP:=false}"
: "${WAIT_FOR_SERVICES_TIMEOUT:=30}"
: "${STRICT_POLICY_MODE:=false}"

# Get client ID number from SERVICE_ID
CLIENT_OFFSET=0
if [[ "$SERVICE_ID" =~ [0-9]+$ ]]; then
  CLIENT_OFFSET=$(echo "$SERVICE_ID" | grep -oE '[0-9]+$')
fi

log "Service type: $SERVICE_TYPE"
log "Service ID: $SERVICE_ID"
log "Client ID: $CLIENT_OFFSET"
log "Logging level: $LOG_LEVEL"
log "Network mode: $NETWORK_MODE"
log "GNS3 network: $GNS3_NETWORK"
log "Static IP mode: $USE_STATIC_IP"
log "FL Client host: $HOST"
log "FL Client port: $CLIENT_PORT"

# Get the appropriate client IP variable based on client ID
CLIENT_IP_VAR="NODE_IP_FL_CLIENT"
if [ "$CLIENT_OFFSET" -gt 0 ]; then
  CLIENT_IP_VAR="NODE_IP_FL_CLIENT_${CLIENT_OFFSET}"
fi

CLIENT_IP=${!CLIENT_IP_VAR}

if [ -z "$CLIENT_IP" ]; then
  log "ERROR" "No IP found for $CLIENT_IP_VAR environment variable"
  exit 1
fi

log "INFO" "Client IP: $CLIENT_IP"

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
  log "INFO" "Assigning static IP $CLIENT_IP/24 to $TARGET_IFACE"
  ip addr add "$CLIENT_IP/24" dev "$TARGET_IFACE" || {
    log "ERROR" "Failed to assign IP $CLIENT_IP to $TARGET_IFACE. Check network configuration and permissions. Exiting."
    exit 1
  }
    
  # Verify IP was actually assigned
  sleep 1
  ASSIGNED_IP=$(ip -4 addr show dev "$TARGET_IFACE" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
  if [ "$ASSIGNED_IP" == "$CLIENT_IP" ]; then
    log "SUCCESS" "IP $ASSIGNED_IP successfully assigned to $TARGET_IFACE"
    CLEAN_IP="$ASSIGNED_IP"
    
    # Set up routing if we have a valid IP
    IFS='.' read -r -a IP_PARTS <<< "$CLEAN_IP"
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
    log "ERROR" "Failed to assign or verify static IP. Expected $CLIENT_IP but found $ASSIGNED_IP on $TARGET_IFACE."
  fi
fi

# Add hosts entries for all NODE_IP_ variables
log "Adding hosts entries from NODE_IP_ variables"
for var in $(env | grep "^NODE_IP_" | sort); do
  varname=$(echo "$var" | cut -d= -f1)
  ip_value=$(echo "$var" | cut -d= -f2)
  
  # Skip if invalid IP
  if ! validate_ip "$ip_value"; then
    log "WARNING" "Invalid IP in $varname: $ip_value, skipping"
    continue
  fi
  
  # Extract hostname from variable name
  hostname=$(echo "${varname#NODE_IP_}" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
  
  log "Adding hosts entry: $hostname -> $ip_value"
  update_hosts_entry "$ip_value" "$hostname"
done

# Update own IP in hosts file
update_hosts_entry "127.0.0.1" "localhost"
if [ -n "$CLEAN_IP" ]; then
  update_hosts_entry "$CLEAN_IP" "$HOSTNAME"
  update_hosts_entry "$CLEAN_IP" "fl-client-$CLIENT_OFFSET"
  update_hosts_entry "$CLEAN_IP" "client-$CLIENT_OFFSET"
elif [ -n "$CLIENT_IP" ]; then
  update_hosts_entry "$CLIENT_IP" "$HOSTNAME"
  update_hosts_entry "$CLIENT_IP" "fl-client-$CLIENT_OFFSET"
  update_hosts_entry "$CLIENT_IP" "client-$CLIENT_OFFSET"
fi

log "FL Client environment setup complete"

# Create necessary directories with proper permissions
log "Creating necessary directories"
mkdir -p /app/logs
mkdir -p /app/config/fl_client
mkdir -p /app/data/models
chmod -R 777 /app/logs
chmod -R 777 /app/config
chmod -R 777 /app/data

# Get the CONFIG_DIR from environment or use default
CONFIG_DIR=${CONFIG_DIR:-"/app/config"}
CLIENT_CONFIG_DIR=${CLIENT_CONFIG_DIR:-"${CONFIG_DIR}/fl_client"}
mkdir -p "$CLIENT_CONFIG_DIR"

# Dynamic config generation
GENERATED_CONFIG_PATH="${CLIENT_CONFIG_DIR}/client_${CLIENT_OFFSET}_config.json"
log "INFO" "Generating dynamic client configuration at $GENERATED_CONFIG_PATH"

# Start building the JSON configuration
cat > "$GENERATED_CONFIG_PATH" << EOF
{
  "client_id": "${SERVICE_ID}",
  "client_offset": ${CLIENT_OFFSET},
  "host": "${HOST:-"0.0.0.0"}",
  "port": ${CLIENT_PORT:-8080},
  "log_level": "${LOG_LEVEL:-"INFO"}",
  "log_file": "${LOG_FILE:-"/app/logs/fl-client-${CLIENT_OFFSET}.log"}",
  "model_dir": "${MODEL_DIR:-"/app/data/models"}"
}
EOF

# Add client IP to configuration
if [ -n "$CLEAN_IP" ]; then
  # Use jq if available to properly update the JSON
  if command -v jq >/dev/null 2>&1; then
    jq --arg ip "$CLEAN_IP" '. + {"client_ip": $ip}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    # Fallback method without jq - less safe but functional
    # Remove the last closing brace, add the new field, and add the closing brace back
    sed -i '$ s/}$/,\n  "client_ip": "'"$CLEAN_IP"'"\n}/' "$GENERATED_CONFIG_PATH"
  fi
elif [ -n "$CLIENT_IP" ]; then
  # Use client IP if clean IP is not available
  if command -v jq >/dev/null 2>&1; then
    jq --arg ip "$CLIENT_IP" '. + {"client_ip": $ip}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "client_ip": "'"$CLIENT_IP"'"\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

# Add known hostnames from environment variables
if [ -n "$SERVER_HOST" ]; then
  log "INFO" "Adding server_host: $SERVER_HOST to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg k "server_host" --arg v "$SERVER_HOST" '. + {($k): $v}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "server_host": "'"$SERVER_HOST"'"\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

if [ -n "$POLICY_ENGINE_HOST" ]; then
  log "INFO" "Adding policy_engine_host: $POLICY_ENGINE_HOST to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg k "policy_engine_host" --arg v "$POLICY_ENGINE_HOST" '. + {($k): $v}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "policy_engine_host": "'"$POLICY_ENGINE_HOST"'"\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

if [ -n "$COLLECTOR_HOST" ] || [ -n "$NODE_IP_COLLECTOR" ]; then
  COLLECTOR_HOSTNAME=${COLLECTOR_HOST:-"metrics-collector"}
  log "INFO" "Adding collector_host: $COLLECTOR_HOSTNAME to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg k "collector_host" --arg v "$COLLECTOR_HOSTNAME" '. + {($k): $v}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "collector_host": "'"$COLLECTOR_HOSTNAME"'"\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

# Also add ports if they are defined in environment variables
if [ -n "$SERVER_PORT" ]; then
  log "INFO" "Adding server_port: $SERVER_PORT to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg port "$SERVER_PORT" '. + {"server_port": ($port|tonumber)}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "server_port": '"$SERVER_PORT"'\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

if [ -n "$POLICY_ENGINE_PORT" ]; then
  log "INFO" "Adding policy_engine_port: $POLICY_ENGINE_PORT to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg port "$POLICY_ENGINE_PORT" '. + {"policy_engine_port": ($port|tonumber)}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "policy_engine_port": '"$POLICY_ENGINE_PORT"'\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

if [ -n "$COLLECTOR_PORT" ]; then
  log "INFO" "Adding collector_port: $COLLECTOR_PORT to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg port "$COLLECTOR_PORT" '. + {"collector_port": ($port|tonumber)}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "collector_port": '"$COLLECTOR_PORT"'\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

# Add node IPs to config - keeping this for backward compatibility, but hostnames above should be preferred
if command -v jq >/dev/null 2>&1; then
  NODE_IPS_JSON="{}"
  
  # Add all NODE_IP_ variables to the node_ips JSON object
  for var in $(env | grep "^NODE_IP_" | sort); do
    varname=$(echo "$var" | cut -d= -f1)
    ip_value=$(echo "$var" | cut -d= -f2)
    
    # Skip if invalid IP
    if ! validate_ip "$ip_value"; then
      continue
    fi
    
    # Extract component name from variable name (without NODE_IP_ prefix)
    component=$(echo "${varname#NODE_IP_}" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
    
    # Add to node_ips JSON object
    NODE_IPS_JSON=$(echo "$NODE_IPS_JSON" | jq --arg k "$component" --arg v "$ip_value" '. + {($k): $v}')
  done
  
  # Add node_ips object to config
  echo "$NODE_IPS_JSON" > "${GENERATED_CONFIG_PATH}.node_ips.json"
  jq -s '.[0] + {"node_ips": .[1]}' "$GENERATED_CONFIG_PATH" "${GENERATED_CONFIG_PATH}.node_ips.json" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  rm -f "${GENERATED_CONFIG_PATH}.node_ips.json"
else
  # Simple fallback if jq is not available - just add each NODE_IP_ as a separate entry
  for var in $(env | grep "^NODE_IP_" | sort); do
    varname=$(echo "$var" | cut -d= -f1)
    ip_value=$(echo "$var" | cut -d= -f2)
    
    # Skip if invalid IP
    if ! validate_ip "$ip_value"; then
      continue
    fi
    
    # Extract component name from variable name
    component=$(echo "${varname#NODE_IP_}" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
    key="node_ip_$(echo "$component" | tr '-' '_')"
    
    # Add to config
    sed -i '$ s/}$/,\n  "'"$key"'": "'"$ip_value"'"\n}/' "$GENERATED_CONFIG_PATH"
  done
fi

# Add any custom configuration environments with CLIENT_CONFIG_ prefix
for var in $(env | grep "^CLIENT_CONFIG_"); do
  key=$(echo "$var" | cut -d= -f1 | sed 's/^CLIENT_CONFIG_//' | tr '[:upper:]' '[:lower:]')
  value=$(echo "$var" | cut -d= -f2)
  
  # Try to determine if value is numeric, boolean, or string
  if [[ "$value" =~ ^[0-9]+$ ]]; then
    # Integer value - no quotes
    if command -v jq >/dev/null 2>&1; then
      jq --arg k "$key" --arg v "$value" '. + {($k): ($v|tonumber)}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
    else
      sed -i '$ s/}$/,\n  "'"$key"'": '"$value"'\n}/' "$GENERATED_CONFIG_PATH"
    fi
  elif [[ "$value" =~ ^(true|false)$ ]]; then
    # Boolean value - no quotes
    if command -v jq >/dev/null 2>&1; then
      jq --arg k "$key" --arg v "$value" '. + {($k): ($v=="true")}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
    else
      sed -i '$ s/}$/,\n  "'"$key"'": '"$value"'\n}/' "$GENERATED_CONFIG_PATH"
    fi
  else
    # String value - add quotes
    if command -v jq >/dev/null 2>&1; then
      jq --arg k "$key" --arg v "$value" '. + {($k): $v}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
    else
      sed -i '$ s/}$/,\n  "'"$key"'": "'"$value"'"\n}/' "$GENERATED_CONFIG_PATH"
    fi
  fi
done

# Log the generated config
log "INFO" "Generated client configuration:"
if command -v jq >/dev/null 2>&1; then
  jq . "$GENERATED_CONFIG_PATH" | tee -a "$LOG_FILE"
else
  cat "$GENERATED_CONFIG_PATH" | tee -a "$LOG_FILE"
fi

log "INFO" "Waiting for services before starting client..."

# Change to the app directory
cd /app || {
  log "ERROR" "Failed to change to /app directory"
  exit 1
}

# Forward all NODE_IP_ variables to the Python client as environment variables
log "INFO" "Setting up environment variables for the FL client"

# Export NODE_IP variables for Python client
for var in $(env | grep "^NODE_IP_" | sort); do
  export "$var"
  varname=$(echo "$var" | cut -d= -f1)
  varvalue=$(echo "$var" | cut -d= -f2)
  log "INFO" "Forwarding environment variable: $varname=$varvalue"
done

# Export all configuration to FL_* environment variables for the Python client
export FL_CONFIG="$GENERATED_CONFIG_PATH"
export FL_CLIENT_ID="$SERVICE_ID"
export FL_SERVER_HOST="${SERVER_HOST:-fl-server}"
if [ -n "$NODE_IP_FL_SERVER" ]; then
  export FL_SERVER_HOST="$NODE_IP_FL_SERVER"
  log "INFO" "Setting FL_SERVER_HOST from NODE_IP_FL_SERVER: $FL_SERVER_HOST"
fi

export FL_SERVER_PORT="${SERVER_PORT:-8080}"
export FL_LOG_LEVEL="$LOG_LEVEL"
export FL_LOG_FILE="$LOG_FILE"
export CLIENT_ID="$SERVICE_ID"  # Legacy support

# Set policy engine URL if policy engine IP is available
if [ -n "$NODE_IP_POLICY_ENGINE" ]; then
  export POLICY_ENGINE_URL="http://$NODE_IP_POLICY_ENGINE:5000"
  log "INFO" "Setting POLICY_ENGINE_URL from NODE_IP_POLICY_ENGINE: $POLICY_ENGINE_URL"
fi

# Export strict policy mode setting
export STRICT_POLICY_MODE="$STRICT_POLICY_MODE"
log "INFO" "Setting STRICT_POLICY_MODE: $STRICT_POLICY_MODE"

# Check for Python installation first
if command -v python3 &> /dev/null; then
  PYTHON_CMD="python3"
  log "INFO" "Using python3 for execution"
elif command -v python &> /dev/null; then
  PYTHON_CMD="python"
  log "INFO" "Using python for execution"
else
  log "ERROR" "Neither python nor python3 command found"
  exit 1
fi

# Show Python version for debugging
$PYTHON_CMD --version 2>&1 | tee -a "$LOG_FILE"

# Improved entrypoint detection - check all possible locations
log "INFO" "Searching for FL Client entry point"

# Define possible entry points in order of preference
POSSIBLE_ENTRYPOINTS=(
  "/app/src/fl/client/fl_client.py"
  "/app/src/flclient/fl_client.py"
  "/app/src/fl_client.py"
  "/app/fl_client.py"
  "/app/src/fl/client/service.py"
  "/app/src/fl/client/main.py"
  "/app/main.py"
)

# Find the entry point
CLIENT_ENTRYPOINT=""
CLIENT_ARGS=""

for entrypoint in "${POSSIBLE_ENTRYPOINTS[@]}"; do
  if [ -f "$entrypoint" ]; then
    log "INFO" "Found potential entry point: $entrypoint"
    
    # Check if the file is executable or readable
    if [ -x "$entrypoint" ] || [ -r "$entrypoint" ]; then
      CLIENT_ENTRYPOINT="$entrypoint"
      # Add special args for main.py
      if [[ "$entrypoint" == *"/main.py" ]]; then
        CLIENT_ARGS="--client"
        log "INFO" "Adding --client argument for main.py"
      fi
      log "SUCCESS" "Selected entry point: $CLIENT_ENTRYPOINT"
      break
    else
      log "WARNING" "Found $entrypoint but it's not executable/readable"
      # Try to fix permissions
      chmod +rx "$entrypoint" && {
        log "INFO" "Fixed permissions for $entrypoint"
        CLIENT_ENTRYPOINT="$entrypoint"
        if [[ "$entrypoint" == *"/main.py" ]]; then
          CLIENT_ARGS="--client"
        fi
        break
      } || {
        log "WARNING" "Failed to fix permissions for $entrypoint"
      }
    fi
  fi
done

if [ -z "$CLIENT_ENTRYPOINT" ]; then
  # Last resort: search for any Python files that might work
  log "WARNING" "No predefined entry points found, searching for Python files"
  
  # List all Python files in the /app directory tree
  PYTHON_FILES=$(find /app -name "*.py" -type f 2>/dev/null | sort)
  log "INFO" "Found Python files: $(echo "$PYTHON_FILES" | tr '\n' ' ')"
  
  # Try to identify a likely candidate based on filename
  for pyfile in $PYTHON_FILES; do
    if [[ "$pyfile" == *"client"* && "$pyfile" == *"fl"* ]]; then
      log "INFO" "Found potential client file: $pyfile"
      CLIENT_ENTRYPOINT="$pyfile"
      break
    elif [[ "$pyfile" == */app/main.py || "$pyfile" == */src/main.py ]]; then
      log "INFO" "Found potential main file: $pyfile"
      CLIENT_ENTRYPOINT="$pyfile"
      CLIENT_ARGS="--client"
      break
    fi
  done
fi

# If we still don't have an entry point, fail
if [ -z "$CLIENT_ENTRYPOINT" ]; then
  log "ERROR" "FL Client entry point not found after exhaustive search"
  log "ERROR" "Current directory: $(pwd)"
  log "ERROR" "Directory contents: $(ls -la /app)"
  log "ERROR" "Python files found: $(find /app -name "*.py" -type f 2>/dev/null)"
  exit 1
fi

# Verify the script exists and is readable
if [ ! -r "$CLIENT_ENTRYPOINT" ]; then
  log "ERROR" "Selected entry point $CLIENT_ENTRYPOINT is not readable"
  exit 1
fi

# Final checks and execution
log "INFO" "Starting FL Client from $CLIENT_ENTRYPOINT with config $GENERATED_CONFIG_PATH"

# Execute with error handling - try capturing error output
if [ -n "$CLIENT_ARGS" ]; then
  CMD="$PYTHON_CMD -u \"$CLIENT_ENTRYPOINT\" $CLIENT_ARGS --config \"$GENERATED_CONFIG_PATH\""
else
  CMD="$PYTHON_CMD -u \"$CLIENT_ENTRYPOINT\" --config \"$GENERATED_CONFIG_PATH\""
fi

log "INFO" "Executing command: $CMD"

# Use set -x to log the actual command being executed
set -x
# Execute the Python client with the environment variables we've set up
eval "$CMD" 2>&1 || {
  log "ERROR" "Failed to execute FL Client. Retrying with direct execution..."
  
  # Try direct execution as a fallback
  if [ -n "$CLIENT_ARGS" ]; then
    exec $PYTHON_CMD -u "$CLIENT_ENTRYPOINT" $CLIENT_ARGS --config "$GENERATED_CONFIG_PATH"
  else
    exec $PYTHON_CMD -u "$CLIENT_ENTRYPOINT" --config "$GENERATED_CONFIG_PATH"
  fi
}

# This line will only be reached if both execution methods failed
log "ERROR" "FL Client exited unexpectedly"
exit 1 