#!/bin/bash
# Streamlined entrypoint script for OpenVSwitch container

# === BASIC SETUP ===
set -e
trap 'echo "Error on line $LINENO"; exit 1' ERR

# Setup logging
LOGS_DIR="/app/logs"
mkdir -p "$LOGS_DIR"
LOG_FILE="$LOGS_DIR/openvswitch.log"
touch $LOG_FILE
chmod 777 "$LOG_FILE"
chmod -R 777 /app/logs

set +e

# === CONFIGURATION ===
MAIN_BRIDGE="br0"
DEFAULT_OF_VERSION="OpenFlow13"
DEFAULT_CONTROLLER_PORT=6633
RECONNECT_INTERVAL=10  # Seconds between reconnection attempts
INACTIVITY_PROBE=15000 # Milliseconds (15s) for inactivity probe
BRIDGE_MGMT_IP="192.168.100.61/24" # IP for the bridge's management interface (br0_int or br0_tap)

# === UTILITY FUNCTIONS ===

# Log function
log() {
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  local level=${1:-INFO}
  local message=$2
  if [ "$#" -eq 1 ]; then
    message=$level
    level="INFO"
  fi
  echo "[$timestamp] [OVS] [$level] $message" | tee -a "$LOG_FILE"
}

# Function to validate IP addresses
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

# Function to update hosts file with proper error handling
update_hosts_entry() {
  local ip=$1
  local hostname=$2
  
  # Skip if IP is invalid
  if ! validate_ip "$ip"; then
    log "WARNING" "Invalid IP for hosts entry: $ip, skipping"
    return 1
  fi
  
  # Create temp file for hosts updates
  TEMP_HOSTS=$(mktemp)
  if [ -z "$TEMP_HOSTS" ] || [ ! -f "$TEMP_HOSTS" ]; then
    log "ERROR" "Failed to create temporary file for hosts update."
    # Do not exit, as this is not fatal for OVS operation itself
    return 1
  fi
  
  # Check if entry already exists with exact match
  if grep -q "^$ip[[:space:]].*$hostname\\($\\|[[:space:]]\\)" /etc/hosts; then
    log "DEBUG" "Hosts entry already exists for $hostname -> $ip"
    rm -f "$TEMP_HOSTS"
    return 0
  fi
  
  # Remove any existing entries for this hostname
  grep -v "[[:space:]]$hostname\\($\\|[[:space:]]\\)" /etc/hosts > "$TEMP_HOSTS"
  echo "$ip $hostname" >> "$TEMP_HOSTS"
  if ! cp "$TEMP_HOSTS" /etc/hosts; then
    log "ERROR" "Failed to copy temporary hosts file to /etc/hosts. Check permissions."
    rm -f "$TEMP_HOSTS"
    return 1
  fi
  rm -f "$TEMP_HOSTS"
  
  log "INFO" "Added/updated hosts entry: $ip -> $hostname"
  return 0
}

# === ENVIRONMENT DETECTION ===
detect_environment() {
  # Is this running in WSL?
  if grep -qE "(Microsoft|WSL)" /proc/version 2>/dev/null; then
    log "INFO" "Detected WSL2 environment"
    IS_WSL2=true
  else
    IS_WSL2=false
  fi

  # Determine if running in GNS3
  if [ "$NETWORK_MODE" = "gns3" ] || [ "$GNS3_NETWORK" = "true" ] || env | grep -q "GNS3"; then
    log "INFO" "Detected GNS3 environment"
    IS_GNS3=true
  else
    log "INFO" "Detected local/compose environment"
    IS_GNS3=false
  fi

  export IS_WSL2 IS_GNS3
}

# === NETWORK SETUP ===

