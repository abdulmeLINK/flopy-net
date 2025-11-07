#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

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
Telnet Connection Pool for GNS3.

This module provides a connection pool for telnet connections to GNS3 nodes,
allowing connections to be reused and reducing overhead for multiple commands.
"""

import logging
import time
import telnetlib
import threading
from typing import Dict, Tuple, Optional, Any
import socket

logger = logging.getLogger(__name__)

class TelnetConnection:
    """Represents a telnet connection to a GNS3 node console."""
    
    def __init__(self, host: str, port: int, timeout: int = 10):
        """
        Initialize a telnet connection.
        
        Args:
            host: Telnet host (usually localhost)
            port: Telnet port
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.telnet = None
        self.last_used = 0
        self.lock = threading.Lock()
        self.connected = False
        
    def connect(self) -> bool:
        """
        Establish the telnet connection if not already connected.
        
        Returns:
            True if connection is successful, False otherwise
        """
        if self.connected and self.telnet:
            try:
                # Check if connection is still alive
                self.telnet.sock.send(telnetlib.IAC + telnetlib.NOP)
                return True
            except:
                # Connection is dead, reconnect
                self.close()
            
        try:
            self.telnet = telnetlib.Telnet(self.host, self.port, self.timeout)
            self.connected = True
            self.last_used = time.time()
            
            # Send a newline to get a prompt
            self.telnet.write(b"\n")
            time.sleep(0.5)
            
            # Try to read the initial prompt
            try:
                output = self.telnet.read_until(b">", timeout=2).decode('utf-8', errors='ignore')
                if ">" not in output:
                    # Send another newline
                    self.telnet.write(b"\n")
                    time.sleep(0.5)
                    self.telnet.read_until(b">", timeout=2)
            except:
                # Ignore timeout on initial read
                pass
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to {self.host}:{self.port}: {e}")
            self.connected = False
            self.telnet = None
            return False
    
    def send_command(self, command: str, wait_time: int = 3) -> Tuple[bool, str]:
        """
        Send a command to the telnet connection.
        
        Args:
            command: Command to send
            wait_time: Time to wait for command execution in seconds
            
        Returns:
            Tuple of (success, output)
        """
        with self.lock:
            if not self.connected or not self.telnet:
                if not self.connect():
                    return False, "Failed to connect to console"
            
            try:
                # Clear any pending output
                try:
                    pending_output = self.telnet.read_very_eager().decode('utf-8', errors='ignore')
                    logger.debug(f"Cleared pending output: {pending_output}")
                except:
                    # If read_very_eager fails, just continue
                    pass
                
                # Send the command
                self.telnet.write(f"{command}\n".encode('ascii'))
                
                # Wait for command to complete
                time.sleep(wait_time)
                
                # Read the response with a reasonable timeout
                try:
                    result = self.telnet.read_until(b">", timeout=5).decode('utf-8', errors='ignore')
                except socket.timeout:
                    # If timeout occurs, try to read whatever is available
                    try:
                        result = self.telnet.read_very_eager().decode('utf-8', errors='ignore')
                    except:
                        result = f"Timeout reading command output for: {command}"
                
                self.last_used = time.time()
                
                # Check for ping success if it's a ping command
                if "ping" in command.lower():
                    if "bytes from" in result:
                        return True, result
                    elif "host unreachable" in result.lower() or "destination unreachable" in result.lower():
                        return False, result
                
                # For other commands, just check for presence of command in output
                return True, result
                
            except Exception as e:
                logger.error(f"Error sending command {command}: {e}")
                self.close()
                return False, f"Error: {str(e)}"
    
    def close(self):
        """Close the telnet connection."""
        if self.telnet:
            try:
                self.telnet.close()
            except:
                pass
            self.telnet = None
        self.connected = False


class TelnetConnectionPool:
    """A pool of telnet connections to GNS3 nodes."""
    
    def __init__(self, max_idle_time: int = 300):
        """
        Initialize the connection pool.
        
        Args:
            max_idle_time: Maximum time in seconds to keep idle connections
        """
        self.connections: Dict[str, TelnetConnection] = {}
        self.lock = threading.Lock()
        self.max_idle_time = max_idle_time
        self.cleanup_thread = None
        self.running = False
        
    def start(self):
        """Start the pool and cleanup thread."""
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_idle_connections, daemon=True)
        self.cleanup_thread.start()
        
    def stop(self):
        """Stop the pool and cleanup thread."""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=1)
        self._close_all_connections()
        
    def _get_connection_key(self, host: str, port: int) -> str:
        """Generate a unique key for a connection."""
        return f"{host}:{port}"
        
    def get_connection(self, host: str, port: int) -> TelnetConnection:
        """
        Get a connection from the pool or create a new one.
        
        Args:
            host: Telnet host
            port: Telnet port
            
        Returns:
            A TelnetConnection object
        """
        key = self._get_connection_key(host, port)
        
        with self.lock:
            if key in self.connections:
                conn = self.connections[key]
                # If connection is dead, create a new one
                if not conn.connected:
                    if not conn.connect():
                        # If connection fails, create a new one
                        conn = TelnetConnection(host, port)
                        self.connections[key] = conn
            else:
                # Create a new connection
                conn = TelnetConnection(host, port)
                self.connections[key] = conn
                
        return conn
    
    def send_command(self, host: str, port: int, command: str, wait_time: int = 3) -> Tuple[bool, str]:
        """
        Send a command to a node via telnet.
        
        Args:
            host: Telnet host
            port: Telnet port
            command: Command to send
            wait_time: Time to wait for command execution
            
        Returns:
            Tuple of (success, output)
        """
        conn = self.get_connection(host, port)
        return conn.send_command(command, wait_time)
    
    def _cleanup_idle_connections(self):
        """Cleanup thread that removes idle connections."""
        while self.running:
            try:
                current_time = time.time()
                keys_to_remove = []
                
                with self.lock:
                    for key, conn in self.connections.items():
                        # Check if connection is idle
                        if current_time - conn.last_used > self.max_idle_time:
                            keys_to_remove.append(key)
                
                # Close and remove idle connections
                for key in keys_to_remove:
                    with self.lock:
                        if key in self.connections:
                            logger.debug(f"Closing idle connection: {key}")
                            self.connections[key].close()
                            del self.connections[key]
                
                # Sleep for a bit before next cleanup
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
                time.sleep(60)  # Sleep and try again
    
    def _close_all_connections(self):
        """Close all connections in the pool."""
        with self.lock:
            for key, conn in self.connections.items():
                try:
                    conn.close()
                except:
                    pass
            self.connections.clear()


# Global connection pool instance
connection_pool = TelnetConnectionPool()
connection_pool.start()

# Ensure the pool is cleaned up on exit
import atexit
atexit.register(connection_pool.stop) 