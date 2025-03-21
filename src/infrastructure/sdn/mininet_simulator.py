"""
Mininet Network Simulator Implementation

This module provides an implementation of the INetworkSimulator interface using Mininet.
"""
import os
import json
import time
import logging
import subprocess
import threading
from typing import Dict, Any, List, Optional, Tuple

from src.domain.interfaces.network_simulator import INetworkSimulator

logger = logging.getLogger(__name__)


class MininetSimulator(INetworkSimulator):
    """Implementation of INetworkSimulator using Mininet."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the Mininet simulator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.mininet_path = self.config.get("mininet_path", "mn")
        self.custom_script_path = self.config.get("custom_script_path", None)
        self.log_file = self.config.get("log_file", "mininet.log")
        self.topology = None
        self.process = None
        self.running = False
        self.status = {"state": "stopped", "start_time": None, "metrics": {}}
        self.clients = {}
        
        logger.info("Initialized Mininet simulator")
    
    def create_topology(self, topology_config: Dict[str, Any]) -> bool:
        """
        Create a network topology based on configuration.
        
        Args:
            topology_config: Topology configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate topology type
            topo_type = topology_config.get("type", "single")
            if topo_type not in ["single", "linear", "tree", "custom"]:
                logger.error(f"Unsupported topology type: {topo_type}")
                return False
            
            self.topology = topology_config
            logger.info(f"Created {topo_type} topology configuration")
            
            # If we have a custom topology, generate a Python script
            if topo_type == "custom" and self.custom_script_path:
                self._generate_custom_topology_script()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to create topology: {e}")
            return False
    
    def _generate_custom_topology_script(self) -> None:
        """Generate a Python script for custom topology."""
        switches = self.topology.get("switches", [])
        hosts = self.topology.get("hosts", [])
        links = self.topology.get("links", [])
        
        script = f"""#!/usr/bin/env python
from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
import sys

def custom_topology():
    # Create network with remote controller
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink)
    
    # Add controllers
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)
    
    # Add switches
    switches = {{}}
"""
        
        # Add switches
        for s in switches:
            script += f"    s{s['id']} = net.addSwitch('s{s['id']}')\n"
            script += f"    switches['s{s['id']}'] = s{s['id']}\n"
        
        script += "\n    # Add hosts\n"
        # Add hosts
        for h in hosts:
            ip = h.get("ip", "")
            if ip:
                script += f"    h{h['id']} = net.addHost('h{h['id']}', ip='{ip}')\n"
            else:
                script += f"    h{h['id']} = net.addHost('h{h['id']}')\n"
        
        script += "\n    # Add links\n"
        # Add links
        for link in links:
            src = link["source"]
            dst = link["target"]
            params = ""
            
            # Add link parameters if specified
            if "bw" in link:
                params += f"bw={link['bw']}"
            if "delay" in link:
                if params:
                    params += ", "
                params += f"delay='{link['delay']}'"
            if "loss" in link:
                if params:
                    params += ", "
                params += f"loss={link['loss']}"
            
            if params:
                script += f"    net.addLink({src}, {dst}, {params})\n"
            else:
                script += f"    net.addLink({src}, {dst})\n"
        
        script += """
    # Build and start network
    net.build()
    net.start()
    
    # If arguments were provided, don't start CLI
    if len(sys.argv) > 1 and sys.argv[1] == '--no-cli':
        pass
    else:
        CLI(net)
    
    # Return network for further use
    return net

if __name__ == '__main__':
    setLogLevel('info')
    net = custom_topology()
    
    # Keep running if --no-cli flag is used
    if len(sys.argv) > 1 and sys.argv[1] == '--no-cli':
        try:
            print("Network running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    # Cleanup
    net.stop()
"""
        
        # Write the script to file
        with open(self.custom_script_path, 'w') as f:
            f.write(script)
        
        # Make it executable
        os.chmod(self.custom_script_path, 0o755)
        logger.info(f"Generated custom topology script at {self.custom_script_path}")
    
    def start_simulation(self) -> bool:
        """
        Start the network simulation.
        
        Returns:
            True if successful, False otherwise
        """
        if self.running:
            logger.warning("Simulation already running")
            return True
        
        try:
            # Build command based on topology type
            topo_type = self.topology.get("type", "single")
            cmd = []
            
            if topo_type == "custom" and self.custom_script_path:
                cmd = [self.custom_script_path, "--no-cli"]
            else:
                cmd = [
                    self.mininet_path,
                    "--topo", topo_type
                ]
                
                # Add parameters specific to topology type
                if topo_type == "linear":
                    cmd.extend(["--switch", "ovs,protocols=OpenFlow13"])
                    cmd.extend(["--controller", "remote"])
                    
                    # Add number of switches
                    switches = self.topology.get("switches", 3)
                    cmd.append(str(switches))
                
                elif topo_type == "tree":
                    cmd.extend(["--switch", "ovs,protocols=OpenFlow13"])
                    cmd.extend(["--controller", "remote"])
                    
                    # Add depth and fanout
                    depth = self.topology.get("depth", 2)
                    fanout = self.topology.get("fanout", 2)
                    cmd.extend([str(depth), str(fanout)])
            
            # Start Mininet process
            with open(self.log_file, 'w') as log:
                self.process = subprocess.Popen(
                    cmd, 
                    stdout=log, 
                    stderr=log, 
                    preexec_fn=os.setsid
                )
            
            # Update status
            self.running = True
            self.status = {
                "state": "running",
                "start_time": time.time(),
                "topology": topo_type,
                "metrics": {}
            }
            
            logger.info(f"Started {topo_type} topology simulation")
            
            # Apply network conditions
            self._apply_network_conditions()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to start simulation: {e}")
            return False
    
    def _apply_network_conditions(self) -> None:
        """Apply configured network conditions."""
        if not self.topology or not self.running:
            return
        
        # Apply link conditions from topology
        links = self.topology.get("links", [])
        for link in links:
            if "delay" in link:
                self.add_link_delay(link["source"], link["target"], int(float(link["delay"].replace("ms", ""))))
            
            if "loss" in link:
                self.add_link_loss(link["source"], link["target"], float(link["loss"]))
            
            if "bw" in link:
                self.set_link_bandwidth(link["source"], link["target"], int(link["bw"]))
    
    def stop_simulation(self) -> bool:
        """
        Stop the network simulation.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.running:
            logger.warning("Simulation not running")
            return True
        
        try:
            # Stop Mininet process
            if self.process:
                os.killpg(os.getpgid(self.process.pid), 9)
                self.process = None
            
            # Update status
            self.running = False
            self.status["state"] = "stopped"
            
            logger.info("Stopped simulation")
            return True
        
        except Exception as e:
            logger.error(f"Failed to stop simulation: {e}")
            return False
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get the current status of the simulation.
        
        Returns:
            Dictionary containing simulation status information
        """
        # Update runtime if running
        if self.running and self.status["start_time"]:
            self.status["runtime_seconds"] = time.time() - self.status["start_time"]
        
        return self.status
    
    def add_link_delay(self, source: str, target: str, delay_ms: int) -> bool:
        """
        Add delay to a network link.
        
        Args:
            source: Source node ID
            target: Target node ID
            delay_ms: Delay in milliseconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.running:
            logger.warning("Cannot add link delay: simulation not running")
            return False
        
        try:
            # Construct tc command to add delay
            delay_cmd = f"tc qdisc add dev {source}-{target} root netem delay {delay_ms}ms"
            self._run_mininet_cmd(delay_cmd)
            
            logger.info(f"Added {delay_ms}ms delay to link {source}-{target}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add link delay: {e}")
            return False
    
    def add_link_loss(self, source: str, target: str, loss_percentage: float) -> bool:
        """
        Add packet loss to a network link.
        
        Args:
            source: Source node ID
            target: Target node ID
            loss_percentage: Loss percentage (0-100)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.running:
            logger.warning("Cannot add link loss: simulation not running")
            return False
        
        try:
            # Construct tc command to add packet loss
            loss_cmd = f"tc qdisc add dev {source}-{target} root netem loss {loss_percentage}%"
            self._run_mininet_cmd(loss_cmd)
            
            logger.info(f"Added {loss_percentage}% packet loss to link {source}-{target}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add link loss: {e}")
            return False
    
    def set_link_bandwidth(self, source: str, target: str, bandwidth_mbps: int) -> bool:
        """
        Set bandwidth for a network link.
        
        Args:
            source: Source node ID
            target: Target node ID
            bandwidth_mbps: Bandwidth in Mbps
            
        Returns:
            True if successful, False otherwise
        """
        if not self.running:
            logger.warning("Cannot set link bandwidth: simulation not running")
            return False
        
        try:
            # Construct tc command to set bandwidth
            bw_cmd = f"tc qdisc add dev {source}-{target} root tbf rate {bandwidth_mbps}mbit burst 15000 latency 1ms"
            self._run_mininet_cmd(bw_cmd)
            
            logger.info(f"Set bandwidth to {bandwidth_mbps}Mbps for link {source}-{target}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to set link bandwidth: {e}")
            return False
    
    def _run_mininet_cmd(self, cmd: str) -> Tuple[str, str]:
        """
        Run a command in the Mininet environment.
        
        Args:
            cmd: Command to run
            
        Returns:
            Tuple of (stdout, stderr)
        """
        if not self.running:
            raise RuntimeError("Mininet is not running")
        
        full_cmd = f"mn -c && {self.mininet_path} {cmd}"
        process = subprocess.Popen(
            full_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        return stdout.decode(), stderr.decode()
    
    def add_client_node(self, client_id: str, host_config: Dict[str, Any]) -> bool:
        """
        Add a federated learning client node to the simulation.
        
        Args:
            client_id: Unique client identifier
            host_config: Host configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not self.running:
            logger.warning("Cannot add client node: simulation not running")
            return False
        
        try:
            # Add host to Mininet
            host_name = f"h{client_id}"
            ip = host_config.get("ip", "")
            
            if ip:
                cmd = f"py net.addHost('{host_name}', ip='{ip}')"
            else:
                cmd = f"py net.addHost('{host_name}')"
            
            self._run_mininet_cmd(cmd)
            
            # Connect to a switch
            switch = host_config.get("switch", "s1")
            link_cmd = f"py net.addLink('{host_name}', '{switch}')"
            self._run_mininet_cmd(link_cmd)
            
            # Start the host
            start_cmd = f"py net.get('{host_name}').start()"
            self._run_mininet_cmd(start_cmd)
            
            # Store client configuration
            self.clients[client_id] = host_config
            
            logger.info(f"Added client node {host_name} connected to {switch}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add client node: {e}")
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics from the simulation.
        
        Returns:
            Dictionary containing performance metrics
        """
        if not self.running:
            logger.warning("Cannot get performance metrics: simulation not running")
            return {}
        
        try:
            metrics = {}
            
            # Get ping times between hosts
            hosts = self.topology.get("hosts", [])
            if len(hosts) >= 2:
                ping_results = {}
                for i in range(len(hosts)):
                    for j in range(i+1, len(hosts)):
                        src = f"h{hosts[i]['id']}"
                        dst = f"h{hosts[j]['id']}"
                        ping_cmd = f"py net.get('{src}').cmd('ping -c 3 {dst}')"
                        stdout, _ = self._run_mininet_cmd(ping_cmd)
                        
                        # Parse ping results
                        lines = stdout.strip().split('\n')
                        for line in lines:
                            if "min/avg/max" in line:
                                parts = line.split('=')[1].strip().split('/')
                                ping_results[f"{src}-{dst}"] = {
                                    "min_ms": float(parts[0]),
                                    "avg_ms": float(parts[1]),
                                    "max_ms": float(parts[2])
                                }
                
                metrics["ping"] = ping_results
            
            # Get bandwidth measurements using iperf
            if len(hosts) >= 2:
                iperf_results = {}
                for i in range(len(hosts)):
                    for j in range(i+1, len(hosts)):
                        src = f"h{hosts[i]['id']}"
                        dst = f"h{hosts[j]['id']}"
                        
                        # Start iperf server on dst
                        server_cmd = f"py net.get('{dst}').cmd('iperf -s -p 5001 &')"
                        self._run_mininet_cmd(server_cmd)
                        
                        # Wait for server to start
                        time.sleep(1)
                        
                        # Run iperf client on src
                        client_cmd = f"py net.get('{src}').cmd('iperf -c {dst} -p 5001 -t 2')"
                        stdout, _ = self._run_mininet_cmd(client_cmd)
                        
                        # Kill iperf server
                        kill_cmd = f"py net.get('{dst}').cmd('pkill -f \"iperf -s\"')"
                        self._run_mininet_cmd(kill_cmd)
                        
                        # Parse iperf results
                        lines = stdout.strip().split('\n')
                        for line in lines:
                            if "Mbits/sec" in line:
                                parts = line.split()
                                for i, part in enumerate(parts):
                                    if part == "Mbits/sec":
                                        iperf_results[f"{src}-{dst}"] = {
                                            "bandwidth_mbps": float(parts[i-1])
                                        }
                
                metrics["bandwidth"] = iperf_results
            
            # Update status with metrics
            self.status["metrics"] = metrics
            
            return metrics
        
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}
    
    def save_simulation_state(self, file_path: str) -> bool:
        """
        Save the current simulation state to a file.
        
        Args:
            file_path: Path to save the simulation state
            
        Returns:
            True if successful, False otherwise
        """
        try:
            state = {
                "status": self.status,
                "topology": self.topology,
                "clients": self.clients,
                "running": self.running
            }
            
            with open(file_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Saved simulation state to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save simulation state: {e}")
            return False
    
    def load_simulation_state(self, file_path: str) -> bool:
        """
        Load a simulation state from a file.
        
        Args:
            file_path: Path to load the simulation state from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Stop current simulation if running
            if self.running:
                self.stop_simulation()
            
            # Load state from file
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            self.status = state.get("status", {})
            self.topology = state.get("topology", {})
            self.clients = state.get("clients", {})
            
            # Start simulation if it was running
            if state.get("running", False):
                self.start_simulation()
            
            logger.info(f"Loaded simulation state from {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load simulation state: {e}")
            return False 