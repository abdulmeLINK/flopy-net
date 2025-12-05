"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
Port management utilities for GNS3 network simulations.

This module provides comprehensive platform-specific functions for managing 
and freeing up ports used by GNS3, including NIO UDP ports.
"""

import logging
import platform
import subprocess
import time
import traceback
import re
from typing import Tuple

logger = logging.getLogger(__name__)


class PortManager:
    """Platform-specific port management operations for GNS3."""
    
    def __init__(self):
        """Initialize the port manager."""
        self.system = platform.system()
    
    def free_ports(self, min_port: int = 5000, max_port: int = 10000, timeout: int = 30) -> int:
        """
        Free ports in the specified range that might be in use.
        This is a platform-specific function that calls the appropriate implementation.
        
        Args:
            min_port: Minimum port in the range to check
            max_port: Maximum port in the range to check
            timeout: Maximum time to spend on this operation
            
        Returns:
            Number of ports freed
        """
        logger.info(f"Freeing ports in range {min_port}-{max_port} with {timeout}s timeout")
        
        start_time = time.time()
        ports_freed = 0
        
        try:
            if self.system == 'Windows':
                ports_freed = self._free_ports_windows(min_port, max_port, timeout)
            elif self.system == 'Linux':
                ports_freed = self._free_ports_linux(min_port, max_port, timeout)
            elif self.system == 'Darwin':  # macOS
                ports_freed = self._free_ports_macos(min_port, max_port, timeout)
            else:
                logger.warning(f"Unsupported platform: {self.system}, cannot free ports")
                return 0
                
            elapsed = time.time() - start_time
            logger.info(f"Freed {ports_freed} ports in {elapsed:.1f}s")
            return ports_freed
            
        except Exception as e:
            logger.error(f"Error freeing ports: {e}")
            logger.error(traceback.format_exc())
            return 0
    
    def free_nio_udp_ports(self) -> int:
        """
        Free UDP ports specifically used by GNS3 NIOs (Network I/O).
        GNS3 uses UDP ports in the 10000-20000 range for NIOs between devices.
        
        Returns:
            int: Number of ports freed
        """
        try:
            logger.info("Freeing UDP ports used by GNS3 NIOs...")
            if self.system == "Windows":
                return self._free_nio_udp_ports_windows()
            elif self.system == "Linux":
                return self._free_nio_udp_ports_linux()
            elif self.system == "Darwin":  # macOS
                return self._free_nio_udp_ports_macos()
            else:
                logger.error(f"Unsupported OS for NIO UDP port freeing: {self.system}")
                return 0
        except Exception as e:
            logger.error(f"Error freeing GNS3 NIO UDP ports: {e}")
            return 0
    
    def _free_nio_udp_ports_windows(self) -> int:
        """
        Free UDP ports used by GNS3 NIOs on Windows.
        
        Returns:
            int: Number of ports freed
        """
        ports_freed = 0
        try:
            # Check if we have admin privileges first
            has_admin = False
            try:
                subprocess.check_output("net session >nul 2>&1", shell=True)
                has_admin = True
                logger.info("Running with admin privileges, can terminate system processes")
            except:
                logger.warning("Not running with admin privileges, some processes cannot be killed")
            
            # Get all UDP ports with PIDs
            try:
                # Use netstat to get UDP listening ports
                netstat_output = subprocess.check_output("netstat -ano -p UDP", shell=True).decode('utf-8')
                
                # Parse the output to find UDP ports in the 10000-20000 range with PIDs
                udp_port_regex = re.compile(r':(\d{5})\s+.*?(\d+)')
                matches = udp_port_regex.findall(netstat_output)
                
                # Filter to only include ports in GNS3's NIO range (10000-20000)
                gns3_nio_matches = [(port, pid) for port, pid in matches if 10000 <= int(port) <= 20000]
                
                logger.info(f"Found {len(gns3_nio_matches)} UDP ports in GNS3 NIO range (10000-20000)")
                
                # Track terminated processes to avoid duplicates
                terminated_pids = set()
                
                for port, pid in gns3_nio_matches:
                    try:
                        pid_num = int(pid)
                        
                        # Skip if already terminated
                        if pid_num in terminated_pids:
                            continue
                            
                        # Skip system processes with low PIDs if we don't have admin rights
                        if pid_num < 1000 and not has_admin:
                            logger.info(f"Skipping system process {pid} using UDP port {port} (requires admin)")
                            continue
                        
                        # Get process info
                        task_info = ""
                        try:
                            task_info = subprocess.check_output(f"tasklist /FI \"PID eq {pid}\"", shell=True).decode('utf-8')
                            is_system_critical = "System" in task_info or "svchost.exe" in task_info
                            
                            # Handle system-critical processes
                            if is_system_critical:
                                if has_admin:
                                    logger.warning(f"Found system process {pid} ({task_info.split()[0]}) using UDP port {port}")
                                else:
                                    logger.warning(f"Skipping system process {pid} using UDP port {port}")
                                    continue
                        except:
                            logger.warning(f"Could not determine process type for PID {pid}")
                        
                        # Terminate the process
                        logger.info(f"Attempting to free UDP port {port} used by PID {pid}")
                        
                        # Skip actual GNS3 processes - we don't want to kill GNS3 itself
                        if "gns3" in task_info.lower() or "dynamips" in task_info.lower() or "vpcs" in task_info.lower():
                            logger.info(f"Skipping GNS3-related process {pid}")
                            continue
                            
                        result = subprocess.call(f"taskkill /PID {pid}", shell=True)
                        if result != 0:
                            if has_admin:
                                logger.info(f"Using force to terminate process {pid}")
                                result = subprocess.call(f"taskkill /F /PID {pid}", shell=True)
                                if result == 0:
                                    ports_freed += 1
                                    terminated_pids.add(pid_num)
                                    logger.info(f"Successfully terminated process {pid} with force")
                                else:
                                    logger.warning(f"Could not terminate process {pid} even with force")
                            else:
                                logger.warning(f"Could not terminate process {pid}, admin rights required")
                        else:
                            ports_freed += 1
                            terminated_pids.add(pid_num)
                            logger.info(f"Successfully terminated process {pid} gracefully")
                    except Exception as e:
                        logger.error(f"Error freeing UDP port {port} used by PID {pid}: {e}")
                
                logger.info(f"Freed {ports_freed} UDP ports on Windows")
                
                # As a last resort, try to reset the TCP/IP stack if no ports were freed and we have admin
                if ports_freed == 0 and has_admin:
                    try:
                        logger.warning("No UDP ports freed, attempting to reset Windows TCP/IP stack")
                        subprocess.call("netsh winsock reset", shell=True)
                        logger.info("Windows TCP/IP stack reset, a system restart is recommended")
                    except Exception as reset_error:
                        logger.error(f"Failed to reset TCP/IP stack: {reset_error}")
                
                return ports_freed
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to run netstat command: {e}")
                return 0
                
        except Exception as e:
            logger.error(f"Error freeing NIO UDP ports on Windows: {e}")
            return 0
            
    def _free_nio_udp_ports_linux(self) -> int:
        """
        Free UDP ports used by GNS3 NIOs on Linux.
        
        Returns:
            int: Number of ports freed
        """
        ports_freed = 0
        try:
            # Get all UDP ports with PIDs
            try:
                # Try ss command first (more modern)
                netstat_cmd = "ss -lunp 2>/dev/null"
                netstat_output = subprocess.check_output(netstat_cmd, shell=True).decode('utf-8')
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    # Fallback to netstat if ss is not available
                    netstat_cmd = "netstat -lunp 2>/dev/null"
                    netstat_output = subprocess.check_output(netstat_cmd, shell=True).decode('utf-8')
                except subprocess.CalledProcessError:
                    logger.error("Failed to run netstat/ss command")
                    return 0
            
            # Parse the output to find UDP ports in the 10000-20000 range with PIDs
            # Handle both ss and netstat formats
            udp_port_regex = re.compile(r':(\d{5})\s+.*?(?:users:\(\(".*?",pid=(\d+).*?\)|(\d+)/.*?)(?:\)|\s)')
            matches = udp_port_regex.findall(netstat_output)
            
            # Process matches - extract port and pid
            nio_ports = []
            for match in matches:
                port = match[0]
                # Handle different formats (ss vs netstat)
                pid = match[1] if match[1] else match[2]
                if pid and 10000 <= int(port) <= 20000:
                    nio_ports.append((port, pid))
            
            logger.info(f"Found {len(nio_ports)} UDP ports in GNS3 NIO range (10000-20000)")
            
            # Track terminated processes to avoid duplicates
            terminated_pids = set()
            
            for port, pid in nio_ports:
                try:
                    pid_num = int(pid)
                    
                    # Skip if already terminated
                    if pid_num in terminated_pids:
                        continue
                    
                    # Get process info
                    try:
                        ps_output = subprocess.check_output(f"ps -p {pid} -o comm=", shell=True).decode('utf-8').strip()
                        is_system_critical = ps_output in ["systemd", "init", "udevd"]
                        
                        if is_system_critical:
                            logger.warning(f"Skipping system process {pid} ({ps_output}) using UDP port {port}")
                            continue
                            
                        # Skip GNS3-related processes
                        if "gns3" in ps_output.lower() or "dynamips" in ps_output.lower() or "vpcs" in ps_output.lower():
                            logger.info(f"Skipping GNS3-related process {pid} ({ps_output})")
                            continue
                    except:
                        logger.warning(f"Could not determine process type for PID {pid}")
                    
                    # Terminate the process
                    logger.info(f"Attempting to free UDP port {port} used by PID {pid}")
                    
                    # Try graceful termination first
                    try:
                        subprocess.call(f"kill {pid}", shell=True)
                        time.sleep(0.5)  # Give it a moment to terminate
                        
                        # Check if process is still running
                        try:
                            subprocess.check_output(f"ps -p {pid}", shell=True)
                            # Process still exists, try SIGKILL
                            logger.info(f"Using SIGKILL for process {pid}")
                            subprocess.call(f"kill -9 {pid}", shell=True)
                        except subprocess.CalledProcessError:
                            # Process already terminated
                            pass
                            
                        # Assume success if we get here
                        ports_freed += 1
                        terminated_pids.add(pid_num)
                        logger.info(f"Successfully terminated process {pid}")
                    except Exception as kill_error:
                        logger.error(f"Error terminating process {pid}: {kill_error}")
                        
                except Exception as e:
                    logger.error(f"Error freeing UDP port {port} used by PID {pid}: {e}")
            
            logger.info(f"Freed {ports_freed} UDP ports on Linux")
            return ports_freed
            
        except Exception as e:
            logger.error(f"Error freeing NIO UDP ports on Linux: {e}")
            return 0
            
    def _free_nio_udp_ports_macos(self) -> int:
        """
        Free UDP ports used by GNS3 NIOs on macOS.
        
        Returns:
            int: Number of ports freed
        """
        ports_freed = 0
        try:
            # Get all UDP ports with PIDs
            try:
                netstat_cmd = "lsof -i UDP -P -n"
                netstat_output = subprocess.check_output(netstat_cmd, shell=True).decode('utf-8')
            except subprocess.CalledProcessError:
                logger.error("Failed to run lsof command")
                return 0
            
            # Parse the output to find UDP ports in the 10000-20000 range with PIDs
            lines = netstat_output.split('\n')
            nio_ports = []
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 9:
                    match = re.search(r':(\d{5})(?:\s|$)', parts[8])
                    if match:
                        port = match.group(1)
                        if 10000 <= int(port) <= 20000:
                            pid = parts[1]
                            process = parts[0]
                            nio_ports.append((port, pid, process))
            
            logger.info(f"Found {len(nio_ports)} UDP ports in GNS3 NIO range (10000-20000)")
            
            # Track terminated processes to avoid duplicates
            terminated_pids = set()
            
            for port, pid, process in nio_ports:
                try:
                    pid_num = int(pid)
                    
                    # Skip if already terminated
                    if pid_num in terminated_pids:
                        continue
                    
                    # Skip system processes
                    if process in ["launchd", "kernel", "systemd"]:
                        logger.warning(f"Skipping system process {pid} ({process}) using UDP port {port}")
                        continue
                        
                    # Skip GNS3-related processes
                    if "gns3" in process.lower() or "dynamips" in process.lower() or "vpcs" in process.lower():
                        logger.info(f"Skipping GNS3-related process {pid} ({process})")
                        continue
                    
                    # Terminate the process
                    logger.info(f"Attempting to free UDP port {port} used by PID {pid} ({process})")
                    
                    # Try SIGTERM first
                    try:
                        subprocess.call(f"kill {pid}", shell=True)
                        time.sleep(0.5)  # Give it a moment to terminate
                        
                        # Check if process is still running
                        try:
                            subprocess.check_output(f"ps -p {pid}", shell=True)
                            # Process still exists, try SIGKILL
                            logger.info(f"Using SIGKILL for process {pid}")
                            subprocess.call(f"kill -9 {pid}", shell=True)
                        except subprocess.CalledProcessError:
                            # Process already terminated
                            pass
                            
                        # Assume success if we get here
                        ports_freed += 1
                        terminated_pids.add(pid_num)
                        logger.info(f"Successfully terminated process {pid}")
                    except Exception as kill_error:
                        logger.error(f"Error terminating process {pid}: {kill_error}")
                        
                except Exception as e:
                    logger.error(f"Error freeing UDP port {port} used by PID {pid}: {e}")
            
            logger.info(f"Freed {ports_freed} UDP ports on macOS")
            return ports_freed
            
        except Exception as e:
            logger.error(f"Error freeing NIO UDP ports on macOS: {e}")
            return 0
    
    def _free_ports_windows(self, min_port: int = 5000, max_port: int = 10000, timeout: int = 30) -> int:
        """
        Free ports in use on Windows systems.
        
        Args:
            min_port: Minimum port in the range to check
            max_port: Maximum port in the range to check
            timeout: Maximum time to spend on this operation
            
        Returns:
            Number of ports freed
        """
        logger.info(f"Freeing ports on Windows in range {min_port}-{max_port}")
        freed_count = 0
        start_time = time.time()
        
        try:
            # Run netstat to list all connections
            cmd = "netstat -ano"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Error running netstat: {stderr}")
                return 0
                
            # Parse output to find ports in the given range
            ports_to_kill = []
            for line in stdout.splitlines():
                if "LISTENING" not in line:
                    continue
                    
                # Example line: TCP    0.0.0.0:5000    0.0.0.0:0    LISTENING    1234
                parts = line.split()
                if len(parts) < 5:
                    continue
                    
                # Extract port and PID
                try:
                    socket_part = parts[1]
                    for part in parts:
                        if ':' in part:
                            socket_part = part
                            break
                            
                    port_part = socket_part.split(':')[-1]
                    port = int(port_part)
                    pid = int(parts[-1])
                    
                    # Check if the port is in our range
                    if min_port <= port <= max_port:
                        ports_to_kill.append((port, pid))
                except Exception as e:
                    logger.debug(f"Error parsing netstat line '{line}': {e}")
                    continue
                    
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            # Kill processes using those ports
            killed_pids = set()
            for port, pid in ports_to_kill:
                # Skip system PIDs (< 100) and already killed processes
                if pid < 100 or pid in killed_pids:
                    continue
                    
                try:
                    # Skip MS essential services
                    if self._is_windows_protected_process(pid):
                        logger.info(f"Skipping Windows protected process PID {pid} using port {port}")
                        continue
                    
                    # Double-check that the process is actually using the port
                    valid, command = self._get_windows_process_command(pid)
                    if not valid:
                        logger.debug(f"Process {pid} no longer exists or cannot be accessed")
                        continue
                        
                    if "system32" in command.lower() or "windows" in command.lower():
                        logger.info(f"Skipping Windows system process PID {pid} using port {port}")
                        continue
                    
                    logger.info(f"Killing process {pid} using port {port} (command: {command})")
                    kill_cmd = f"taskkill /F /PID {pid}"
                    kill_process = subprocess.Popen(kill_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    kill_stdout, kill_stderr = kill_process.communicate(timeout=10)
                    
                    if kill_process.returncode == 0:
                        logger.info(f"Successfully killed process {pid} using port {port}")
                        freed_count += 1
                        killed_pids.add(pid)
                    else:
                        logger.warning(f"Failed to kill process {pid}: {kill_stderr}")
                except Exception as e:
                    logger.error(f"Error killing process {pid}: {e}")
                
                # Check timeout again
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            return freed_count
            
        except Exception as e:
            logger.error(f"Error freeing ports on Windows: {e}")
            logger.error(traceback.format_exc())
            return freed_count
            
    def _is_windows_protected_process(self, pid: int) -> bool:
        """
        Check if a Windows process is protected and should not be killed.
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if the process is protected
        """
        # List of protected Windows services by executable name
        protected_exes = [
            "lsass.exe", "csrss.exe", "services.exe", "svchost.exe", 
            "winlogon.exe", "wininit.exe", "smss.exe", "spoolsv.exe",
            "explorer.exe", "dllhost.exe", "taskmgr.exe"
        ]
        
        try:
            cmd = f"tasklist /FI \"PID eq {pid}\" /FO CSV /NH"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(timeout=5)
            
            if process.returncode != 0 or not stdout.strip():
                return False
                
            # Parse output to get executable name
            # Output format: "Image Name","PID","Session Name","Session#","Mem Usage"
            import csv
            from io import StringIO
            reader = csv.reader(StringIO(stdout))
            for row in reader:
                if row and len(row) > 1:
                    exe_name = row[0].lower()
                    for protected in protected_exes:
                        if protected.lower() in exe_name:
                            return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking if process {pid} is protected: {e}")
            return False
            
    def _get_windows_process_command(self, pid: int) -> Tuple[bool, str]:
        """
        Get the command line of a Windows process.
        
        Args:
            pid: Process ID to get command for
            
        Returns:
            Tuple of (success, command)
        """
        try:
            # Use wmic to get command line
            cmd = f"wmic process where processid={pid} get commandline /format:list"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(timeout=5)
            
            if process.returncode != 0:
                logger.debug(f"Error getting command for PID {pid}: {stderr}")
                return False, ""
                
            # Parse output
            command = ""
            for line in stdout.splitlines():
                if line.startswith("CommandLine="):
                    command = line[12:].strip()
                    break
                    
            return True, command
            
        except Exception as e:
            logger.debug(f"Error getting command for PID {pid}: {e}")
            return False, ""
    
    def _free_ports_linux(self, min_port: int = 5000, max_port: int = 10000, timeout: int = 30) -> int:
        """
        Free ports in use on Linux systems.
        
        Args:
            min_port: Minimum port in the range to check
            max_port: Maximum port in the range to check
            timeout: Maximum time to spend on this operation
            
        Returns:
            Number of ports freed
        """
        logger.info(f"Freeing ports on Linux in range {min_port}-{max_port}")
        freed_count = 0
        start_time = time.time()
        
        try:
            # Check for sudo access
            has_sudo = False
            try:
                sudo_check = subprocess.run(['sudo', '-n', 'true'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1)
                has_sudo = sudo_check.returncode == 0
                if has_sudo:
                    logger.info("Running with sudo privileges, can terminate system processes")
                else:
                    logger.warning("Not running with sudo privileges, some processes cannot be killed")
            except Exception as e:
                logger.warning(f"Error checking sudo privileges: {e}")
                
            # Run ss command to list all connections
            cmd = "ss -tlnp"
            if has_sudo:
                cmd = f"sudo {cmd}"
                
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Error running ss command: {stderr}")
                return 0
                
            # Parse output to find ports in the given range
            # Example line: LISTEN 0 128 *:5000 *:* users:(("python",pid=1234,fd=5))
            port_regex = re.compile(r'.*:(\d+)\s+.*\("([^"]+)",pid=(\d+),')
            
            ports_to_kill = []
            for line in stdout.splitlines():
                matches = port_regex.findall(line)
                if not matches:
                    continue
                    
                for port_str, process_name, pid_str in matches:
                    try:
                        port = int(port_str)
                        pid = int(pid_str)
                        
                        # Check if the port is in our range
                        if min_port <= port <= max_port:
                            ports_to_kill.append((port, pid, process_name))
                    except Exception as e:
                        logger.debug(f"Error parsing ss line '{line}': {e}")
                        continue
                
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            # Kill processes using those ports
            killed_pids = set()
            for port, pid, process_name in ports_to_kill:
                # Skip already killed processes
                if pid in killed_pids:
                    continue
                    
                try:
                    # Skip system processes if we don't have sudo
                    if not has_sudo and (pid < 1000 or self._is_linux_protected_process(process_name)):
                        logger.info(f"Skipping protected process {process_name} (PID {pid}) using port {port}")
                        continue
                    
                    # Kill the process
                    logger.info(f"Killing process {process_name} (PID {pid}) using port {port}")
                    kill_cmd = f"kill -9 {pid}"
                    if not has_sudo and pid < 1000:
                        kill_cmd = f"sudo {kill_cmd}"
                        
                    kill_process = subprocess.Popen(kill_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    kill_stdout, kill_stderr = kill_process.communicate(timeout=5)
                    
                    if kill_process.returncode == 0:
                        logger.info(f"Successfully killed process {process_name} (PID {pid}) using port {port}")
                        freed_count += 1
                        killed_pids.add(pid)
                    else:
                        logger.warning(f"Failed to kill process {process_name} (PID {pid}): {kill_stderr}")
                except Exception as e:
                    logger.error(f"Error killing process {pid}: {e}")
                
                # Check timeout again
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            return freed_count
            
        except Exception as e:
            logger.error(f"Error freeing ports on Linux: {e}")
            logger.error(traceback.format_exc())
            return freed_count
            
    def _is_linux_protected_process(self, process_name: str) -> bool:
        """
        Check if a Linux process is protected and should not be killed.
        
        Args:
            process_name: Name of the process to check
            
        Returns:
            True if the process is protected
        """
        # List of protected Linux services by executable name
        protected_processes = [
            "systemd", "dbus", "sshd", "bash", "sh", "init", "NetworkManager",
            "rsyslogd", "dnsmasq", "crond", "chronyd", "ntpd", "udevd"
        ]
        
        for protected in protected_processes:
            if protected in process_name:
                return True
        
        return False
        
    def _free_ports_macos(self, min_port: int = 5000, max_port: int = 10000, timeout: int = 30) -> int:
        """
        Free ports in use on macOS systems.
        
        Args:
            min_port: Minimum port in the range to check
            max_port: Maximum port in the range to check
            timeout: Maximum time to spend on this operation
            
        Returns:
            Number of ports freed
        """
        logger.info(f"Freeing ports on macOS in range {min_port}-{max_port}")
        freed_count = 0
        start_time = time.time()
        
        try:
            # Check for admin access
            has_admin = False
            try:
                admin_check = subprocess.run(['sudo', '-n', 'true'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1)
                has_admin = admin_check.returncode == 0
                if has_admin:
                    logger.info("Running with admin privileges, can terminate system processes")
                else:
                    logger.warning("Not running with admin privileges, some processes cannot be killed")
            except Exception as e:
                logger.warning(f"Error checking admin privileges: {e}")
                
            # Run lsof command to list ports in use
            cmd = "lsof -i -P -n | grep LISTEN"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0 and process.returncode != 1:  # grep returns 1 if no matches
                logger.error(f"Error running lsof command: {stderr}")
                return 0
                
            # Parse output to find ports in the given range
            # Example line: python 1234 user 5u IPv4 0xabcdef 0t0 TCP *:5000 (LISTEN)
            port_regex = re.compile(r'.*:(\d+)\s+\(LISTEN\)')
            
            ports_to_kill = []
            for line in stdout.splitlines():
                parts = line.split()
                if len(parts) < 2:
                    continue
                    
                process_name = parts[0]
                pid_str = parts[1]
                
                # Find port in the line
                matches = port_regex.findall(line)
                if not matches:
                    continue
                    
                try:
                    port = int(matches[0])
                    pid = int(pid_str)
                    
                    # Check if the port is in our range
                    if min_port <= port <= max_port:
                        ports_to_kill.append((port, pid, process_name))
                except Exception as e:
                    logger.debug(f"Error parsing lsof line '{line}': {e}")
                    continue
                
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            # Kill processes using those ports
            killed_pids = set()
            for port, pid, process_name in ports_to_kill:
                # Skip already killed processes
                if pid in killed_pids:
                    continue
                    
                try:
                    # Skip system processes if we don't have admin
                    if not has_admin and (pid < 1000 or self._is_macos_protected_process(process_name)):
                        logger.info(f"Skipping protected process {process_name} (PID {pid}) using port {port}")
                        continue
                    
                    # Kill the process
                    logger.info(f"Killing process {process_name} (PID {pid}) using port {port}")
                    kill_cmd = f"kill -9 {pid}"
                    if not has_admin and pid < 1000:
                        kill_cmd = f"sudo {kill_cmd}"
                        
                    kill_process = subprocess.Popen(kill_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    kill_stdout, kill_stderr = kill_process.communicate(timeout=5)
                    
                    if kill_process.returncode == 0:
                        logger.info(f"Successfully killed process {process_name} (PID {pid}) using port {port}")
                        freed_count += 1
                        killed_pids.add(pid)
                    else:
                        logger.warning(f"Failed to kill process {process_name} (PID {pid}): {kill_stderr}")
                except Exception as e:
                    logger.error(f"Error killing process {pid}: {e}")
                
                # Check timeout again
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            return freed_count
            
        except Exception as e:
            logger.error(f"Error freeing ports on macOS: {e}")
            logger.error(traceback.format_exc())
            return freed_count
            
    def _is_macos_protected_process(self, process_name: str) -> bool:
        """
        Check if a macOS process is protected and should not be killed.
        
        Args:
            process_name: Name of the process to check
            
        Returns:
            True if the process is protected
        """
        # List of protected macOS services by executable name
        protected_processes = [
            "launchd", "kernel", "WindowServer", "sshd", "bash", "sh", "zsh",
            "loginwindow", "Dock", "Finder", "mds", "configd", "systemstats"
        ]
        
        for protected in protected_processes:
            if process_name.lower() == protected.lower():
                return True
        
        return False


# Module-level instance for convenience
_port_manager = None


def get_port_manager() -> PortManager:
    """Get the global PortManager instance."""
    global _port_manager
    if _port_manager is None:
        _port_manager = PortManager()
    return _port_manager


def kill_port_processes() -> int:
    """
    Identify and terminate processes that are using ports in the GNS3 port range.
    This is a wrapper around PortManager.free_ports().
    
    Returns:
        Number of processes killed
    """
    return get_port_manager().free_ports()


def free_nio_udp_ports() -> int:
    """
    Free UDP ports specifically used by GNS3 NIOs (Network I/O).
    
    Returns:
        Number of ports freed
    """
    return get_port_manager().free_nio_udp_ports()