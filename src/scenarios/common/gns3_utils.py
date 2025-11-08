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

import paramiko
import logging
import time
import traceback
from typing import Dict, Any

# Configure logging - it's good practice for a utility module
# You might want to integrate this with your project's overall logging setup
logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Avoid adding multiple handlers if imported multiple times
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Or your preferred default level

def manage_socat_port_forwarding(
    gns3_server_ip: str,
    gns3_server_ssh_port: int,
    gns3_server_user: str,
    gns3_server_password: str,
    action: str,  # "start" or "stop"
    external_port: int,
    internal_ip: str,
    internal_port: int
) -> bool:
    """
    Manages socat port forwarding on the GNS3 server via SSH.
    Assumes socat is installed on the GNS3 server.

    Args:
        gns3_server_ip: IP address of the GNS3 server.
        gns3_server_ssh_port: SSH port of the GNS3 server.
        gns3_server_user: SSH username for the GNS3 server.
        gns3_server_password: SSH password for the GNS3 server.
        action: "start" or "stop" the port forwarding.
        external_port: The port on the GNS3 host to listen on.
        internal_ip: The internal IP address of the target container in GNS3.
        internal_port: The internal port of the target container in GNS3.

    Returns:
        True if the action was successful, False otherwise.
    """
    logger.info(f"Attempting to {action} socat port forwarding on {gns3_server_ip}...")
    logger.info(f"Rule: host_port {external_port} -> gns3_container {internal_ip}:{internal_port}")

    ssh = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            gns3_server_ip,
            port=gns3_server_ssh_port,
            username=gns3_server_user,
            password=gns3_server_password,
            timeout=30
        )

        # --- BEGIN SOCAT INSTALLATION CHECK ---
        socat_installed = False
        # Check if socat is installed
        logger.info("Checking if socat is installed on the GNS3 server...")
        stdin, stdout, stderr = ssh.exec_command("command -v socat")
        if stdout.channel.recv_exit_status() == 0 and stdout.read().decode().strip():
            logger.info("socat is already installed.")
            socat_installed = True
        else:
            logger.warning("socat command not found on GNS3 server. Attempting to install...")
            # Attempt to install socat
            # This requires sudo privileges without a password prompt for the user,
            # or the user gns3_server_user must be able to run apt-get install without sudo.
            install_cmd = "sudo apt-get update && sudo apt-get install -y socat"
            logger.info(f"Executing installation command: {install_cmd}")
            stdin_install, stdout_install, stderr_install = ssh.exec_command(install_cmd)
            install_exit_status = stdout_install.channel.recv_exit_status()

            if install_exit_status == 0:
                logger.info("socat installation command executed successfully. Re-checking...")
                # Re-check if socat is installed
                stdin_recheck, stdout_recheck, stderr_recheck = ssh.exec_command("command -v socat")
                if stdout_recheck.channel.recv_exit_status() == 0 and stdout_recheck.read().decode().strip():
                    logger.info("socat successfully installed.")
                    socat_installed = True
                else:
                    logger.error("socat installation attempted, but still not found. Please install manually.")
                    logger.error(f"Re-check stderr: {stderr_recheck.read().decode().strip()}")
            else:
                logger.error(f"socat installation command failed with exit status {install_exit_status}.")
                error_output = stderr_install.read().decode().strip()
                if error_output:
                    logger.error(f"Installation stderr: {error_output}")
                logger.error("Please install socat manually on the GNS3 server.")
        
        if not socat_installed:
            return False # Cannot proceed without socat
        # --- END SOCAT INSTALLATION CHECK ---

        if action == "start":
            # --- BEGIN PRE-START CLEANUP ---
            logger.info(f"Attempting to stop any existing socat forwarding on port {external_port} before starting a new one.")
            # Temporarily call the stop logic for this port. 
            # We'll make a more streamlined internal function later if this pattern is common.
            current_action_is_start = True # Flag to remember we are in 'start' action
            
            find_cmd_pre = f"fuser -n tcp {external_port}"
            stdin_pre, stdout_pre, stderr_pre = ssh.exec_command(find_cmd_pre)
            pids_str_pre = stdout_pre.read().decode().strip()
            exit_status_find_pre = stdout_pre.channel.recv_exit_status()

            if exit_status_find_pre == 0 and pids_str_pre:
                pids_pre = pids_str_pre.split()
                killed_any_pre = False
                for pid_pre in pids_pre:
                    if not pid_pre.isdigit():
                        logger.warning(f"[Pre-start cleanup] Non-numeric PID '{pid_pre}' found by fuser, skipping.")
                        continue
                    logger.info(f"[Pre-start cleanup] Found process PID {pid_pre} using port {external_port}. Attempting to kill...")
                    kill_cmd_pre = f"kill {pid_pre}"
                    stdin_kill_pre, stdout_kill_pre, stderr_kill_pre = ssh.exec_command(kill_cmd_pre)
                    if stdout_kill_pre.channel.recv_exit_status() == 0:
                        logger.info(f"[Pre-start cleanup] Successfully sent kill signal to PID {pid_pre}.")
                        killed_any_pre = True
                    else:
                        logger.warning(f"[Pre-start cleanup] Failed to kill PID {pid_pre}: {stderr_kill_pre.read().decode().strip()}")
                if killed_any_pre:
                    logger.info(f"[Pre-start cleanup] Finished attempting to stop existing processes on port {external_port}.")
                    time.sleep(1) # Give a moment for ports to free up
            elif exit_status_find_pre == 1:
                logger.info(f"[Pre-start cleanup] No existing process found on port {external_port}.")
            else:
                logger.warning(f"[Pre-start cleanup] Error checking for existing process on port {external_port}. stderr: {stderr_pre.read().decode().strip()}")
            # --- END PRE-START CLEANUP ---

            # Command to start socat in the background
            # Logs will go to /tmp/socat_gns3utils_<external_port>.log on the GNS3 server
            log_file_path = f"/tmp/socat_gns3utils_{external_port}.log"
            socat_cmd = f"nohup socat -d -d TCP-LISTEN:{external_port},fork,reuseaddr TCP:{internal_ip}:{internal_port} > {log_file_path} 2>&1 & echo $!"
            
            logger.info(f"Executing socat command: {socat_cmd}")
            stdin, stdout, stderr = ssh.exec_command(socat_cmd)
            exit_status_exec = stdout.channel.recv_exit_status()
            socat_pid = stdout.read().decode().strip()
            
            time.sleep(2) # Give socat a moment to start and potentially fail

            # --- BEGIN POST-START VERIFICATION ---
            socat_listening = False
            listening_check_cmd = f"ss -tulnp | grep LISTEN | grep ':{external_port}'"
            logger.info(f"Verifying socat is listening with: {listening_check_cmd}")
            stdin_ss, stdout_ss, stderr_ss = ssh.exec_command(listening_check_cmd)
            ss_output = stdout_ss.read().decode().strip()
            ss_exit_status = stdout_ss.channel.recv_exit_status()

            if ss_exit_status == 0 and ss_output:
                logger.info(f"'ss' command output shows a process listening on port {external_port}:\n{ss_output}")
                socat_listening = True
            else:
                logger.warning(f"'ss' command did not find a listening process on port {external_port}, or the command failed. Stderr: {stderr_ss.read().decode().strip()}")
            # --- END POST-START VERIFICATION (ss) ---

            # --- BEGIN CHECKING SOCAT LOG FILE ---
            logger.info(f"Checking socat log file: {log_file_path}")
            stdin_log, stdout_log, stderr_log = ssh.exec_command(f"cat {log_file_path}")
            log_content = stdout_log.read().decode().strip()
            log_stderr = stderr_log.read().decode().strip()

            if log_content:
                logger.info(f"Contents of {log_file_path}:\n{log_content}")
            elif log_stderr:
                logger.warning(f"Could not read {log_file_path}. Stderr: {log_stderr}")
            else:
                logger.info(f"{log_file_path} is empty or does not exist (which might be normal if socat started cleanly and daemonized without error to stdout/stderr before nohup redirection).")
            # --- END CHECKING SOCAT LOG FILE ---

            # --- BEGIN VERIFY CONNECTIVITY TO INTERNAL TARGET FROM GNS3 VM (nc) ---
            if socat_listening: # Only try if socat itself started listening
                nc_available = False
                logger.info("Checking if 'nc' (netcat) is available on the GNS3 VM...")
                stdin_nc_check, stdout_nc_check, _ = ssh.exec_command("command -v nc")
                if stdout_nc_check.channel.recv_exit_status() == 0 and stdout_nc_check.read().decode().strip():
                    logger.info("'nc' is available.")
                    nc_available = True
                else:
                    logger.warning("'nc' (netcat) not found on GNS3 VM. Skipping direct internal connectivity test.")

                if nc_available:
                    nc_check_cmd = f"nc -zv -w 2 {internal_ip} {internal_port}"
                    logger.info(f"Attempting to connect to internal target from GNS3 VM: {nc_check_cmd}")
                    stdin_nc, stdout_nc, stderr_nc = ssh.exec_command(nc_check_cmd)
                    nc_stdout = stdout_nc.read().decode().strip()
                    nc_stderr = stderr_nc.read().decode().strip() # nc often prints to stderr for -zv
                    nc_exit_status = stdout_nc.channel.recv_exit_status()

                    if nc_exit_status == 0:
                        logger.info(f"Successfully connected to {internal_ip}:{internal_port} from GNS3 VM. Output: {nc_stderr if nc_stderr else nc_stdout}")
                    else:
                        logger.warning(
                            f"Failed to connect to {internal_ip}:{internal_port} from GNS3 VM "
                            f"(Exit Status: {nc_exit_status}). "
                            f"Stdout: '{nc_stdout}'. Stderr: '{nc_stderr}'. "
                            f"This suggests the collector service inside the container might not be running/reachable."
                        )
            # --- END VERIFY CONNECTIVITY TO INTERNAL TARGET FROM GNS3 VM (nc) ---

            if exit_status_exec == 0 and socat_pid and socat_pid.isdigit() and socat_listening:
                logger.info(f"socat process likely started with PID: {socat_pid} and confirmed listening. Forwarding {gns3_server_ip}:{external_port} -> {internal_ip}:{internal_port}")
                logger.info(f"Log file on GNS3 server: {log_file_path}")
                return True
            else:
                logger.error(f"Failed to start socat for port {external_port}.")
                logger.error(f"Socat command exit status: {exit_status_exec}, PID reported: {socat_pid}, Listening: {socat_listening}")
                error_message = stderr.read().decode().strip()
                if error_message:
                    logger.error(f"Stderr from socat exec: {error_message}")
                
                # Try to get logs if socat failed
                stdin_log, stdout_log, stderr_log_read = ssh.exec_command(f"cat /tmp/socat_gns3utils_{external_port}.log")
                log_content = stdout_log.read().decode().strip()
                if log_content:
                    logger.error(f"Contents of /tmp/socat_gns3utils_{external_port}.log: {log_content}")
                return False

        elif action == "stop":
            # Find PIDs using the external port (fuser is good for this)
            # The -k option for fuser is not used here to allow more controlled logging
            find_cmd = f"fuser -n tcp {external_port}"
            logger.info(f"Attempting to find processes using TCP port {external_port} with: {find_cmd}")
            stdin, stdout, stderr_find = ssh.exec_command(find_cmd)
            pids_str = stdout.read().decode().strip()
            exit_status_find = stdout.channel.recv_exit_status()

            if exit_status_find == 0 and pids_str: # PIDs found
                pids = pids_str.split()
                killed_any = False
                for pid in pids:
                    if not pid.isdigit():
                        logger.warning(f"Non-numeric PID '{pid}' found by fuser, skipping.")
                        continue
                    logger.info(f"Found process PID {pid} using port {external_port}. Attempting to kill...")
                    kill_cmd = f"kill {pid}"
                    stdin_kill, stdout_kill, stderr_kill = ssh.exec_command(kill_cmd)
                    if stdout_kill.channel.recv_exit_status() == 0:
                        logger.info(f"Successfully sent kill signal to PID {pid}.")
                        killed_any = True
                    else:
                        logger.warning(f"Failed to kill PID {pid}: {stderr_kill.read().decode().strip()}")
                
                if killed_any:
                    logger.info(f"Stopped socat forwarding for host port {external_port}.")
                    # Optionally clean up the log file:
                    # ssh.exec_command(f"rm /tmp/socat_gns3utils_{external_port}.log")
                    return True
                else:
                    logger.warning(f"Found PIDs ({pids_str}) on port {external_port}, but could not kill them or they were not the target socat process.")
                    return False
            elif exit_status_find == 1: # fuser returns 1 if no process found
                logger.info(f"No process found using TCP port {external_port} on {gns3_server_ip}. Assumed already stopped or never started with this utility.")
                return True # Considered success as the port is not in use by a process fuser can find
            else: # Other fuser error
                logger.warning(f"Error checking for process on port {external_port} using fuser. Exit status: {exit_status_find}")
                error_output = stderr_find.read().decode().strip()
                if error_output:
                    logger.warning(f"Stderr from fuser: {error_output}")
                return False
        else:
            logger.error(f"Invalid action for socat management: {action}. Must be 'start' or 'stop'.")
            return False

    except paramiko.AuthenticationException:
        logger.error(f"Authentication failed for {gns3_server_user}@{gns3_server_ip}:{gns3_server_ssh_port}")
        return False
    except paramiko.SSHException as e:
        logger.error(f"SSH connection error to {gns3_server_ip}:{gns3_server_ssh_port}: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during socat management: {e}")
        logger.error(traceback.format_exc())
        return False
    finally:
        if ssh and ssh.get_transport() and ssh.get_transport().is_active():
            ssh.close()
            logger.debug(f"SSH connection to {gns3_server_ip} closed.")

