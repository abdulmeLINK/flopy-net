#!/bin/bash
# Entrypoint script for Metrics Collector container

# Configure error handling
set -e
set -o pipefail

# Setup logging
LOGS_DIR="/app/logs"
mkdir -p "$LOGS_DIR"
LOG_FILE="$LOGS_DIR/collector.log"
touch $LOG_FILE
chmod -R 777 /app/logs

# Log function
log() {
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  local level=${1:-INFO}
  local message=$2
  if [ "$#" -eq 1 ]; then
    message=$level
    level="INFO"
  fi
  echo "[$timestamp] [COLLECTOR] [$level] $message" | tee -a "$LOG_FILE"
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

log "Starting Collector entrypoint script"

# Get container information
HOSTNAME=${HOSTNAME:-$(hostname)}
CONTAINER_ID=$(cat /etc/hostname)

# Set default values for environment variables
: "${SERVICE_TYPE:=collector}"
: "${SERVICE_ID:=metrics-collector}"
: "${HOST:=0.0.0.0}"
: "${COLLECTOR_PORT:=9090}"
: "${METRICS_PORT:=9091}"
: "${LOG_LEVEL:=INFO}"
: "${NETWORK_MODE:=docker}"
: "${GNS3_NETWORK:=false}"
: "${USE_STATIC_IP:=false}"
: "${COLLECTOR_ENTRYPOINT:=/app/src/collector/service.py}"
: "${FL_SERVER_PORT:=9091}"  # Set default FL server port to match the metrics port

log "Service type: $SERVICE_TYPE"
log "Service ID: $SERVICE_ID"
log "Logging level: $LOG_LEVEL"
log "Network mode: $NETWORK_MODE"
log "GNS3 network: $GNS3_NETWORK"
log "Static IP mode: $USE_STATIC_IP"
log "Collector host: $HOST"
log "Collector port: $COLLECTOR_PORT"
log "Metrics port: $METRICS_PORT"

# Get the collector IP from environment
COLLECTOR_IP_VALUE="$NODE_IP_COLLECTOR"
if [ -z "$COLLECTOR_IP_VALUE" ]; then
  log "ERROR" "No IP found for NODE_IP_COLLECTOR environment variable"
  exit 1
fi

log "INFO" "Collector IP: $COLLECTOR_IP_VALUE"

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
  log "INFO" "Assigning static IP $COLLECTOR_IP_VALUE/24 to $TARGET_IFACE"
  ip addr add "$COLLECTOR_IP_VALUE/24" dev "$TARGET_IFACE" || {
    log "ERROR" "Failed to assign IP $COLLECTOR_IP_VALUE to $TARGET_IFACE. Check network configuration and permissions. Exiting."
    exit 1
  }
    
  # Verify IP was actually assigned
  sleep 1
  ASSIGNED_IP=$(ip -4 addr show dev "$TARGET_IFACE" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
  if [ "$ASSIGNED_IP" == "$COLLECTOR_IP_VALUE" ]; then
    log "SUCCESS" "IP $ASSIGNED_IP successfully assigned to $TARGET_IFACE"
    CLEAN_IP="$ASSIGNED_IP"
    
    # Configure northbound interface if specified
    # configure_northbound_interface # <-- Commented out this line
    
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
    log "ERROR" "Failed to assign or verify static IP. Expected $COLLECTOR_IP_VALUE but found $ASSIGNED_IP on $TARGET_IFACE."
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
# Always use the provided NODE_IP_COLLECTOR value if available
if [ -n "$COLLECTOR_IP_VALUE" ]; then
  log "INFO" "Using specified collector IP $COLLECTOR_IP_VALUE for hosts entries."
  update_hosts_entry "$COLLECTOR_IP_VALUE" "$HOSTNAME"
  update_hosts_entry "$COLLECTOR_IP_VALUE" "metrics-collector"
  update_hosts_entry "$COLLECTOR_IP_VALUE" "collector"
elif [ -n "$CLEAN_IP" ]; then
  # Fallback to dynamically detected IP if NODE_IP_COLLECTOR was not set
  log "WARNING" "NODE_IP_COLLECTOR not set, using dynamically detected IP $CLEAN_IP for hosts entries."
  update_hosts_entry "$CLEAN_IP" "$HOSTNAME"
  update_hosts_entry "$CLEAN_IP" "metrics-collector"
  update_hosts_entry "$CLEAN_IP" "collector"
else
  log "WARNING" "Could not determine collector IP for hosts file updates."
fi

log "Collector environment setup complete"

# Create necessary directories with proper permissions
log "Creating necessary directories"
mkdir -p /app/logs
mkdir -p /app/config/collector
mkdir -p /app/data/metrics
chmod -R 777 /app/logs
chmod -R 777 /app/config
chmod -R 777 /app/data

# Get the CONFIG_DIR from environment or use default
CONFIG_DIR=${CONFIG_DIR:-"/app/config"}
COLLECTOR_CONFIG_DIR=${COLLECTOR_CONFIG_DIR:-"${CONFIG_DIR}/collector"}
mkdir -p "$COLLECTOR_CONFIG_DIR"

# Dynamic config generation
GENERATED_CONFIG_PATH="${COLLECTOR_CONFIG_DIR}/collector_config.json"
log "INFO" "Loading collector configuration..."

# Check for mounted collector_config.json first (from config directory in project)
MOUNTED_CONFIG="/app/config/collector_config.json"
if [ -f "$MOUNTED_CONFIG" ]; then
  log "INFO" "Found mounted collector configuration at $MOUNTED_CONFIG"
  # Copy it to the expected location
  cp "$MOUNTED_CONFIG" "$GENERATED_CONFIG_PATH"
  log "INFO" "Copied mounted configuration to $GENERATED_CONFIG_PATH"
else
  # No mounted config, so we need to generate one from environment variables
  log "INFO" "No mounted JSON config found. Generating configuration from environment variables at $GENERATED_CONFIG_PATH"
  
  # Create a basic JSON configuration structure
  cat > "$GENERATED_CONFIG_PATH" << EOF
{
  "collector_id": "${SERVICE_ID}",
  "host": "${HOST:-"0.0.0.0"}",
  "port": ${COLLECTOR_PORT:-9090},
  "metrics_port": ${METRICS_PORT:-9091},
  "log_level": "${LOG_LEVEL:-"INFO"}",
  "log_file": "${LOG_FILE:-"/app/logs/collector.log"}",
  "storage_dir": "${STORAGE_DIR:-"/app/data/metrics"}",
  "policy_engine": {
    "url": "http://${POLICY_ENGINE_HOST:-"policy-engine"}:${POLICY_ENGINE_PORT:-5000}"
  },
  "fl_server": {
    "url": "http://${FL_SERVER_HOST:-"fl-server"}:${FL_SERVER_PORT:-8085}"
  },
  "features": {
    "check_policy_enabled": ${CHECK_POLICY_ENABLED:-true},
    "policy_monitor_enabled": ${POLICY_MONITOR_ENABLED:-true},
    "fl_monitor_enabled": ${FL_MONITOR_ENABLED:-true},
    "network_monitor_enabled": ${NETWORK_MONITOR_ENABLED:-false}
  },
  "intervals": {
    "policy_interval_sec": ${POLICY_INTERVAL_SEC:-5},
    "fl_interval_sec": ${FL_INTERVAL_SEC:-5},
    "network_interval_sec": ${NETWORK_INTERVAL_SEC:-5},
    "event_interval_sec": ${EVENT_INTERVAL_SEC:-5}
  },
  "api": {
    "enabled": true,
    "port": ${COLLECTOR_PORT:-8000}
  }
}
EOF
  log "INFO" "Basic configuration template created"
fi

# Add collector IP to configuration
# Always use the provided NODE_IP_COLLECTOR value if available
if [ -n "$COLLECTOR_IP_VALUE" ]; then
  log "INFO" "Using specified collector IP $COLLECTOR_IP_VALUE for configuration."
  if command -v jq >/dev/null 2>&1; then
    jq --arg ip "$COLLECTOR_IP_VALUE" '. + {"collector_ip": $ip}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,
  "collector_ip": "'"$COLLECTOR_IP_VALUE"'"
}/' "$GENERATED_CONFIG_PATH"
  fi
elif [ -n "$CLEAN_IP" ]; then
  # Fallback to dynamically detected IP if NODE_IP_COLLECTOR was not set
  log "WARNING" "NODE_IP_COLLECTOR not set, using dynamically detected IP $CLEAN_IP for configuration."
  if command -v jq >/dev/null 2>&1; then
    jq --arg ip "$CLEAN_IP" '. + {"collector_ip": $ip}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,
  "collector_ip": "'"$CLEAN_IP"'"
}/' "$GENERATED_CONFIG_PATH"
  fi
