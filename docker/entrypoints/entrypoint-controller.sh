#!/bin/bash
# Entrypoint script for SDN Controller container

# Setup logging
LOGS_DIR="/app/logs"
mkdir -p "$LOGS_DIR"
LOG_FILE="$LOGS_DIR/controller.log"
touch $LOG_FILE
chmod 777 "$LOG_FILE"

# Log function
log() {
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  local level=${1:-INFO}
  local message=$2
  if [ "$#" -eq 1 ]; then
    message=$level
    level="INFO"
  fi
  echo "[$timestamp] [CONTROLLER] [$level] $message" | tee -a "$LOG_FILE"
}

# Cleanup function for script exit
cleanup() {
  log "INFO" "Running cleanup function"
  # Save exit status
  local exit_status=$?
  
  # Check if routes need cleaning
  if ip route | grep -q "${NODE_IP_POLICY_ENGINE}/32"; then
    log "INFO" "Cleaning up added routes"
    ip route del ${NODE_IP_POLICY_ENGINE}/32 2>/dev/null || true
  fi
  
  # Check for any leftover processes or files
  # and clean them up here
  
  # Exit with the original exit status
  exit $exit_status
}

# Set trap for script exit
trap cleanup EXIT INT TERM

# Basic IP validation
validate_ip() {
  local ip=$1
  if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    return 0
  else
    return 1
  fi
}

# Get container IP
get_container_ip() {
  local interface="${1:-eth0}"
  ip -4 addr show $interface 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n 1 | tr -d '\n'
}