# Build IP map from environment variables
build_ip_map() {
  log "INFO" "Building IP map from environment variables"
  IP_MAP=""
  for var in $(env | grep "^NODE_IP_" | sort); do
    varname=$(echo "$var" | cut -d= -f1)
    ip_value=$(echo "$var" | cut -d= -f2)
    
    if [ -z "$ip_value" ] || ! validate_ip "$ip_value"; then
      log "WARNING" "Invalid IP in $varname: $ip_value, skipping"
      continue
    fi
    
    component=$(echo "$varname" | sed "s/^NODE_IP_//" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
    
    if [ -n "$component" ]; then
      if [ -n "$IP_MAP" ]; then
        IP_MAP="${IP_MAP},${component}:${ip_value}"
      else
        IP_MAP="${component}:${ip_value}"
      fi
      log "INFO" "Added $component:$ip_value to IP map from $varname"
    fi
  done

  if [ -n "$IP_MAP" ]; then
    log "SUCCESS" "IP map is available: $IP_MAP"
  else
    # This might not be an error if IPs are configured differently, but useful for discovery
    log "WARNING" "IP map from NODE_IP_ variables is empty."
  fi
}

# Configure static IP if required
configure_static_ip() {
  if [ "$USE_STATIC_IP" != "true" ]; then
    return 0
  fi

  log "INFO" "Static IP mode enabled, configuring network..."
  
  # Use eth0 by default for OVS host IP
  TARGET_IFACE="eth0"
  log "INFO" "Using $TARGET_IFACE as default interface for static IP assignment ($OVS_IP)"
  
  # Configure interface
  ip link set "$TARGET_IFACE" up
  # Flushing might remove IPs needed for GNS3 initial communication if not careful
  # ip addr flush dev "$TARGET_IFACE" scope global || true 
  sleep 1
  
  # Assign static IP
  log "INFO" "Assigning static IP $OVS_IP/24 to $TARGET_IFACE"
  if ip addr add "$OVS_IP/24" dev "$TARGET_IFACE"; then
    log "SUCCESS" "IP $OVS_IP successfully assigned to $TARGET_IFACE"
    
    # Set up routing
    IFS='.' read -r -a IP_PARTS <<< "$OVS_IP"
    SUBNET="${IP_PARTS[0]}.${IP_PARTS[1]}.${IP_PARTS[2]}"
    GATEWAY="${SUBNET}.1" # Common gateway convention
    log "INFO" "Network subnet: $SUBNET.0/24, Gateway: $GATEWAY"
    
    # Add default route if needed
    if ! ip route | grep -q "default"; then
      log "INFO" "Setting up default route via $GATEWAY dev $TARGET_IFACE"
      ip route add default via "$GATEWAY" dev "$TARGET_IFACE" || log "WARNING" "Failed to add default route via $GATEWAY"
    fi
    
    # Add explicit route to controller with better metrics if controller IP is known
    if [ -n "$NODE_IP_SDN_CONTROLLER" ] && validate_ip "$NODE_IP_SDN_CONTROLLER"; then
      log "INFO" "Adding direct route to SDN controller ($NODE_IP_SDN_CONTROLLER) via $TARGET_IFACE"
      ip route add "$NODE_IP_SDN_CONTROLLER/32" dev "$TARGET_IFACE" metric 10 || log "WARNING" "Failed to add direct route to controller"

      # Verify controller connectivity
      if ping -c 1 -W 2 "$NODE_IP_SDN_CONTROLLER" >/dev/null 2>&1; then
        log "SUCCESS" "SDN controller at $NODE_IP_SDN_CONTROLLER is reachable via $TARGET_IFACE"
      else 
        log "WARNING" "Cannot ping SDN controller ($NODE_IP_SDN_CONTROLLER) via $TARGET_IFACE after static IP setup"
      fi
    else
      log "INFO" "NODE_IP_SDN_CONTROLLER not set or invalid; skipping direct route and ping test here."
    fi
  else
    log "ERROR" "Failed to assign IP $OVS_IP to $TARGET_IFACE. Check if IP is already in use or interface issues."
    # This could be a fatal error for OVS functionality if eth0 is critical.
  fi
}

# Update hosts file with node information
update_hosts_file() {
  log "INFO" "Adding hosts entries from NODE_IP_ variables"
  for var in $(env | grep "^NODE_IP_" | sort); do
    varname=$(echo "$var" | cut -d= -f1)
    ip_value=$(echo "$var" | cut -d= -f2)
    
    hostname=$(echo "${varname#NODE_IP_}" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
    
    if [ -n "$hostname" ] && [ -n "$ip_value" ]; then
        log "INFO" "Processing hosts entry for: $hostname -> $ip_value"
        update_hosts_entry "$ip_value" "$hostname"
    fi
  done

  # Update own IP in hosts file
  update_hosts_entry "127.0.0.1" "localhost"
  if [ -n "$OVS_IP" ] && validate_ip "$OVS_IP"; then
    update_hosts_entry "$OVS_IP" "$HOSTNAME" # HOSTNAME is usually set by Docker
    update_hosts_entry "$OVS_IP" "openvswitch"
    update_hosts_entry "$OVS_IP" "ovs"
  else
    log "WARNING" "OVS_IP is not set or invalid; skipping self-referential host entries."
  fi
}

# === OVS MANAGEMENT ===

# Start OVS services (ovsdb-server and ovs-vswitchd)
start_ovs_services() {
  log "INFO" "Starting OpenVSwitch services"
  
  # Ensure required devices exist
  if [ ! -d /dev/net ]; then
    mkdir -p /dev/net
  fi
  if [ ! -c /dev/net/tun ]; then
    # Try to load tun module if not present. May fail if not permitted.
    modprobe tun 2>/dev/null || log "WARNING" "Failed to load tun module. TAP devices might not work."
    mknod /dev/net/tun c 10 200 || log "ERROR" "Failed to create /dev/net/tun device node."
  fi
  
  # Stop any existing OVS processes gracefully
  log "INFO" "Attempting to stop existing OVS processes..."
  /usr/share/openvswitch/scripts/ovs-ctl stop || log "INFO" "ovs-ctl stop reported an issue (maybe OVS wasn't running)."
  sleep 2 # Give time for processes to terminate
  
  # Start ovsdb-server first
  log "INFO" "Starting ovsdb-server..."
  if ! /usr/share/openvswitch/scripts/ovs-ctl start --system-id=random --no-ovs-vswitchd; then
    log "ERROR" "Failed to start ovsdb-server using ovs-ctl."
    cat /var/log/openvswitch/ovsdb-server.log >> "$LOG_FILE" 2>/dev/null
    exit 1
  fi
  
  # Verify ovsdb-server started
  if ! pidof ovsdb-server >/dev/null; then
    log "ERROR" "ovsdb-server process not found after start attempt!"
    cat /var/log/openvswitch/ovsdb-server.log >> "$LOG_FILE" 2>/dev/null
    exit 1
  fi
  log "SUCCESS" "ovsdb-server started successfully."
  
  # Wait for OVSDB to become responsive
  log "INFO" "Waiting for OVSDB server to become responsive..."
  max_attempts=10
  attempt=1
  while ! ovs-vsctl show > /dev/null 2>&1; do
    if [ $attempt -ge $max_attempts ]; then
      log "ERROR" "OVSDB server not responsive after $max_attempts attempts."
      exit 1
    fi
    log "INFO" "OVSDB not ready, waiting... ($attempt/$max_attempts)"
    sleep 1
    ((attempt++))
  done
  log "SUCCESS" "OVSDB server is responsive."
  
  # Configure datapath type (important for GNS3/WSL2)
  if [ "$IS_GNS3" = "true" ] || [ "$IS_WSL2" = "true" ]; then
    log "INFO" "Configuring OVS to use userspace datapath (netdev)"
    ovs-vsctl --no-wait set Open_vSwitch . other_config:datapath-type=netdev
    # Verify it was set
    current_dp_type=$(ovs-vsctl --timeout=5 get Open_vSwitch . other_config:datapath-type 2>/dev/null | tr -d '\"')
    if [ "$current_dp_type" = "netdev" ]; then
        log "INFO" "Successfully verified other_config:datapath-type is set to 'netdev' in DB."
    else
        log "WARNING" "Failed to verify other_config:datapath-type is 'netdev' in DB. Found '$current_dp_type'. ovs-ctl might default to system datapath."
    fi
  else
    log "INFO" "Configuring OVS to use system datapath (likely kernel)"
    ovs-vsctl --no-wait set Open_vSwitch . other_config:datapath-type=system
    current_dp_type=$(ovs-vsctl --timeout=5 get Open_vSwitch . other_config:datapath-type 2>/dev/null | tr -d '\"')
    if [ "$current_dp_type" = "system" ]; then
        log "INFO" "Successfully verified other_config:datapath-type is set to 'system' in DB."
    else
        log "WARNING" "Failed to verify other_config:datapath-type is 'system' in DB. Found '$current_dp_type'."
    fi
  fi
  
  log "INFO" "Attempting to disable DPDK initialization..."
  ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-init=false
  
  # Start ovs-vswitchd
  log "INFO" "Starting ovs-vswitchd..."
  if [ "$IS_GNS3" = "true" ] || [ "$IS_WSL2" = "true" ]; then
    log "INFO" "Using direct userspace approach for starting ovs-vswitchd (for GNS3/WSL2)"
    OVS_VSWITCHD_PATH=$(which ovs-vswitchd 2>/dev/null || echo "/usr/sbin/ovs-vswitchd")
    if [ ! -x "$OVS_VSWITCHD_PATH" ]; then
      log "ERROR" "Cannot find executable ovs-vswitchd. Searched at $OVS_VSWITCHD_PATH"
      exit 1
    fi
    
    # Create required directories
    mkdir -p /var/run/openvswitch
    
    # Start with direct command rather than ovs-ctl
    # Flags for userspace operation:
    # --disable-system: prevents attempts to use kernel datapath
    # --pidfile: ensures proper PID tracking for later management
    log "INFO" "Starting ovs-vswitchd directly with userspace-specific flags"
    
    # Define log file and PID file paths
    VSWITCHD_LOG="/var/log/openvswitch/ovs-vswitchd.log"
    VSWITCHD_PID="/var/run/openvswitch/ovs-vswitchd.pid"
    
    # Ensure log directory exists
    mkdir -p /var/log/openvswitch
    
    # Simplify the command with only essential flags, redirecting both stdout and stderr
    log "INFO" "Launching with simplified command: $OVS_VSWITCHD_PATH --pidfile=$VSWITCHD_PID unix:/var/run/openvswitch/db.sock"
    $OVS_VSWITCHD_PATH --pidfile="$VSWITCHD_PID" unix:/var/run/openvswitch/db.sock > "$VSWITCHD_LOG" 2>&1 &
    
    # Store PID and verify process started
    VSWITCHD_PID_VALUE=$!
    sleep 3 # Give it time to initialize or fail
    
    if kill -0 "$VSWITCHD_PID_VALUE" 2>/dev/null; then
      log "SUCCESS" "ovs-vswitchd started directly with PID $VSWITCHD_PID_VALUE."
      
      # Update PID file with actual PID if needed
      echo "$VSWITCHD_PID_VALUE" > "$VSWITCHD_PID"
    else
      log "ERROR" "Failed to start ovs-vswitchd directly. Dumping logs:"
      if [ -f "$VSWITCHD_LOG" ]; then
        cat "$VSWITCHD_LOG" >> "$LOG_FILE"
        log "ERROR" "===== End of ovs-vswitchd log ====="
      else
        log "ERROR" "No log file found at $VSWITCHD_LOG"
      fi
      
      # Try alternative method as a fallback - sometimes privs are needed
      log "INFO" "Trying fallback method with basic flags..."
      $OVS_VSWITCHD_PATH unix:/var/run/openvswitch/db.sock > "$VSWITCHD_LOG" 2>&1 &
      VSWITCHD_PID_VALUE=$!
      sleep 3
      
      if kill -0 "$VSWITCHD_PID_VALUE" 2>/dev/null; then
        log "SUCCESS" "Fallback method worked! ovs-vswitchd started with PID $VSWITCHD_PID_VALUE."
        echo "$VSWITCHD_PID_VALUE" > "$VSWITCHD_PID"
      else
        log "ERROR" "Fallback method also failed. Dumping logs:"
        if [ -f "$VSWITCHD_LOG" ]; then
          cat "$VSWITCHD_LOG" >> "$LOG_FILE"
        fi
        exit 1
      fi
    fi
  else
    log "INFO" "Using standard approach for starting ovs-vswitchd"
    if ! /usr/share/openvswitch/scripts/ovs-ctl start --no-ovsdb-server; then
      log "ERROR" "Failed to start ovs-vswitchd using ovs-ctl."
      cat /var/log/openvswitch/ovs-vswitchd.log >> "$LOG_FILE" 2>/dev/null
      exit 1
    fi
  fi
  
  # Verify ovs-vswitchd started (both methods should create a process)
  sleep 2 # Give it a moment to initialize
  if ! pidof ovs-vswitchd >/dev/null; then
    log "ERROR" "ovs-vswitchd process not found after start attempt!"
    cat /var/log/openvswitch/ovs-vswitchd.log >> "$LOG_FILE" 2>/dev/null
    exit 1
  fi
  log "SUCCESS" "ovs-vswitchd started successfully."
}

# Find the SDN controller URL
find_controller_url() {
  # Set controller port based on environment variables or defaults
  CONTROLLER_PORT=${SDN_CONTROLLER_PORT:-$DEFAULT_CONTROLLER_PORT}
  log "INFO" "Using controller port: $CONTROLLER_PORT"
  
  # First try to get controller IP from specific environment variable
  if [ -n "$NODE_IP_SDN_CONTROLLER" ] && validate_ip "$NODE_IP_SDN_CONTROLLER"; then
    CONTROLLER_URL="tcp:$NODE_IP_SDN_CONTROLLER:$CONTROLLER_PORT"
    log "INFO" "Controller target identified from NODE_IP_SDN_CONTROLLER: $CONTROLLER_URL"
    
    # Test connectivity (brief timeout)
    log "INFO" "Testing controller connection to $NODE_IP_SDN_CONTROLLER:$CONTROLLER_PORT"
    if timeout 3 bash -c "</dev/null >/dev/tcp/$NODE_IP_SDN_CONTROLLER/$CONTROLLER_PORT" 2>/dev/null; then
      log "SUCCESS" "Controller port is open at $NODE_IP_SDN_CONTROLLER:$CONTROLLER_PORT"
      update_hosts_entry "$NODE_IP_SDN_CONTROLLER" "sdn-controller"
      return 0
    else
      log "WARNING" "Controller port at $NODE_IP_SDN_CONTROLLER:$CONTROLLER_PORT did not respond to initial check."
      # Proceed anyway, OVS will handle reconnections
    fi
    return 0 # Return 0 as we have a candidate URL
  fi
  
  # Fallback: Try to find controller in IP_MAP if direct env var failed or wasn't set
  if [ -n "$IP_MAP" ]; then
    IFS=',' read -ra MAPPINGS <<< "$IP_MAP"
    for mapping in "${MAPPINGS[@]}"; do
      component=$(echo "$mapping" | cut -d':' -f1 | tr '[:upper:]' '[:lower:]')
      ip=$(echo "$mapping" | cut -d':' -f2)
      
      if [[ "$component" == "sdn-controller" || "$component" == "controller" ]] && validate_ip "$ip"; then
        CONTROLLER_URL="tcp:$ip:$CONTROLLER_PORT"
        log "INFO" "Found controller in IP map: $CONTROLLER_URL"
        update_hosts_entry "$ip" "sdn-controller"
        return 0
      fi
    done
  fi
  
  # If we get here, no controller was found
  log "WARNING" "No SDN controller explicitly found via environment variables or IP map. OVS will operate without a pre-defined controller target if not set later."
  CONTROLLER_URL=""
  return 1
}

# Create the main OVS bridge with proper configuration
create_bridge() {
  local bridge_name="$MAIN_BRIDGE"
  
  log "INFO" "Creating bridge $bridge_name"
  
  # Delete bridge if it exists (clean start)
  ovs-vsctl --if-exists del-br "$bridge_name" || true
  sleep 1 # Allow time for deletion to complete
  
  # Create bridge
  log "INFO" "Adding bridge $bridge_name to OVS"
  if ! ovs-vsctl add-br "$bridge_name"; then
      log "ERROR" "Failed to create bridge $bridge_name. Dumping ovs-vswitchd.log:"
      cat /var/log/openvswitch/ovs-vswitchd.log >> "$LOG_FILE" 2>/dev/null
      return 1
  fi

  # If GNS3/WSL2, ensure netdev datapath type is set on the bridge itself
  if [ "$IS_GNS3" = "true" ] || [ "$IS_WSL2" = "true" ]; then
    log "INFO" "Setting datapath_type=netdev for bridge $bridge_name (GNS3/WSL2)"
    ovs-vsctl set bridge "$bridge_name" datapath_type=netdev
  fi
  
  # Set OpenFlow protocol version
  log "INFO" "Setting OpenFlow protocol for $bridge_name to $DEFAULT_OF_VERSION"
  if ! ovs-vsctl set bridge "$bridge_name" protocols="$DEFAULT_OF_VERSION"; then
    log "WARNING" "Failed to set OpenFlow protocol version on $bridge_name"
  fi
  
  # Configure bridge for out-of-band control since eth0 (OVS host IP) is separate
  log "INFO" "Configuring bridge $bridge_name for out-of-band control"
  ovs-vsctl set bridge "$bridge_name" other-config:disable-in-band=true
  
  # Set secure fail mode (controller is mandatory)
  ovs-vsctl set-fail-mode "$bridge_name" secure
  
  # Create an internal port for the bridge (e.g., br0_int) for GNS3/netdev
  if [ "$IS_GNS3" = "true" ] || [ "$IS_WSL2" = "true" ]; then
    local internal_port_name="${bridge_name}_int"
    log "INFO" "Creating internal port $internal_port_name for bridge $bridge_name"
    ovs-vsctl --may-exist add-port "$bridge_name" "$internal_port_name" -- set interface "$internal_port_name" type=internal

    log "INFO" "Waiting a few seconds for $internal_port_name to appear in the system..."
    sleep 3 # Give kernel and OVS time to sync

    if ip link show "$internal_port_name" >/dev/null 2>&1; then
      log "INFO" "Bringing up internal port $internal_port_name"
      if ip link set dev "$internal_port_name" up; then
        log "SUCCESS" "Internal port $internal_port_name is up."
        log "INFO" "Assigning IP $BRIDGE_MGMT_IP to $internal_port_name"
        if ip addr add "$BRIDGE_MGMT_IP" dev "$internal_port_name"; then
          log "SUCCESS" "Assigned IP $BRIDGE_MGMT_IP to $internal_port_name"
        else
          log "WARNING" "Failed to assign IP $BRIDGE_MGMT_IP to $internal_port_name. It might already have an IP or other issue."
        fi
      else
        log "WARNING" "Failed to bring up $internal_port_name."
      fi
    else
      log "WARNING" "Internal port $internal_port_name did not become visible in Linux. Bridge interaction from host OS might be affected."
      # Fallback to TAP device if internal port failed (optional, can be removed if br0_int is made reliable)
      local tap_port_name="${bridge_name}_tap"
      log "INFO" "Attempting to create TAP device $tap_port_name as fallback."
      ip tuntap del dev "$tap_port_name" mode tap 2>/dev/null || true
      if ip tuntap add dev "$tap_port_name" mode tap; then
          log "SUCCESS" "TAP device $tap_port_name created."
          ovs-vsctl --may-exist add-port "$bridge_name" "$tap_port_name"
          ip link set dev "$tap_port_name" up
          ip link set dev "$tap_port_name" promisc on
          # Attempt to force carrier if sysfs entry exists (best effort)
          if [ -f "/sys/class/net/${tap_port_name}/carrier" ]; then
              echo 1 > "/sys/class/net/${tap_port_name}/carrier" 2>/dev/null || true
          fi
          log "INFO" "Assigning IP $BRIDGE_MGMT_IP to $tap_port_name"
          if ip addr add "$BRIDGE_MGMT_IP" dev "$tap_port_name"; then
             log "SUCCESS" "Assigned IP $BRIDGE_MGMT_IP to $tap_port_name"
          else
             log "WARNING" "Failed to assign IP $BRIDGE_MGMT_IP to $tap_port_name."
          fi
          # Check if OVS picked it up
          if ! ovs-vsctl list-ports "$bridge_name" | grep -q "$tap_port_name"; then
            log "WARNING" "OVS does not list $tap_port_name after creation. Check OVS logs."
          fi
      else
          log "ERROR" "Failed to create TAP device $tap_port_name. Bridge will not have a host-visible IP interface."
      fi
    fi
  fi # End GNS3/WSL2 internal/TAP port creation
  
  # Verify bridge exists in OVS database
  if ovs-vsctl list-br | grep -q "$bridge_name"; then
    log "SUCCESS" "Bridge $bridge_name created and configured in OVS database"
    log "INFO" "Current OVS bridges and ports:"
    ovs-vsctl show || log "WARNING" "Failed to show OVS configuration"
    log "INFO" "Linux network interfaces (ip -br link show):"
    ip -br link show || log "WARNING" "Failed to show Linux network interfaces"
    return 0
  else
    log "ERROR" "Bridge $bridge_name not listed in OVS database after creation attempt"
    return 1
  fi
}

# Add interfaces to bridge (physical/external interfaces)
add_interfaces_to_bridge() {
  local bridge="$MAIN_BRIDGE"
  local interfaces_added=0
  
  log "INFO" "Adding external interfaces to bridge $bridge"
  
  # Make sure the bridge exists
  if ! ovs-vsctl list-br | grep -q "$bridge"; then
    log "ERROR" "Bridge $bridge does not exist, cannot add interfaces."
    return 1
  fi
  
  # eth0 is typically used for OVS host management/controller communication, not added to bridge
  log "INFO" "Ensuring $OVS_HOST_IFACE (eth0) is up for controller connectivity - NOT adding to bridge $bridge"
  ip link set "$OVS_HOST_IFACE" up || log "WARNING" "Failed to bring up $OVS_HOST_IFACE"
  
  # Add other interfaces (e.g., eth1, eth2, ...) to the bridge
  # Filter out common non-data interfaces: lo, docker*, veth*, tap*, mgmt*, $MAIN_BRIDGE, and $OVS_HOST_IFACE
  local exclude_pattern="lo\\|$OVS_HOST_IFACE\\|$MAIN_BRIDGE\\|docker.*\\|veth.*\\|tap.*\\|mgmt.*"
  
  for iface in $(ls /sys/class/net/ | grep -Ev "$exclude_pattern"); do
    if [ -d "/sys/class/net/$iface" ]; then # Check if it's a directory (i.e., an interface)
      log "INFO" "Found potential data interface: $iface"
      
      # Bring interface up and set promiscuous mode
      ip link set "$iface" promisc on || log "WARNING" "Failed to set $iface to promiscuous mode"
      ip link set "$iface" up || log "WARNING" "Failed to bring up $iface"
      
      log "INFO" "Adding interface $iface to bridge $bridge"
      if ovs-vsctl --may-exist add-port "$bridge" "$iface"; then
        log "SUCCESS" "Added interface $iface to bridge $bridge"
        interfaces_added=$((interfaces_added+1))
      else
        log "WARNING" "Failed to add $iface to bridge $bridge. Check OVS logs."
        # No retry here, ovs-vsctl add-port is usually robust if interface exists and is up.
      fi
    fi
  done
  
  if [ $interfaces_added -gt 0 ]; then
    log "INFO" "Added $interfaces_added data interface(s) to bridge $bridge"
  else
    log "WARNING" "No additional data interfaces were found or added to bridge $bridge. Ensure GNS3 links are connected."
  fi
  
  # Route to controller via eth0 should already be handled by configure_static_ip
  # if [ -n "$NODE_IP_SDN_CONTROLLER" ] && validate_ip "$NODE_IP_SDN_CONTROLLER" ; then
  #   ip route add "$NODE_IP_SDN_CONTROLLER/32" dev "$OVS_HOST_IFACE" metric 5 2>/dev/null || true # ensure
  #   log "INFO" "Ensured direct route to SDN controller ($NODE_IP_SDN_CONTROLLER) via $OVS_HOST_IFACE"
  # fi
  
  return 0
}

# Configure controller connection and settings
setup_controller() {
  local bridge="$MAIN_BRIDGE"
  
  if [ -z "$CONTROLLER_URL" ]; then
    log "WARNING" "No controller URL defined. Configuring bridge $bridge for standalone operation (fail_mode=standalone)."
    ovs-vsctl set-fail-mode "$bridge" standalone # Override secure if no controller
    return 1
  fi
  
  log "INFO" "Setting controller for $bridge to $CONTROLLER_URL"
  # Use --may-exist with del-controller then add-controller, or set-controller
  ovs-vsctl --if-exists del-controller "$bridge"
  if ! ovs-vsctl set-controller "$bridge" "$CONTROLLER_URL"; then
    log "ERROR" "Failed to set controller $CONTROLLER_URL for bridge $bridge."
    return 1
  fi
  
  # Configure controller connection parameters
  log "INFO" "Setting controller connection parameters for $bridge"
  local controller_uuid
  controller_uuid=$(ovs-vsctl get Bridge "$bridge" controller) # This gets the UUID of the controller record
  
  if [ -n "$controller_uuid" ] && [ "$controller_uuid" != "[]" ]; then
    # Strip quotes if any from the UUID (sometimes OVS returns "uuid")
    controller_uuid=$(echo "$controller_uuid" | tr -d '"')
    log "INFO" "Retrieved controller UUID: $controller_uuid. Configuring parameters."
    ovs-vsctl set Controller "$controller_uuid" connection_mode=out-of-band
    ovs-vsctl set Controller "$controller_uuid" max_backoff=10000  # Max 10s between reconnect attempts
    ovs-vsctl set Controller "$controller_uuid" inactivity_probe=30000 # 30s inactivity probe
    # Remove any local_ip/local_port restriction that might interfere
    ovs-vsctl remove Controller "$controller_uuid" local_ip 2>/dev/null || true
    ovs-vsctl remove Controller "$controller_uuid" local_port 2>/dev/null || true
    log "INFO" "Controller parameters set for UUID $controller_uuid."
  else
    log "WARNING" "Could not retrieve controller UUID for $bridge after setting controller. Advanced parameters (like out-of-band) will not be set."
  fi
  
  # Initial check for connection (don't wait too long here, monitor will handle it)
  log "INFO" "Checking initial controller connection status (short wait)..."
  sleep 3 # Brief wait
  
  if ovs-vsctl -- get controller "$bridge" is_connected 2>/dev/null | grep -q "true"; then
    log "SUCCESS" "Controller connection for $bridge appears to be established."
    log "INFO" "Flows on $bridge (should be populated by controller):"
    ovs-ofctl -O "$DEFAULT_OF_VERSION" dump-flows "$bridge" || log "WARNING" "Failed to dump flows after controller connect."
  else
    log "WARNING" "Controller connection for $bridge not established within initial check. Monitoring will continue."
    # Try alternate port if primary (6633) was used and failed, and alternate (6653) is different
    if [[ "$CONTROLLER_URL" == *":$DEFAULT_CONTROLLER_PORT" ]] && [ "$DEFAULT_CONTROLLER_PORT" -ne 6653 ]; then
      ALTERNATE_URL="${CONTROLLER_URL/:$DEFAULT_CONTROLLER_PORT/:6653}"
      log "INFO" "Initial connection failed. Trying alternate controller port: $ALTERNATE_URL"
      ovs-vsctl set-controller "$bridge" "$ALTERNATE_URL" # This will also update controller_uuid implicitly
      # Re-apply settings for the new target if needed, or rely on monitor to sort it out
      # For simplicity, we assume monitor_controller_connection will handle the new target.
      # Or, re-fetch UUID and re-apply settings here if strictness is needed.
      CONTROLLER_URL="$ALTERNATE_URL" # Update global for monitor
      sleep 3
      if ovs-vsctl -- get controller "$bridge" is_connected 2>/dev/null | grep -q "true"; then
        log "SUCCESS" "Controller connected on alternate port $ALTERNATE_URL"
      else
        log "WARNING" "Controller still not connected on alternate port $ALTERNATE_URL."
      fi
    fi
  fi
  return 0 # Even if not immediately connected, monitor will take over
}

# Monitor and maintain controller connection
monitor_controller_connection() {
  local bridge="$MAIN_BRIDGE"
  local interval="$RECONNECT_INTERVAL"
  
  log "INFO" "Starting controller connection monitoring for $bridge (interval: ${interval}s, OF: $DEFAULT_OF_VERSION)"
  
  # Run in background
  (
    set +e # Allow commands inside loop to fail without exiting subshell
    while true; do
      if [ -z "$CONTROLLER_URL" ]; then # If no controller URL was ever set
        # log "DEBUG" "Monitor: No controller URL defined, bridge $bridge likely in standalone."
        # Ensure fail_mode is standalone if no controller
        if ovs-vsctl list-br | grep -q "$bridge"; then
            current_fail_mode=$(ovs-vsctl get-fail-mode "$bridge" 2>/dev/null)
            if [ "$current_fail_mode" != "standalone" ]; then
                log "INFO" "Monitor: No controller URL defined. Setting $bridge to fail_mode=standalone."
                ovs-vsctl set-fail-mode "$bridge" standalone
            fi
        fi
        sleep "$interval"
        continue
      fi
      
      # Check if bridge exists before interacting
      if ! ovs-vsctl list-br | grep -q "$bridge"; then
        log "WARNING" "Monitor: Bridge $bridge no longer exists. Stopping monitoring for it."
        # Consider exiting this subshell if the main bridge is gone, or just sleep.
        # For now, just log and sleep. The main script might recreate it.
        sleep "$interval"
        continue
      fi

      # Check connection status
      if ovs-vsctl -- get controller "$bridge" is_connected 2>/dev/null | grep -q "true"; then
        # log "DEBUG" "Monitor: Controller for $bridge is connected."
        # Optionally, check if flows are present if controller is connected
        num_flows=$(ovs-ofctl -O "$DEFAULT_OF_VERSION" dump-flows "$bridge" 2>/dev/null | grep -cv NXST_FLOW || echo "0")
        if [ "$num_flows" -lt 1 ]; then # Expect at least one flow if controller active, or default
          log "WARNING" "Monitor: Controller for $bridge connected but few/no flows installed ($num_flows). Controller might be idle or misconfigured."
        fi
      else
        log "WARNING" "Monitor: Controller connection for $bridge lost or not established. Will ensure basic connectivity."
        # Attempt to re-establish controller or ensure settings are correct
        # ovs-vsctl set-controller "$bridge" "$CONTROLLER_URL" # Re-assert controller
        
        # Ensure fail_mode is 'secure' if we expect a controller, or 'standalone' if explicitly no controller
        # This logic is tricky: if CONTROLLER_URL is set, we want 'secure'.
        current_fail_mode=$(ovs-vsctl get-fail-mode "$bridge" 2>/dev/null)
        if [ "$current_fail_mode" != "secure" ]; then
            log "INFO" "Monitor: Controller disconnected. Setting $bridge to fail_mode=secure (expecting controller)."
            ovs-vsctl set-fail-mode "$bridge" secure
        fi
        
        # Add a simple fallback flow to allow basic L2 learning if controller is down
        # This prevents network outage if controller fails, but might conflict if controller comes back with different ideas.
        # A single, low-priority NORMAL flow is a common strategy.
        log "INFO" "Monitor: Adding/Ensuring low-priority NORMAL flow on $bridge for basic connectivity."
        ovs-ofctl -O "$DEFAULT_OF_VERSION" add-flow "$bridge" "table=0,priority=0,actions=NORMAL" >/dev/null 2>&1 || \
          log "WARNING" "Monitor: Failed to add fallback NORMAL flow to $bridge."
      fi
      
      sleep "$interval"
    done
  ) &
  
  # Save the PID for potential cleanup
  MONITOR_PID=$!
  log "INFO" "Controller monitor for $bridge started with PID $MONITOR_PID"
}


# === MAIN EXECUTION ===

# Initialize and get environment variables
log "INFO" "Starting OpenVSwitch entrypoint script (v2 streamlined)"

# Get container information and settings
HOSTNAME=${HOSTNAME:-$(hostname)} # Docker usually sets this
OVS_HOST_IFACE="eth0" # Standard interface for OVS host IP / controller communication
SERVICE_TYPE=${SERVICE_TYPE:-openvswitch}
SERVICE_ID=${SERVICE_ID:-ovs-1}
LOG_LEVEL=${LOG_LEVEL:-INFO}
NETWORK_MODE=${NETWORK_MODE:-docker} # e.g., docker, gns3
GNS3_NETWORK=${GNS3_NETWORK:-false} # More specific GNS3 flag
USE_STATIC_IP=${USE_STATIC_IP:-true} # Assume static IP for OVS host in GNS3

# Get OVS ID from SERVICE_ID if it contains a number (e.g., ovs-1 -> 1, openvswitch2 -> 2)
OVS_OFFSET=""
if [[ "$SERVICE_ID" =~ ([0-9]+)$ ]]; then
  OVS_OFFSET="${BASH_REMATCH[1]}"
fi

log "INFO" "Service type: $SERVICE_TYPE, Service ID: $SERVICE_ID, OVS Offset: $OVS_OFFSET (if any)"

# Environment detection (WSL2, GNS3)
detect_environment

# Build IP mapping from NODE_IP_xxx variables (useful for discovery and hosts file)
build_ip_map

# Determine the OVS_IP (IP for the OVS host itself, typically on eth0)
# Default to NODE_IP_OPENVSWITCH or NODE_IP_OPENVSWITCH_<offset>
OVS_IP_VAR_BASE="NODE_IP_OPENVSWITCH"
OVS_IP_VAR="$OVS_IP_VAR_BASE"
if [ -n "$OVS_OFFSET" ] && [ "$OVS_OFFSET" -ne 1 ]; then # If offset is present and not 1
  OVS_IP_VAR="${OVS_IP_VAR_BASE}_${OVS_OFFSET}"
fi
OVS_IP=${!OVS_IP_VAR} # Dereference the constructed variable name

if [ -z "$OVS_IP" ] || ! validate_ip "$OVS_IP" ; then
  log "WARNING" "No valid IP found for OVS host from $OVS_IP_VAR. Static IP config for $OVS_HOST_IFACE might fail or use DHCP."
  # If USE_STATIC_IP is true, this is a problem. For now, proceed and let configure_static_ip handle it.
  if [ "$USE_STATIC_IP" = "true" ]; then
    log "ERROR" "Static IP mode is enabled, but OVS_IP ($OVS_IP from $OVS_IP_VAR) is not set or invalid. This is critical."
    # Depending on strictness, might exit here. For now, let it try.
  fi
fi
log "INFO" "OVS Host IP target: $OVS_IP (on $OVS_HOST_IFACE from $OVS_IP_VAR)"

# Configure network with static IP for OVS host if requested (typically on eth0)
if [ "$USE_STATIC_IP" = "true" ] && [ -n "$OVS_IP" ]; then
  configure_static_ip # Uses OVS_IP and OVS_HOST_IFACE
else
  log "INFO" "Skipping static IP configuration for $OVS_HOST_IFACE (USE_STATIC_IP is '$USE_STATIC_IP' or OVS_IP is empty)."
fi

# Update /etc/hosts file with discovered node IPs
update_hosts_file

log "INFO" "OVS host network environment setup complete."

# Start OpenVSwitch services (ovsdb-server, ovs-vswitchd)
start_ovs_services # Exits on critical failure

# Find controller URL (from NODE_IP_SDN_CONTROLLER or IP_MAP)
find_controller_url # Sets $CONTROLLER_URL

# Set up the main bridge (br0)
if ! create_bridge; then # Exits on critical failure internally if bridge cant be made
    log "ERROR" "Failed to create or configure main bridge $MAIN_BRIDGE. Exiting."
    exit 1
fi

# Add external/data interfaces to the bridge (eth1, eth2, etc.)
add_interfaces_to_bridge # Uses OVS_HOST_IFACE to exclude it

# Set up controller connection for the main bridge
setup_controller # Uses $CONTROLLER_URL, sets fail_mode, configures params

# Monitor controller connection in the background
monitor_controller_connection # Starts background process, adds fallback flow if controller lost

# Display final OVS status
log "INFO" "Final OVS configuration status for $MAIN_BRIDGE:"
ovs-vsctl show || log "WARNING" "Failed to show final OVS status."
log "INFO" "Current flow table for $MAIN_BRIDGE (OpenFlow: $DEFAULT_OF_VERSION):"
if ovs-vsctl list-br | grep -q "$MAIN_BRIDGE"; then
  ovs-ofctl -O "$DEFAULT_OF_VERSION" dump-flows "$MAIN_BRIDGE" 2>/dev/null || \
    log "WARNING" "Failed to dump flows. Bridge $MAIN_BRIDGE might not be fully operational or OF version issue."
else
  log "WARNING" "Cannot dump flows, bridge $MAIN_BRIDGE not found in OVS database at script end."
fi

# Keep the container running by tailing a log or a sleep loop
log "INFO" "OpenVSwitch setup complete. Container is now active. Tailing OVS logs..."

# Handle termination signals gracefully
trap 'log "INFO" "Received shutdown signal. Killing monitor PID $MONITOR_PID and exiting..."; kill $MONITOR_PID 2>/dev/null; exit 0' SIGTERM SIGINT

# Tail OVS logs to keep container running and provide live OVS daemon logs
# Ensure the log file exists and is readable
touch /var/log/openvswitch/ovs-vswitchd.log
tail -f /var/log/openvswitch/ovs-vswitchd.log &
wait $! # Wait for tail to exit (e.g. on signal)

log "INFO" "OpenVSwitch entrypoint script finished."
exit 0