if __name__ == '__main__':
    # Example usage / basic test
    # This part will only run if you execute this script directly
    # Replace with your actual GNS3 server details and desired ports for testing
    
    # Configure a basic logger for direct script execution testing
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')

    GNS3_IP = "192.168.141.128"  # Replace with your GNS3 server IP
    GNS3_SSH_PORT = 22
    GNS3_USER = "gns3"           # Replace with your GNS3 SSH username
    GNS3_PASS = "gns3"           # Replace with your GNS3 SSH password

    COLLECTOR_INTERNAL_IP = "192.168.100.40" # Example internal IP of a GNS3 node
    COLLECTOR_INTERNAL_PORT = 8000
    EXTERNAL_PORT_ON_GNS3_HOST = 8001

    # Test starting port forwarding
    logger.info(f"Attempting to START port forwarding: {GNS3_IP}:{EXTERNAL_PORT_ON_GNS3_HOST} -> {COLLECTOR_INTERNAL_IP}:{COLLECTOR_INTERNAL_PORT}")
    success_start = manage_socat_port_forwarding(
        gns3_server_ip=GNS3_IP,
        gns3_server_ssh_port=GNS3_SSH_PORT,
        gns3_server_user=GNS3_USER,
        gns3_server_password=GNS3_PASS,
        action="start",
        external_port=EXTERNAL_PORT_ON_GNS3_HOST,
        internal_ip=COLLECTOR_INTERNAL_IP,
        internal_port=COLLECTOR_INTERNAL_PORT
    )

    if success_start:
        logger.info(f"Successfully STARTED port forwarding. Check port {EXTERNAL_PORT_ON_GNS3_HOST} on {GNS3_IP}.")
        logger.info("Waiting for 10 seconds before stopping...")
        time.sleep(10)

        # Test stopping port forwarding
        logger.info(f"Attempting to STOP port forwarding for port {EXTERNAL_PORT_ON_GNS3_HOST} on {GNS3_IP}")
        success_stop = manage_socat_port_forwarding(
            gns3_server_ip=GNS3_IP,
            gns3_server_ssh_port=GNS3_SSH_PORT,
            gns3_server_user=GNS3_USER,
            gns3_server_password=GNS3_PASS,
            action="stop",
            external_port=EXTERNAL_PORT_ON_GNS3_HOST,
            internal_ip=COLLECTOR_INTERNAL_IP, # Not strictly needed for stop, but good to pass for consistency
            internal_port=COLLECTOR_INTERNAL_PORT # Not strictly needed for stop
        )
        if success_stop:
            logger.info(f"Successfully STOPPED port forwarding for port {EXTERNAL_PORT_ON_GNS3_HOST}.")
        else:
            logger.error(f"Failed to STOP port forwarding for port {EXTERNAL_PORT_ON_GNS3_HOST}.")
    else:
        logger.error(f"Failed to START port forwarding for port {EXTERNAL_PORT_ON_GNS3_HOST}.") 