# Simple IP assignment function
assign_ip() {
  local ip=$1
  local interface=$2
  local subnet=${3:-24}
  
  log "DEBUG" "Starting IP assignment for $interface with IP $ip/$subnet"
  
  # Make sure interface is up first
  log "INFO" "Setting $interface up"
  ip link set dev $interface up
  if [ $? -ne 0 ]; then
    log "ERROR" "Failed to bring up $interface"
    ip link show $interface | tee -a "$LOG_FILE"
    return 1
  fi
  log "DEBUG" "Interface $interface is up"
  
  # Flush existing IPs
  log "INFO" "Flushing existing IPs from $interface"
  ip addr flush dev $interface scope global
  if [ $? -ne 0 ]; then
    log "WARNING" "Failed to flush interface (may have had no IP)"
  fi
  sleep 1
  
  # Add the new IP
  log "INFO" "Adding IP $ip/$subnet to $interface"
  ip addr add $ip/$subnet dev $interface
  if [ $? -ne 0 ]; then
    log "ERROR" "Failed to assign IP $ip to $interface"
    log "DEBUG" "Current interface state:"
    ip addr show $interface | tee -a "$LOG_FILE"
    return 1
  fi
  
  # Verify the IP was assigned
  local assigned_ip=$(ip -4 addr show dev $interface | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
  if [ "$assigned_ip" = "$ip" ]; then
    log "SUCCESS" "Verified IP $ip is assigned to $interface"
    log "DEBUG" "IP assignment successful for $interface"
    return 0
  else
    log "ERROR" "IP verification failed, expected $ip but found $assigned_ip"
    log "DEBUG" "Current interface state after assignment attempt:"
    ip addr show $interface | tee -a "$LOG_FILE"
    return 1
  fi
}

# Configure northbound interface
configure_northbound_interface() {
  log "DEBUG" "========== NORTHBOUND INTERFACE CONFIGURATION STARTING =========="
  
  # Check if northbound interface is specified
  if [ -z "$NORTHBOUND_INTERFACE" ]; then
    log "INFO" "No northbound interface specified, skipping northbound configuration"
    return 0
  fi

  log "DEBUG" "Northbound interface to configure: $NORTHBOUND_INTERFACE"
  
  # Check if northbound IP is specified
  if [ -z "$NORTHBOUND_IP" ]; then
    log "WARNING" "Northbound interface specified but no IP provided, using default"
    NORTHBOUND_IP="${SUBNET_PREFIX:-192.168.100}.51"  # Fallback to a fixed IP
    log "DEBUG" "Using fallback northbound IP: $NORTHBOUND_IP"
  fi
  
  log "INFO" "Configuring northbound interface $NORTHBOUND_INTERFACE with IP $NORTHBOUND_IP"
  
  # Check if interface exists
  if ! ip link show "$NORTHBOUND_INTERFACE" &>/dev/null; then
    log "WARNING" "Northbound interface $NORTHBOUND_INTERFACE does not exist"
    log "DEBUG" "Available interfaces:"
    ip link | grep -E "^[0-9]+" | tee -a "$LOG_FILE"
    
    # Continue without failing - just use default route
    log "INFO" "Will proceed using default network route for policy engine communication"
    export NORTHBOUND_MISSING=true
    
    # Add specific route for policy engine through default interface
    if [ -n "$NODE_IP_POLICY_ENGINE" ]; then
      log "INFO" "Adding direct route to policy engine via default interface"
      # Find the default interface
      DEFAULT_INTERFACE=$(ip -o -4 route show to default | awk '{print $5}' | head -n 1)
      if [ -n "$DEFAULT_INTERFACE" ]; then
        log "INFO" "Using default interface $DEFAULT_INTERFACE for policy engine communication"
        ip route add ${NODE_IP_POLICY_ENGINE}/32 dev ${DEFAULT_INTERFACE} || true
        log "INFO" "Added route to policy engine via ${DEFAULT_INTERFACE}"
      fi
    fi
    
    log "DEBUG" "========== NORTHBOUND INTERFACE CONFIGURATION SKIPPED (INTERFACE MISSING) =========="
    return 0
  fi
  
  # Continue with normal setup if interface exists
  log "DEBUG" "Northbound interface $NORTHBOUND_INTERFACE exists, proceeding with IP assignment"
  
  # Simply use the assign_ip function
  if assign_ip "$NORTHBOUND_IP" "$NORTHBOUND_INTERFACE"; then
    log "SUCCESS" "Successfully configured northbound interface $NORTHBOUND_INTERFACE with IP $NORTHBOUND_IP"
    
    # Verify the IP was assigned
    ASSIGNED_NB_IP=$(ip -4 addr show dev "$NORTHBOUND_INTERFACE" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
    if [ -n "$ASSIGNED_NB_IP" ]; then
      log "SUCCESS" "Verified northbound IP $ASSIGNED_NB_IP on interface $NORTHBOUND_INTERFACE"
    else
      log "ERROR" "Failed to verify northbound IP on interface $NORTHBOUND_INTERFACE"
      ip addr show "$NORTHBOUND_INTERFACE" | tee -a "$LOG_FILE"
    fi
    
    # Add specific route for policy engine through northbound interface
    if [ -n "$NODE_IP_POLICY_ENGINE" ]; then
      log "INFO" "Adding specific route to policy engine via northbound interface"
      ip route add ${NODE_IP_POLICY_ENGINE}/32 dev ${NORTHBOUND_INTERFACE}
      if [ $? -eq 0 ]; then
        log "SUCCESS" "Successfully added route to policy engine via ${NORTHBOUND_INTERFACE}"
      else
        log "ERROR" "Failed to add route to policy engine via ${NORTHBOUND_INTERFACE}"
      fi
    fi
    
    log "DEBUG" "========== NORTHBOUND INTERFACE CONFIGURATION COMPLETE =========="
    return 0
  else
    log "ERROR" "Failed to configure northbound interface $NORTHBOUND_INTERFACE"
    log "DEBUG" "========== NORTHBOUND INTERFACE CONFIGURATION FAILED =========="
    return 1
  fi
}

# Function to update hosts file
update_hosts_entry() {
  local ip=$1
  local hostname=$2
  
  # Sanity check
  if [ -z "$ip" ] || [ -z "$hostname" ]; then
    log "WARNING" "Cannot update hosts file: empty IP or hostname"
    return 1
  fi
  
  # Skip if IP is invalid
  if ! validate_ip "$ip"; then
    log "WARNING" "Cannot update hosts file: invalid IP $ip for $hostname"
    return 1
  fi
  
  log "DEBUG" "Updating hosts entry: $ip $hostname"
  
  # Check if entry already exists with exact match
  if grep -q "^$ip[[:space:]].*$hostname\($\|[[:space:]]\)" /etc/hosts; then
    log "DEBUG" "Hosts entry already exists for $hostname -> $ip"
    return 0
  fi
  
  # Create a temp file for hosts updates
  local TEMP_HOSTS=$(mktemp)
  
  # Remove any existing entries for this hostname
  grep -v "[[:space:]]$hostname\($\|[[:space:]]\)" /etc/hosts > "$TEMP_HOSTS"
  
  # Add the new entry
  echo "$ip $hostname" >> "$TEMP_HOSTS"
  
  # Check if the temp file was created successfully
  if [ ! -s "$TEMP_HOSTS" ]; then
    log "ERROR" "Failed to create temp hosts file"
    rm -f "$TEMP_HOSTS"
    return 1
  fi
  
  # Replace the hosts file atomically
  cat "$TEMP_HOSTS" > /etc/hosts
  if [ $? -ne 0 ]; then
    log "ERROR" "Failed to update /etc/hosts with new entry: $ip $hostname"
    rm -f "$TEMP_HOSTS"
    return 1
  fi
  
  # Clean up
  rm -f "$TEMP_HOSTS"
  
  log "SUCCESS" "Added/updated hosts entry: $ip -> $hostname"
  return 0
}

log "Starting SDN Controller entrypoint script"

# Get container information
HOSTNAME=${HOSTNAME:-$(hostname)}
CONTAINER_ID=$(cat /etc/hostname)

# Set default values for environment variables
: "${SERVICE_TYPE:=controller}"
: "${SERVICE_ID:=sdn-controller}"
: "${HOST:=0.0.0.0}"
: "${CONTROLLER_PORT:=6633}"
: "${METRICS_PORT:=9091}"
: "${LOG_LEVEL:=INFO}"
: "${NETWORK_MODE:=docker}"
: "${USE_STATIC_IP:=false}"
: "${SUBNET_PREFIX:=192.168.100}"
: "${NORTHBOUND_INTERFACE:=eth1}"
: "${NORTHBOUND_IP:=${SUBNET_PREFIX}.51}"

# Set default IPs for components if not provided in environment
: "${NODE_IP_POLICY_ENGINE:=${SUBNET_PREFIX}.20}"
: "${NODE_IP_FL_SERVER:=${SUBNET_PREFIX}.10}"
: "${NODE_IP_COLLECTOR:=${SUBNET_PREFIX}.40}"
: "${NODE_IP_OPENVSWITCH:=${SUBNET_PREFIX}.50}"
: "${NODE_IP_SDN_CONTROLLER:=${SUBNET_PREFIX}.41}"

# Verify environment variables
log "INFO" "Checking environment variables:"
log "INFO" "POLICY_ENGINE_HOST: ${POLICY_ENGINE_HOST:-not set}"
log "INFO" "NODE_IP_POLICY_ENGINE: ${NODE_IP_POLICY_ENGINE}"
log "INFO" "NODE_IP_FL_SERVER: ${NODE_IP_FL_SERVER}"
log "INFO" "NODE_IP_COLLECTOR: ${NODE_IP_COLLECTOR}"
log "INFO" "NODE_IP_OPENVSWITCH: ${NODE_IP_OPENVSWITCH}"
log "INFO" "NODE_IP_SDN_CONTROLLER: ${NODE_IP_SDN_CONTROLLER}"

# Log all environment variables starting with NODE_IP_
log "DEBUG" "All NODE_IP_ variables:"
env | grep "^NODE_IP_" | sort | tee -a "$LOG_FILE" || log "WARNING" "No NODE_IP_ variables found in environment"

log "Service type: $SERVICE_TYPE"
log "Service ID: $SERVICE_ID"
log "Controller host: $HOST"
log "Controller port: $CONTROLLER_PORT"
log "Using Static IP: $USE_STATIC_IP"

# Add hosts entries for all NODE_IP variables BEFORE network configuration
log "INFO" "Adding hosts entries for all services to /etc/hosts"

# Check current /etc/hosts content before changes
log "DEBUG" "Current /etc/hosts content before updates:"
cat /etc/hosts | tee -a "$LOG_FILE"

# Add key services explicitly
log "INFO" "Adding explicit hosts entries for critical services"

# Policy Engine - CRITICAL for controller operation
log "INFO" "Adding policy-engine: $NODE_IP_POLICY_ENGINE"
update_hosts_entry "$NODE_IP_POLICY_ENGINE" "policy-engine"

# FL Server
log "INFO" "Adding fl-server: $NODE_IP_FL_SERVER"
update_hosts_entry "$NODE_IP_FL_SERVER" "fl-server"

# Collector
log "INFO" "Adding metrics-collector: $NODE_IP_COLLECTOR"
update_hosts_entry "$NODE_IP_COLLECTOR" "metrics-collector"
update_hosts_entry "$NODE_IP_COLLECTOR" "collector"

# OpenVSwitch
log "INFO" "Adding openvswitch: $NODE_IP_OPENVSWITCH"
update_hosts_entry "$NODE_IP_OPENVSWITCH" "openvswitch"
update_hosts_entry "$NODE_IP_OPENVSWITCH" "ovs"

# Now process all NODE_IP_ variables in a loop as backup
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
  
  log "INFO" "Adding hosts entry: $hostname -> $ip_value"
  update_hosts_entry "$ip_value" "$hostname"
done

# Check /etc/hosts content after adding service entries
log "DEBUG" "Current /etc/hosts content after service entries:"
cat /etc/hosts | tee -a "$LOG_FILE"

# Get the controller IP
CONTROLLER_IP_VALUE="$NODE_IP_SDN_CONTROLLER"
if [ -z "$CONTROLLER_IP_VALUE" ]; then
  log "ERROR" "No IP found for NODE_IP_SDN_CONTROLLER environment variable"
  exit 1
fi

log "INFO" "Controller IP: $CONTROLLER_IP_VALUE"

# Set up IP and networking
if [ "$USE_STATIC_IP" = "true" ]; then
  log "Static IP mode enabled for SDN controller"
  
  # Determine interface to use
  INTERFACE="eth0"
  if [ -n "$NETWORK_INTERFACE" ]; then
    INTERFACE="$NETWORK_INTERFACE"
    log "Using configured network interface: $INTERFACE"
  fi
  
  # Get expected IP
  MY_IP="$CONTROLLER_IP_VALUE"
  
  log "Configuring interface $INTERFACE with IP $MY_IP"
  
  # Configure IP for main interface
  if assign_ip "$MY_IP" "$INTERFACE"; then
    log "SUCCESS" "Assigned IP $MY_IP to $INTERFACE"
    
    # Now configure northbound interface AFTER main interface
    log "DEBUG" "About to configure northbound interface..."
    configure_northbound_interface
    log "DEBUG" "Northbound interface configuration completed"
    
    log "Network configuration complete"
  else
    log "ERROR" "Failed to assign IP to interface $INTERFACE"
    exit 1
  fi
else
  log "Using dynamic IP assignment from Docker"
  MY_IP=$(get_container_ip)
  log "Detected IP: $MY_IP"
  
  # Configure northbound interface in dynamic mode too
  log "DEBUG" "About to configure northbound interface in dynamic mode..."
  configure_northbound_interface
  log "DEBUG" "Northbound interface configuration completed"
fi

# Show interfaces after configuration
log "INFO" "Network interfaces after configuration:"
ip addr show

# Update own IP in hosts file
update_hosts_entry "127.0.0.1" "localhost"
update_hosts_entry "$MY_IP" "$HOSTNAME"
update_hosts_entry "$MY_IP" "sdn-controller"
update_hosts_entry "$MY_IP" "controller"

# Check the hosts file content after all updates
log "DEBUG" "Final /etc/hosts content:"
cat /etc/hosts | tee -a "$LOG_FILE"

# Verify DNS resolution for important services
log "INFO" "Verifying DNS resolution for critical services:"

# Test policy-engine resolution
if getent hosts policy-engine > /dev/null; then
  POLICY_IP=$(getent hosts policy-engine | awk '{print $1}')
  log "SUCCESS" "policy-engine resolves to $POLICY_IP"
else
  log "ERROR" "policy-engine hostname does not resolve! Check /etc/hosts configuration"
  # Add it again as a last resort
  update_hosts_entry "$NODE_IP_POLICY_ENGINE" "policy-engine"
fi

# Test fl-server resolution
if getent hosts fl-server > /dev/null; then
  FL_SERVER_IP=$(getent hosts fl-server | awk '{print $1}')
  log "SUCCESS" "fl-server resolves to $FL_SERVER_IP"
else
  log "WARNING" "fl-server hostname does not resolve! Check /etc/hosts configuration"
  # Add it again as a last resort
  update_hosts_entry "$NODE_IP_FL_SERVER" "fl-server"
fi

# Test connection to policy engine before starting controller
if ping -c 1 -W 2 policy-engine >/dev/null 2>&1; then
  log "SUCCESS" "policy-engine is pingable"
else
  log "WARNING" "Cannot ping policy-engine with default route."
  # Try explicitly with northbound interface
  if ping -c 1 -W 2 -I ${NORTHBOUND_INTERFACE} policy-engine >/dev/null 2>&1; then
    log "SUCCESS" "policy-engine is pingable via ${NORTHBOUND_INTERFACE}"
  else  
    log "WARNING" "Cannot ping policy-engine even via ${NORTHBOUND_INTERFACE}. This may cause controller errors."
  fi
  
  log "INFO" "Current route table:"
  ip route | tee -a "$LOG_FILE"
  
  log "INFO" "Network configuration from controller to policy-engine:"
  ip route get ${NODE_IP_POLICY_ENGINE} | tee -a "$LOG_FILE" || true
fi

# Test TCP connectivity to policy engine port
log "INFO" "Testing TCP connectivity to policy engine on port 5000"
if timeout 2 bash -c "cat < /dev/null > /dev/tcp/policy-engine/5000" 2>/dev/null; then
  log "SUCCESS" "TCP connection to policy-engine:5000 successful"
elif timeout 2 bash -c "cat < /dev/null > /dev/tcp/${NODE_IP_POLICY_ENGINE}/5000" 2>/dev/null; then
  log "SUCCESS" "TCP connection to ${NODE_IP_POLICY_ENGINE}:5000 successful"
else
  # Try with specific source interface
  if command -v curl >/dev/null 2>&1; then
    log "INFO" "Trying curl with specific interface ${NORTHBOUND_INTERFACE}"
    curl --interface ${NORTHBOUND_INTERFACE} -s -o /dev/null -w "%{http_code}" http://policy-engine:5000/health 2>/dev/null || \
    curl --interface ${NORTHBOUND_INTERFACE} -s -o /dev/null -w "%{http_code}" http://${NODE_IP_POLICY_ENGINE}:5000/health 2>/dev/null || \
    log "WARNING" "Cannot connect to policy-engine:5000 even with curl via ${NORTHBOUND_INTERFACE}"
  else
    log "WARNING" "Cannot connect to policy-engine:5000 and curl is not available for additional tests"
  fi
fi

log "Controller environment setup complete"

# Create necessary directories
mkdir -p /app/logs
mkdir -p /app/config/controller
chmod -R 777 /app/logs
chmod -R 777 /app/config

# Get the CONFIG_DIR from environment or use default
CONFIG_DIR=${CONFIG_DIR:-"/app/config"}
CONTROLLER_CONFIG_DIR=${CONTROLLER_CONFIG_DIR:-"${CONFIG_DIR}/controller"}
mkdir -p "$CONTROLLER_CONFIG_DIR"

# Generate simple configuration
GENERATED_CONFIG_PATH="${CONTROLLER_CONFIG_DIR}/controller_config.json"
log "INFO" "Generating controller configuration at $GENERATED_CONFIG_PATH"

# Create basic JSON configuration
cat > "$GENERATED_CONFIG_PATH" << EOF
{
  "controller_id": "${SERVICE_ID}",
  "host": "${HOST:-"0.0.0.0"}",
  "port": ${CONTROLLER_PORT:-6633},
  "metrics_port": ${METRICS_PORT:-9091},
  "log_level": "${LOG_LEVEL:-"INFO"}",
  "log_file": "${LOG_FILE:-"/app/logs/controller.log"}",
  "controller_ip": "${MY_IP}",
  "northbound_interface": "${NORTHBOUND_INTERFACE}",
  "northbound_ip": "${NORTHBOUND_IP}",
  "policy_engine_host": "policy-engine",
  "policy_engine_ip": "${NODE_IP_POLICY_ENGINE}",
  "policy_engine_port": ${POLICY_ENGINE_PORT:-5000}
}
EOF

# Set environment variables for Python networking
export PYTHONUNBUFFERED=1
export SDN_CONTROLLER_NORTHBOUND_INTERFACE="${NORTHBOUND_INTERFACE}"
export SDN_CONTROLLER_NORTHBOUND_IP="${NORTHBOUND_IP}"
export SDN_CONTROLLER_POLICY_ENGINE_IP="${NODE_IP_POLICY_ENGINE}"
export HTTP_PROXY=""
export HTTPS_PROXY=""
export NO_PROXY="localhost,127.0.0.1,policy-engine,${NODE_IP_POLICY_ENGINE}"

# Wait for services, if specified
if [ "$WAIT_FOR_SERVICES_REQUIRED" = "true" ] && [ -n "$WAIT_FOR_SERVICES_LIST" ]; then
    log "INFO" "Waiting for services: $WAIT_FOR_SERVICES_LIST with timeout $WAIT_FOR_SERVICES_TIMEOUT seconds"
    # Assuming wait-for-it.sh or similar script is available and in PATH
    # Example: wait-for-it.sh policy-engine:5000 -t $WAIT_FOR_SERVICES_TIMEOUT
    # This part needs to be adapted based on the actual wait script used.
    # For now, we'll just log that we would wait.
    IFS=',' read -ra SERVICES_TO_WAIT <<< "$WAIT_FOR_SERVICES_LIST"
    for SERVICE in "${SERVICES_TO_WAIT[@]}"; do
        log "INFO" "Simulating wait for $SERVICE..."
        # In a real scenario, you'd use something like:
        # timeout $WAIT_FOR_SERVICES_TIMEOUT /usr/local/bin/wait-for-it.sh $SERVICE -t $WAIT_FOR_SERVICES_TIMEOUT --strict -- echo "$SERVICE is up"
        # if [ $? -ne 0 ]; then
        #   log "ERROR" "Service $SERVICE did not become available in time. Exiting."
        #   exit 1
        # fi
    done
    log "INFO" "All required services are assumed to be up."
fi

# Check connectivity to Policy Engine
log "INFO" "Testing TCP connectivity to policy engine on port ${POLICY_ENGINE_PORT:-5000}"
if [ -n "$NODE_IP_POLICY_ENGINE" ]; then
    if command -v curl >/dev/null 2>&1; then
      MAX_RETRIES=5
      RETRY_INTERVAL=5 # seconds
      RETRY_COUNT=0
      CONNECTED_TO_PE=false

      log "INFO" "Attempting to connect to Policy Engine (http://${NODE_IP_POLICY_ENGINE}:${POLICY_ENGINE_PORT:-5000}/health) via ${NORTHBOUND_INTERFACE:-eth0}, retries: $MAX_RETRIES"
      
      # Check if the specified northbound interface exists
      NORTHBOUND_IF_TO_USE="${NORTHBOUND_INTERFACE:-eth0}"
      CURL_INTERFACE_OPT=""
      if ip link show "$NORTHBOUND_IF_TO_USE" > /dev/null 2>&1; then
          log "DEBUG" "Northbound interface $NORTHBOUND_IF_TO_USE exists. Using --interface option."
          CURL_INTERFACE_OPT="--interface $NORTHBOUND_IF_TO_USE"
      else
          log "WARNING" "Specified northbound interface $NORTHBOUND_IF_TO_USE does not exist. Will attempt connection using default route."
          # Keep CURL_INTERFACE_OPT empty
      fi
      
      while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        # Use NODE_IP_POLICY_ENGINE for direct IP connection
        # Use $CURL_INTERFACE_OPT which is either empty or --interface ethX
        HTTP_CODE=$(curl $CURL_INTERFACE_OPT -s -o /dev/null -w "%{http_code}" "http://${NODE_IP_POLICY_ENGINE}:${POLICY_ENGINE_PORT:-5000}/health" --connect-timeout 3 --max-time 5)
        if [ "$HTTP_CODE" -eq 200 ]; then
          log "SUCCESS" "Successfully connected to Policy Engine (HTTP $HTTP_CODE)"
          CONNECTED_TO_PE=true
          break
        else
          log "WARNING" "Failed to connect to Policy Engine (Attempt $(($RETRY_COUNT + 1))/$MAX_RETRIES, HTTP Code: $HTTP_CODE). Retrying in $RETRY_INTERVAL seconds..."
          RETRY_COUNT=$(($RETRY_COUNT + 1))
          sleep $RETRY_INTERVAL
        fi
      done

      if [ "$CONNECTED_TO_PE" = "false" ]; then
        log "ERROR" "Could not connect to Policy Engine at http://${NODE_IP_POLICY_ENGINE}:${POLICY_ENGINE_PORT:-5000}/health after $MAX_RETRIES attempts."
        # Depending on requirements, you might want to exit here if PE is critical at startup
        # log "INFO" "Proceeding with startup despite Policy Engine connection failure during entrypoint check."
      fi
    elif command -v nc >/dev/null 2>&1; then
        log "INFO" "curl not found. Using nc to check Policy Engine connectivity to ${NODE_IP_POLICY_ENGINE}:${POLICY_ENGINE_PORT:-5000}"
        MAX_RETRIES_NC=5
        RETRY_INTERVAL_NC=5
        RETRY_COUNT_NC=0
        CONNECTED_VIA_NC=false
        while [ $RETRY_COUNT_NC -lt $MAX_RETRIES_NC ]; do
            if nc -z -w3 "${NODE_IP_POLICY_ENGINE}" "${POLICY_ENGINE_PORT:-5000}"; then
                log "SUCCESS" "Successfully connected to Policy Engine using nc."
                CONNECTED_VIA_NC=true
                break
            else
                log "WARNING" "Failed to connect to Policy Engine using nc (Attempt $(($RETRY_COUNT_NC + 1))/$MAX_RETRIES_NC). Retrying in $RETRY_INTERVAL_NC seconds..."
                RETRY_COUNT_NC=$(($RETRY_COUNT_NC + 1))
                sleep $RETRY_INTERVAL_NC
            fi
        done
        if [ "$CONNECTED_VIA_NC" = "false" ]; then
            log "ERROR" "Could not connect to Policy Engine using nc after $MAX_RETRIES_NC attempts."
        fi
    else
        log "WARNING" "Neither curl nor nc found, cannot check Policy Engine connectivity."
    fi
else
    log "WARNING" "NODE_IP_POLICY_ENGINE not set, skipping direct Policy Engine connectivity check."
fi

# Start the main controller application (Python script)
# Ensure environment variables are available for the python script
export PYTHONPATH=/app:$PYTHONPATH

if [ -f "/app/src/networking/sdn/controller_server.py" ]; then
  log "INFO" "Starting controller from /app/src/networking/sdn/controller_server.py"
  cd /app && PYTHONPATH=/app python -u /app/src/networking/sdn/controller_server.py --ryu-of-port "$CONTROLLER_PORT" --config "$GENERATED_CONFIG_PATH" &
elif [ -f "/app/main.py" ]; then
  log "INFO" "Starting controller from /app/main.py"
  cd /app && PYTHONPATH=/app python -u /app/main.py --controller --config "$GENERATED_CONFIG_PATH" &
elif [ -n "$CONTROLLER_ENTRYPOINT" ] && [ -f "$CONTROLLER_ENTRYPOINT" ]; then
  log "INFO" "Starting controller from $CONTROLLER_ENTRYPOINT"
  cd /app && PYTHONPATH=/app python -u "$CONTROLLER_ENTRYPOINT" --config "$GENERATED_CONFIG_PATH" &
else
  log "ERROR" "No controller entry point found"
  exit 1
fi

# Keep the container running
log "INFO" "Controller started, keeping container running"
tail -f /dev/null