else
  log "WARNING" "Could not determine collector IP for configuration file."
fi

# Add known hostnames from environment variables
if [ -n "$POLICY_ENGINE_HOST" ]; then
  log "INFO" "Adding policy_engine_host: $POLICY_ENGINE_HOST to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg k "policy_engine_host" --arg v "$POLICY_ENGINE_HOST" '. + {($k): $v}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "policy_engine_host": "'"$POLICY_ENGINE_HOST"'"\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

if [ -n "$FL_SERVER_HOST" ]; then
  log "INFO" "Adding fl_server_host: $FL_SERVER_HOST to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg k "fl_server_host" --arg v "$FL_SERVER_HOST" '. + {($k): $v}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "fl_server_host": "'"$FL_SERVER_HOST"'"\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

if [ -n "$SDN_CONTROLLER_HOST" ]; then
  log "INFO" "Adding sdn_controller_host: $SDN_CONTROLLER_HOST to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg k "sdn_controller_host" --arg v "$SDN_CONTROLLER_HOST" '. + {($k): $v}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "sdn_controller_host": "'"$SDN_CONTROLLER_HOST"'"\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

# Also add ports if they are defined in environment variables
if [ -n "$POLICY_ENGINE_PORT" ]; then
  log "INFO" "Adding policy_engine_port: $POLICY_ENGINE_PORT to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg port "$POLICY_ENGINE_PORT" '. + {"policy_engine_port": ($port|tonumber)}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "policy_engine_port": '"$POLICY_ENGINE_PORT"'\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

if [ -n "$FL_SERVER_PORT" ]; then
  log "INFO" "Adding fl_server_port: $FL_SERVER_PORT to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg port "$FL_SERVER_PORT" '. + {"fl_server_port": ($port|tonumber)}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "fl_server_port": '"$FL_SERVER_PORT"'\n}/' "$GENERATED_CONFIG_PATH"
  fi
fi

if [ -n "$SDN_CONTROLLER_PORT" ]; then
  log "INFO" "Adding sdn_controller_port: $SDN_CONTROLLER_PORT to config"
  if command -v jq >/dev/null 2>&1; then
    jq --arg port "$SDN_CONTROLLER_PORT" '. + {"sdn_controller_port": ($port|tonumber)}' "$GENERATED_CONFIG_PATH" > "${GENERATED_CONFIG_PATH}.tmp" && mv "${GENERATED_CONFIG_PATH}.tmp" "$GENERATED_CONFIG_PATH"
  else
    sed -i '$ s/}$/,\n  "sdn_controller_port": '"$SDN_CONTROLLER_PORT"'\n}/' "$GENERATED_CONFIG_PATH"
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

# Add any custom configuration environments with COLLECTOR_CONFIG_ prefix
for var in $(env | grep "^COLLECTOR_CONFIG_"); do
  key=$(echo "$var" | cut -d= -f1 | sed 's/^COLLECTOR_CONFIG_//' | tr '[:upper:]' '[:lower:]')
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
log "INFO" "Generated collector configuration:"
if command -v jq >/dev/null 2>&1; then
  jq . "$GENERATED_CONFIG_PATH" | tee -a "$LOG_FILE"
else
  cat "$GENERATED_CONFIG_PATH" | tee -a "$LOG_FILE"
fi

# Continue with Collector application startup
COLLECTOR_ARGS=""
if [ -f "/app/src/collector/collector.py" ]; then
  COLLECTOR_ENTRYPOINT="/app/src/collector/collector.py"
elif [ -n "$COLLECTOR_ENTRYPOINT" ] && [ -f "$COLLECTOR_ENTRYPOINT" ]; then
  log "INFO" "Using entrypoint from environment: $COLLECTOR_ENTRYPOINT"
  # Keep existing logic for env var based entrypoint if needed
elif [ -f "/app/src/collector/service.py" ]; then # Fallback 1
  log "WARNING" "Main collector.py not found, using service.py fallback"
  COLLECTOR_ENTRYPOINT="/app/src/collector/service.py"
elif [ -f "/app/main.py" ]; then # Fallback 2
  log "WARNING" "Main collector.py not found, using main.py fallback"
  COLLECTOR_ENTRYPOINT="/app/main.py"
  COLLECTOR_ARGS="--collector" # Assume main.py needs this arg
else
  log "ERROR" "Collector entry point not found. Checked: /app/src/collector/collector.py, $COLLECTOR_ENTRYPOINT, /app/src/collector/service.py, /app/main.py"
  exit 1
fi

# Change to the app directory
cd /app || {
  log "ERROR" "Failed to change to /app directory"
  exit 1
}

# Start Collector with appropriate arguments using exec
log "INFO" "Starting Collector from $COLLECTOR_ENTRYPOINT with config $GENERATED_CONFIG_PATH"

# Check python installation
if ! command -v python &> /dev/null; then
  if command -v python3 &> /dev/null; then
    log "INFO" "Using python3 instead of python"
    PYTHON_CMD="python3"
  else
    log "ERROR" "Neither python nor python3 command found"
    exit 1
  fi
else
  PYTHON_CMD="python"
fi

# Execute the command with proper environment
if [ -n "$COLLECTOR_ARGS" ]; then
  exec $PYTHON_CMD -u "$COLLECTOR_ENTRYPOINT" $COLLECTOR_ARGS --config "$GENERATED_CONFIG_PATH"
else
  exec $PYTHON_CMD -u "$COLLECTOR_ENTRYPOINT" --config "$GENERATED_CONFIG_PATH"
fi

# Code below this line will never execute due to the exec command above
log "ERROR" "Collector exited unexpectedly"
exit 1
