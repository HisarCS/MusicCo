# Co.py - Multiplayer connection module for music application with instrument-specific playback

import pygame
import time
import sys
import socket
import threading
import json
import random
import os
import hashlib
import uuid
from constants import WIDTH, HEIGHT, BG_COLOR, TEXT_COLOR, INSTRUMENTS, INSTRUMENT_NAMES, FREQS
from sound_engine import play_note, play_error_sound
from music_parser import parse_music_data

# Connection states
ROLE_SELECTION = 0
MASTER_MODE = 1
SLAVE_MODE = 2
CONNECTION_ACTIVE = 3
SLAVE_SELECT = 4
PLAYING_MODE = 5  # New state for active playback

# Socket server constants
MASTER_BROADCAST_PORT = 5001  # Port for master to broadcast
SLAVE_RESPONSE_PORT = 5002    # Port for slaves to respond
SERVER_PORT = 5000           # Port for direct connections

# Message types
MSG_CONNECT = "connect"
MSG_CONFIRM = "confirm"
MSG_TRACK_INFO = "track_info"
MSG_PLAY_NOTE = "play_note"
MSG_START_PLAYBACK = "start_playback"
MSG_ERROR = "error"
MSG_DISCOVERY = "discovery"
MSG_DISCOVERY_RESPONSE = "discovery_response"
MSG_PLAYBACK_READY = "playback_ready"
MSG_PLAYBACK_COMPLETE = "playback_complete"
MSG_NOTE_PLAYED = "note_played" # Notification that a note was played (but don't play sound)

# Colors
STATUS_RED = (255, 100, 100)  # For disconnected, errors
STATUS_GREEN = (0, 255, 0)    # For connected
STATUS_ORANGE = (255, 165, 0) # For discovery/waiting
ID_YELLOW = (255, 255, 0)     # For displaying IDs
BUTTON_BG = (57, 57, 74)      # Button background
BUTTON_BORDER = (80, 80, 100) # Button border
PIANO_COLOR = (100, 149, 237) # Light blue for piano notes
GUITAR_COLOR = (255, 165, 0)  # Orange for guitar notes

# Global variable to store active slaves
active_slaves = {}

# Debug flag - set to True to see detailed network logs
DEBUG = True

def debug_print(message):
    """Print debug messages if DEBUG is enabled"""
    if DEBUG:
        print(f"[DEBUG] {message}")

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Create a temporary socket to determine our IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't actually connect but gets the route
        s.connect(('8.8.8.8', 1))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        debug_print(f"Could not determine local IP: {e}")
        # Fall back to localhost if we can't determine IP
        return "127.0.0.1"

# Fallback test track - Simple Twinkle Twinkle Little Star
FALLBACK_TRACK = """Do4-0.0-0.5-100-0 Do4-0.5-0.5-100-0 Sol4-1.0-0.5-100-0 Sol4-1.5-0.5-100-0 La4-2.0-0.5-100-0 La4-2.5-0.5-100-0 Sol4-3.0-1.0-100-0 Fa4-4.0-0.5-100-1 Fa4-4.5-0.5-100-1 Mi4-5.0-0.5-100-1 Mi4-5.5-0.5-100-1 Re4-6.0-0.5-100-1 Re4-6.5-0.5-100-1 Do4-7.0-1.0-100-1"""

class MusicConnection:
    """Class to handle multiplayer music connections"""
    
    def __init__(self):
        # Initialize pygame
        pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
            
        # Set up display
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SlidePlay - Connection Mode")
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 64)
        self.clock = pygame.time.Clock()
        
        # Connection state
        self.state = ROLE_SELECTION
        self.selected_role = 0  # 0 for Master, 1 for Slave
        self.connection_status = "Disconnected"
        
        # Slave selection
        self.selected_slave_index = 0
        
        # Unique ID for this instance (used for slave mode)
        self.id = str(uuid.uuid4())[:8]  # Using first 8 chars of UUID for readability
        
        # Socket related
        self.socket = None
        self.client_socket = None
        self.server_thread = None
        self.connection_thread = None
        self.discovery_thread = None
        self.broadcast_socket = None
        self.response_socket = None
        
        # Thread control
        self.discovery_running = False
        self.connection_active = False
        self.heartbeat_running = False
        self.playback_running = False
        
        # Selected instruments
        self.local_instrument = INSTRUMENTS["PIANO"]
        self.remote_instrument = INSTRUMENTS["ELECTRO_GUITAR"]
        
        # Track related
        self.track_name = "track.txt"
        self.track_hash = ""
        self.track_content = ""
        self.song_data = []
        self.parsed_song_data = []
        
        # Dynamic port tracking
        self.connection_port = SERVER_PORT
        
        # Get and store the local IP address
        self.local_ip = get_local_ip()
        debug_print(f"Local IP address: {self.local_ip}")
        
        # Track response port for dynamic allocation
        self.response_port = SLAVE_RESPONSE_PORT
        
        # Playback status
        self.playback_status = "Ready"
        self.remote_ready = False
        self.local_ready = False
        self.playback_completed = False
        self.local_completed = False
        self.remote_completed = False
        self.current_time = 0
        self.start_time = 0
        self.max_song_time = 25.0
        
        # Visual display of notes
        self.played_notes = []  # Notes played locally or received from remote
        self.upcoming_notes = []  # Notes that will play soon
        
        # Try to load track on startup
        self.load_track()
    
    def start_server(self):
        """Start the discovery process for Master mode"""
        try:
            # Clear any existing slaves
            global active_slaves
            active_slaves.clear()
            
            # Close any previous sockets
            self.close_sockets()
            
            # Create separate sockets for broadcasting and receiving
            # Broadcasting socket - sends discovery messages
            self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Enable broadcast on supported platforms
            try:
                self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except:
                debug_print("SO_BROADCAST not supported, multicast may be limited")
            
            # Response socket - receives slave responses
            self.response_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.response_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try to bind to the default response port
            try:
                self.response_socket.bind(('', SLAVE_RESPONSE_PORT))
                self.response_port = SLAVE_RESPONSE_PORT
                debug_print(f"Master response socket bound to port {SLAVE_RESPONSE_PORT}")
            except socket.error as e:
                debug_print(f"Could not bind to port {SLAVE_RESPONSE_PORT}, using random port: {e}")
                self.response_socket.bind(('', 0))
                self.response_port = self.response_socket.getsockname()[1]
                debug_print(f"Using dynamic port {self.response_port} for slave responses")
            
            # Start discovery flag
            self.discovery_running = True
            
            # Start discovery thread
            if self.discovery_thread and self.discovery_thread.is_alive():
                debug_print("Waiting for previous discovery thread to terminate")
                time.sleep(0.5)
            
            self.discovery_thread = threading.Thread(target=self.discover_slaves)
            self.discovery_thread.daemon = True
            self.discovery_thread.start()
            
            self.connection_status = "Scanning for slaves..."
            self.state = SLAVE_SELECT
            return True
            
        except Exception as e:
            debug_print(f"Error starting server: {e}")
            self.connection_status = f"Error: {e}"
            return False
            
    def discover_slaves(self):
        """Master thread to send discovery broadcasts and receive responses"""
        try:
            debug_print(f"Starting slave discovery from {self.local_ip}")
            
            # Keep track of the last broadcast time
            last_broadcast = 0
            
            while self.discovery_running and self.state == SLAVE_SELECT:
                current_time = time.time()
                
                # Send a discovery broadcast every 1 second
                if current_time - last_broadcast > 1:
                    # Prepare the discovery message
                    discovery_msg = json.dumps({
                        "type": MSG_DISCOVERY,
                        "master_id": self.id,
                        "track_hash": self.track_hash,
                        "response_port": self.response_port,
                        "master_ip": self.local_ip  # Include our IP for direct discovery
                    }).encode()
                    
                    # Try using broadcast to 255.255.255.255
                    try:
                        debug_print(f"Broadcasting discovery to port {MASTER_BROADCAST_PORT}")
                        self.broadcast_socket.sendto(discovery_msg, ('<broadcast>', MASTER_BROADCAST_PORT))
                    except:
                        # Try several fallback methods
                        try:
                            # Try subnet broadcast
                            ip_parts = self.local_ip.split('.')
                            subnet_broadcast = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"
                            self.broadcast_socket.sendto(discovery_msg, (subnet_broadcast, MASTER_BROADCAST_PORT))
                        except:
                            # Last resort: try localhost
                            debug_print("Broadcast failed, falling back to localhost")
                            self.broadcast_socket.sendto(discovery_msg, ('localhost', MASTER_BROADCAST_PORT))
                    
                    last_broadcast = current_time
                
                # Check for responses with a non-blocking timeout
                self.response_socket.settimeout(0.1)
                try:
                    data, addr = self.response_socket.recvfrom(4096)
                    message = json.loads(data.decode())
                    
                    if message.get("type") == MSG_DISCOVERY_RESPONSE:
                        slave_id = message.get("slave_id", "unknown")
                        slave_track_hash = message.get("track_hash", "")
                        slave_ip = addr[0]  # Get the IP from the response
                        
                        # Store the slave data with its address
                        if slave_track_hash == self.track_hash:
                            debug_print(f"Discovered slave: {slave_id} at {addr} with IP {slave_ip}")
                            
                            # Update the global active_slaves dictionary
                            global active_slaves
                            active_slaves[slave_id] = {
                                "id": slave_id,
                                "address": addr,
                                "ip": slave_ip,
                                "track_hash": slave_track_hash,
                                "last_seen": current_time
                            }
                            debug_print(f"Updated active_slaves: {list(active_slaves.keys())}")
                except socket.timeout:
                    # Expected timeout, just continue
                    pass
                except Exception as e:
                    debug_print(f"Error receiving discovery response: {e}")
                
                # Prune old slaves that haven't been seen in 5 seconds
                slaves_to_remove = []
                for slave_id, slave_data in active_slaves.items():
                    if current_time - slave_data.get("last_seen", 0) > 5:
                        slaves_to_remove.append(slave_id)
                
                for slave_id in slaves_to_remove:
                    debug_print(f"Removing stale slave: {slave_id}")
                    active_slaves.pop(slave_id, None)
                
                # Small delay to prevent CPU hogging
                time.sleep(0.05)
                
            debug_print("Discovery thread ending")
            
        except Exception as e:
            debug_print(f"Discovery error: {e}")
            self.connection_status = f"Discovery error: {e}"
        finally:
            # Clean up discovery resources
            if hasattr(self, 'response_socket') and self.response_socket:
                try:
                    self.response_socket.close()
                except:
                    pass
                self.response_socket = None
                
            if hasattr(self, 'broadcast_socket') and self.broadcast_socket:
                try:
                    self.broadcast_socket.close()
                except:
                    pass
                self.broadcast_socket = None
            
    def connect_to_slave(self, slave_info):
        """Connect to a selected slave"""
        try:
            # Stop discovery
            self.discovery_running = False
            time.sleep(0.2)  # Give discovery thread time to clean up
            
            # Close any existing sockets
            self.close_sockets()
            
            # Create socket server for the slave to connect to
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try to bind to the default port, if it fails use a random port
            success = False
            for port_attempt in range(3):  # Try up to 3 ports
                try:
                    target_port = SERVER_PORT + port_attempt
                    debug_print(f"Attempting to bind to {self.local_ip}:{target_port}")
                    self.socket.bind((self.local_ip, target_port))
                    self.connection_port = target_port
                    success = True
                    break
                except socket.error as e:
                    debug_print(f"Failed to bind to port {target_port}: {e}")
                    continue
            
            # If all fixed ports failed, use a random port
            if not success:
                debug_print("All fixed ports failed, using random port")
                self.socket.bind((self.local_ip, 0))
                self.connection_port = self.socket.getsockname()[1]
            
            debug_print(f"Successfully bound to {self.local_ip}:{self.connection_port}")
            self.socket.listen(1)
            
            # Send direct connection request to the slave
            connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            connect_msg = json.dumps({
                "type": "connect_request",
                "master_id": self.id,
                "address": self.local_ip,
                "port": self.connection_port
            }).encode()
            
            # Send to the slave's address
            slave_addr = slave_info["address"]
            debug_print(f"Sending connect request to {slave_addr} using {self.local_ip}:{self.connection_port}")
            connection_socket.sendto(connect_msg, slave_addr)
            
            # Also try to send directly to the slave's IP and port
            try:
                slave_ip = slave_info.get("ip", slave_addr[0])
                slave_port = slave_addr[1]
                debug_print(f"Also sending direct connect request to {slave_ip}:{MASTER_BROADCAST_PORT}")
                connection_socket.sendto(connect_msg, (slave_ip, MASTER_BROADCAST_PORT))
            except:
                pass
                
            connection_socket.close()
            
            # Start waiting for connection
            self.connection_status = f"Waiting for slave {slave_info['id']} to connect..."
            
            # Start server listen thread
            if self.server_thread and self.server_thread.is_alive():
                debug_print("Waiting for previous server thread to terminate")
                time.sleep(0.5)
                
            self.server_thread = threading.Thread(target=self.server_listen)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            return True
        except Exception as e:
            debug_print(f"Connection error: {e}")
            self.connection_status = f"Error: {e}"
            return False
            
    def server_listen(self):
        """Server listening thread for master mode"""
        try:
            debug_print(f"Waiting for slave to connect on {self.local_ip}:{self.connection_port}")
            
            # Set a timeout so we can check if we should keep listening
            self.socket.settimeout(2.0)
            
            # Listen for up to 30 seconds (15 iterations with 2-second timeout)
            for _ in range(15):
                try:
                    self.client_socket, addr = self.socket.accept()
                    debug_print(f"Connection from {addr}")
                    
                    # Switch to active connection state
                    self.connection_status = "Connected"
                    self.state = CONNECTION_ACTIVE
                    self.connection_active = True
                    
                    # Start heartbeat thread
                    self.heartbeat_running = True
                    self.start_heartbeat()
                    
                    # Handle communication in separate thread
                    if self.connection_thread and self.connection_thread.is_alive():
                        debug_print("Waiting for previous connection thread to terminate")
                        time.sleep(0.5)
                    
                    self.connection_thread = threading.Thread(target=self.handle_connection, args=(self.client_socket,))
                    self.connection_thread.daemon = True
                    self.connection_thread.start()
                    
                    return  # Successful connection, exit the method
                except socket.timeout:
                    # This is expected with the timeout, check if we should continue
                    if self.state != SLAVE_SELECT:
                        debug_print("State changed, no longer selecting slaves")
                        break
            
            # If we get here, connection timed out
            debug_print("Connection attempt timed out")
            self.connection_status = "Connection timed out"
            # Return to slave selection
            if self.state == SLAVE_SELECT:
                self.start_server()  # Restart the slave discovery
            
        except Exception as e:
            debug_print(f"Server error: {e}")
            self.connection_status = f"Error: {e}"
        finally:
            # Clean up the socket if no connection was made
            if not self.client_socket and hasattr(self, 'socket') and self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
                
    def start_slave_mode(self):
        """Start listening for discovery broadcasts in slave mode"""
        try:
            # Close any existing sockets
            self.close_sockets()
            
            # Create discovery socket
            self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to the master broadcast port to listen for broadcasts
            try:
                # Try to bind to broadcast port
                self.broadcast_socket.bind(('', MASTER_BROADCAST_PORT))
                debug_print(f"Slave bound to master broadcast port {MASTER_BROADCAST_PORT}")
            except socket.error as e:
                debug_print(f"Failed to bind to port {MASTER_BROADCAST_PORT}: {e}")
                
                # Try alternative method - specific IP binding
                try:
                    self.broadcast_socket.bind((self.local_ip, MASTER_BROADCAST_PORT))
                    debug_print(f"Slave bound to specific IP {self.local_ip}:{MASTER_BROADCAST_PORT}")
                except socket.error as e2:
                    debug_print(f"Could not bind to {self.local_ip}:{MASTER_BROADCAST_PORT}: {e2}")
                    
                    # Use a less reliable method - bind to any available port
                    try:
                        self.broadcast_socket.bind(('', 0))
                        listen_port = self.broadcast_socket.getsockname()[1]
                        debug_print(f"Using alternative port {listen_port} for discovery")
                        self.connection_status = "Limited discovery mode"
                    except socket.error as e3:
                        debug_print(f"Could not bind to any port: {e3}")
                        self.connection_status = f"Error: Could not bind to any port"
                        return False
            
            # Flag for discovery thread
            self.discovery_running = True
                
            # Start listening for discovery in a thread
            if self.discovery_thread and self.discovery_thread.is_alive():
                debug_print("Waiting for previous discovery thread to terminate")
                self.discovery_running = False
                time.sleep(0.5)
            
            self.discovery_thread = threading.Thread(target=self.listen_for_discovery)
            self.discovery_thread.daemon = True
            self.discovery_thread.start()
            
            self.connection_status = "Waiting for master to discover..."
            return True
        except Exception as e:
            debug_print(f"Error starting slave mode: {e}")
            self.connection_status = f"Error: {e}"
            return False
            
    def listen_for_discovery(self):
        """Listen for discovery broadcasts from masters"""
        try:
            debug_print(f"Slave starting to listen for master broadcasts on {self.local_ip}")
            master_connections = {}  # Track which masters we've responded to
            
            while self.discovery_running and self.state == SLAVE_MODE:
                # Set timeout to allow checking if we're still in slave mode
                self.broadcast_socket.settimeout(1.0)
                
                try:
                    data, addr = self.broadcast_socket.recvfrom(4096)
                    sender_ip = addr[0]
                    debug_print(f"Received data from {sender_ip}")
                    
                    try:
                        message = json.loads(data.decode())
                        debug_print(f"Slave received message: {message} from {addr}")
                        
                        # Handle different message types
                        if message.get("type") == MSG_DISCOVERY:
                            # Respond to discovery broadcast
                            master_id = message.get("master_id", "unknown")
                            master_track_hash = message.get("track_hash", "")
                            response_port = message.get("response_port", SLAVE_RESPONSE_PORT)
                            master_ip = message.get("master_ip", sender_ip)
                            
                            # Only respond if our track matches and we haven't responded recently
                            current_time = time.time()
                            last_response = master_connections.get(master_id, 0)
                            
                            if master_track_hash == self.track_hash and current_time - last_response > 2:
                                debug_print(f"Discovered by master {master_id} from {addr} with IP {master_ip}")
                                
                                # Create a new socket for the response to avoid conflicts
                                response_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                
                                response = json.dumps({
                                    "type": MSG_DISCOVERY_RESPONSE,
                                    "slave_id": self.id,
                                    "track_hash": self.track_hash,
                                    "slave_ip": self.local_ip  # Include our IP
                                }).encode()
                                
                                # Send to the master's response port on their IP
                                master_addr = (master_ip, response_port)
                                debug_print(f"Sending response to master at {master_addr}")
                                response_socket.sendto(response, master_addr)
                                
                                # Also try responding to the sender's address if different
                                if master_ip != sender_ip:
                                    debug_print(f"Also sending response to sender at {addr}")
                                    response_socket.sendto(response, (sender_ip, response_port))
                                    
                                response_socket.close()
                                
                                master_connections[master_id] = current_time
                                self.connection_status = f"Discovered by master {master_id}"
                                
                        elif message.get("type") == "connect_request":
                            # Master wants to connect to us directly
                            master_id = message.get("master_id", "unknown")
                            server_host = message.get("address", sender_ip)
                            server_port = message.get("port", SERVER_PORT)
                            
                            debug_print(f"Received connect request from master {master_id} at {server_host}:{server_port}")
                            self.connection_status = f"Connecting to master {master_id}..."
                            
                            # Connect to the master's server
                            if self.connect_to_master(server_host, server_port):
                                # Successfully connected, stop listening for discovery
                                break
                    except json.JSONDecodeError:
                        debug_print(f"Received invalid JSON from {addr}")
                except socket.timeout:
                    # This is normal, just continue listening
                    pass
                except Exception as e:
                    debug_print(f"Discovery listen error: {e}")
                    
            debug_print("Slave discovery thread ending")
                    
        except Exception as e:
            debug_print(f"Discovery thread error: {e}")
        finally:
            if hasattr(self, 'broadcast_socket') and self.broadcast_socket:
                try:
                    self.broadcast_socket.close()
                except:
                    pass
                self.broadcast_socket = None
            
    def connect_to_master(self, host, port):
        """Connect to a master's server socket"""
        try:
            debug_print(f"Connecting to master at {host}:{port}")
            
            # Close any existing sockets
            self.close_sockets()
            
            # Create socket and connect
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)  # Set timeout for connection attempt
            
            # Try to connect to the master
            try:
                debug_print(f"Attempting socket connection to {host}:{port}")
                self.socket.connect((host, port))
            except socket.error as e:
                debug_print(f"Could not connect to {host}:{port}: {e}")
                self.connection_status = f"Connection failed: {e}"
                
                # Clean up and return to slave mode
                self.socket.close()
                self.socket = None
                return False
            
            # Reset to blocking mode after connected
            self.socket.settimeout(None)
            
            # Send initial connection message with our track hash
            connection_message = {
                "type": MSG_CONNECT,
                "track_hash": self.track_hash,
                "slave_id": self.id,
                "slave_ip": self.local_ip
            }
            
            debug_print(f"Sending connection message: {connection_message}")
            self.send_message(connection_message)
            
            # Start heartbeat thread
            self.heartbeat_running = True
            self.start_heartbeat()
            
            # Start connection handler
            if self.connection_thread and self.connection_thread.is_alive():
                debug_print("Waiting for previous connection thread to terminate")
                time.sleep(0.5)
                
            self.connection_thread = threading.Thread(target=self.handle_connection, args=(self.socket,))
            self.connection_thread.daemon = True
            self.connection_thread.start()
            
            self.connection_status = "Connected to master"
            self.state = CONNECTION_ACTIVE
            self.connection_active = True
            return True
            
        except Exception as e:
            debug_print(f"Connection error: {e}")
            self.connection_status = f"Error: {e}"
            if hasattr(self, 'socket') and self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False
            
    def send_message(self, message_data):
        """Send a message to the connected client/server"""
        try:
            # Ensure the message has a timestamp for debugging
            if isinstance(message_data, dict) and "timestamp" not in message_data:
                message_data["timestamp"] = time.time()
                
            if not hasattr(self, 'connection_active') or not self.connection_active:
                if self.selected_role == 0 and hasattr(self, 'client_socket') and self.client_socket:
                    debug_print("Socket exists but connection not marked active - sending anyway")
                elif self.selected_role == 1 and hasattr(self, 'socket') and self.socket:
                    debug_print("Socket exists but connection not marked active - sending anyway")
                else:
                    debug_print("Cannot send message - no active connection")
                    return False
                
            # Serialize and send the message
            msg = json.dumps(message_data).encode()
            
            if self.selected_role == 0:  # Master
                if hasattr(self, 'client_socket') and self.client_socket:
                    debug_print(f"Master sending: {message_data}")
                    self.client_socket.send(msg)
                    # Add a small delay after sending to allow processing
                    time.sleep(0.1)
                    return True
            else:  # Slave
                if hasattr(self, 'socket') and self.socket:
                    debug_print(f"Slave sending: {message_data}")
                    self.socket.send(msg)
                    # Add a small delay after sending to allow processing
                    time.sleep(0.1)
                    return True
            
            return False
        except Exception as e:
            debug_print(f"Error sending message: {e}")
            return False
            
    def handle_connection(self, conn):
        """Handle communication with the connected client/server"""
        try:
            # Set a longer timeout to prevent premature disconnection
            conn.settimeout(2.0)  # Use a 2-second timeout
            no_data_count = 0  # Counter for consecutive no-data events
            
            while (hasattr(self, 'connection_active') and self.connection_active and 
                  hasattr(self, 'state') and (self.state == CONNECTION_ACTIVE or self.state == PLAYING_MODE)):
                try:
                    # Receive data
                    data = conn.recv(4096)
                    if not data:
                        # Connection might be closed, but don't disconnect immediately
                        # Give it a few more attempts
                        no_data_count += 1
                        debug_print(f"No data received ({no_data_count}/3)")
                        
                        if no_data_count >= 3:
                            # Only consider the connection closed after multiple attempts
                            debug_print("Connection closed (no data after multiple attempts)")
                            self.connection_status = "Disconnected"
                            self.connection_active = False
                            break
                        
                        # Send a ping to check if connection is still alive
                        try:
                            ping_message = {
                                "type": "ping",
                                "timestamp": time.time()
                            }
                            msg = json.dumps(ping_message).encode()
                            conn.send(msg)
                            debug_print("Sent ping to verify connection")
                        except:
                            debug_print("Failed to send ping, connection appears dead")
                            self.connection_status = "Disconnected"
                            self.connection_active = False
                            break
                            
                        # Small delay before next attempt
                        time.sleep(0.5)
                        continue
                    
                    # Reset no data counter on successful receive
                    no_data_count = 0
                        
                    # Parse the message
                    try:
                        message = json.loads(data.decode())
                        debug_print(f"Received message: {message}")
                        self.process_message(message)
                    except json.JSONDecodeError:
                        debug_print(f"Invalid JSON received: {data.decode()}")
                except socket.timeout:
                    # Just a timeout for checking connection state
                    continue
                except Exception as e:
                    debug_print(f"Connection receive error: {e}")
                    self.connection_status = "Connection error"
                    no_data_count += 1
                    
                    # Give a few more attempts before disconnecting
                    if no_data_count >= 3:
                        self.connection_active = False
                        break
                    
                    # Small delay before next attempt
                    time.sleep(0.5)
                        
            debug_print("Connection handler thread ended")
        except Exception as e:
            debug_print(f"Connection handler error: {e}")
            self.connection_status = "Disconnected"
            self.connection_active = False
        finally:
            try:
                conn.close()
            except:
                pass
            
            # Return to appropriate mode
            if hasattr(self, 'state') and (self.state == CONNECTION_ACTIVE or self.state == PLAYING_MODE):
                if self.selected_role == 0:  # Master
                    self.state = MASTER_MODE
                else:  # Slave
                    self.state = SLAVE_MODE
                    # Automatically restart slave mode
                    self.start_slave_mode()
            
    def process_message(self, message):
        """Process incoming messages"""
        # Check message type
        if "type" not in message:
            debug_print("Received message with no type")
            return
            
        msg_type = message["type"]
        debug_print(f"Processing message of type: {msg_type}")
        
        # Handle ping messages to keep connection alive
        if msg_type == "ping":
            # Respond with a pong
            pong_message = {
                "type": "pong",
                "timestamp": time.time(),
                "echo": message.get("timestamp", 0)
            }
            self.send_message(pong_message)
            return
            
        # Handle pong responses
        if msg_type == "pong":
            # Just log it, no further action needed
            debug_print("Received pong response")
            return
        
        # Handle playback related messages
        if msg_type == MSG_PLAYBACK_READY:
            debug_print("Remote player is ready for playback")
            self.remote_ready = True
            
            # If both are ready and we're in playing mode, start immediately
            if self.local_ready and self.remote_ready and self.state == PLAYING_MODE:
                debug_print("Both players ready, starting synchronized playback")
                if self.selected_role == 0:  # Master controls playback start
                    self.start_playback()
            return
            
        if msg_type == MSG_NOTE_PLAYED:
            # Remote player is playing a note - add to visualization only
            note = message.get("note")
            octave = message.get("octave")
            instrument = message.get("instrument")
            start_time = message.get("start_time", 0)
            
            # Add to visualization only - no sound played
            self.played_notes.append({
                'note': note,
                'octave': octave,
                'instrument': instrument,
                'time': start_time
            })
            return
            
        if msg_type == MSG_PLAYBACK_COMPLETE:
            debug_print("Remote player has completed playback")
            self.remote_completed = True
            
            # If both completed, return to connected state
            if self.local_completed and self.remote_completed:
                debug_print("Playback completed on both sides")
                self.playback_completed = True
                self.playback_status = "Completed"
                
                # Wait a bit to show completion screen, then return to connected state
                if self.state == PLAYING_MODE:
                    # Use a timer to avoid blocking in this thread
                    timer = threading.Timer(5.0, self.return_to_connected)
                    timer.daemon = True
                    timer.start()
            return
            
        if msg_type == MSG_START_PLAYBACK:
            # Master has signaled to start playback
            debug_print("Received start playback signal from master")
            if self.state == PLAYING_MODE:
                # Start playback immediately when master says so
                self.start_playback()
            return
        
        # Handle connection messages
        if msg_type == MSG_CONNECT:
            # Handle connection request
            if self.selected_role == 0:  # Master
                # Check if track hashes match
                client_hash = message.get("track_hash", "")
                client_id = message.get("slave_id", "unknown")
                client_ip = message.get("slave_ip", "unknown")
                
                debug_print(f"Got connection message from slave {client_id} at {client_ip}")
                
                if client_hash != self.track_hash:
                    # Tracks don't match
                    self.send_message({
                        "type": MSG_ERROR,
                        "message": "Track files don't match"
                    })
                else:
                    # Confirm connection
                    self.send_message({
                        "type": MSG_CONFIRM,
                        "track_name": self.track_name,
                        "master_instrument": self.local_instrument,
                        "slave_instrument": self.remote_instrument,
                        "master_ip": self.local_ip
                    })
                    
                    self.connection_status = f"Connected to slave {client_id}"
                    
        elif msg_type == MSG_CONFIRM:
            # Handle connection confirmation
            self.track_name = message.get("track_name", "Unknown")
            # Get instrument assignments if provided
            master_instrument = message.get("master_instrument")
            slave_instrument = message.get("slave_instrument")
            master_ip = message.get("master_ip", "unknown")
            
            if master_instrument is not None and slave_instrument is not None:
                if self.selected_role == 1:  # Slave
                    self.local_instrument = slave_instrument
                    self.remote_instrument = master_instrument
                    
            debug_print(f"Connection confirmed with track: {self.track_name} from {master_ip}")
            
        elif msg_type == MSG_ERROR:
            # Handle error message
            error_msg = message.get('message', 'Unknown error')
            debug_print(f"Error message received: {error_msg}")
            self.connection_status = f"Error: {error_msg}"
    
    def start_heartbeat(self):
        """Start a heartbeat thread to keep the connection alive"""
        self.heartbeat_running = True
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeats)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        debug_print("Started heartbeat thread")

    def send_heartbeats(self):
        """Send periodic heartbeats to keep the connection alive"""
        try:
            while self.heartbeat_running and self.connection_active:
                # Send a heartbeat every 5 seconds
                heartbeat = {
                    "type": "ping",
                    "timestamp": time.time()
                }
                self.send_message(heartbeat)
                
                # Sleep for 5 seconds
                for _ in range(10):  # Check every 0.5 seconds if we should stop
                    if not self.heartbeat_running or not self.connection_active:
                        break
                    time.sleep(0.5)
                    
        except Exception as e:
            debug_print(f"Heartbeat error: {e}")
        finally:
            debug_print("Heartbeat thread ending")
    
    def calculate_track_hash(self, track_content):
        """Calculate a hash of the track file for validation"""
        return hashlib.md5(track_content.encode()).hexdigest()
    
    def load_track(self, filename="track.txt"):
        """Load a track file"""
        try:
            debug_print(f"Attempting to load track from {filename}")
            # First try to load from the file
            with open(filename, "r") as f:
                content = f.read().strip()
                
            if not content:
                raise ValueError("Track file is empty")
                
            self.track_content = content
            self.track_name = os.path.basename(filename)
            self.track_hash = self.calculate_track_hash(content)
            debug_print(f"Successfully loaded track: {self.track_name} with hash: {self.track_hash}")
            
            # Parse the track data
            self.song_data = content
            self.parsed_song_data = parse_music_data(content)
            debug_print(f"Parsed {len(self.parsed_song_data)} notes from track")
            
            # Print first few notes for debugging
            if self.parsed_song_data:
                for i, note in enumerate(self.parsed_song_data[:3]):
                    debug_print(f"Note {i}: {note['Note']}{note['Octave']} at time {note['Start Time']}, inst: {note.get('Instrument', 0)}")
            
            return True
        except Exception as e:
            debug_print(f"Error loading track file: {e}")
            debug_print("Using fallback track")
            
            # Use the fallback track
            content = FALLBACK_TRACK
            self.track_content = content
            self.track_name = "fallback_track.txt"
            self.track_hash = self.calculate_track_hash(content)
            
            # Parse the fallback track
            self.song_data = content
            self.parsed_song_data = parse_music_data(content)
            debug_print(f"Parsed {len(self.parsed_song_data)} notes from fallback track")
            
            # Print first few notes for debugging
            if self.parsed_song_data:
                for i, note in enumerate(self.parsed_song_data[:3]):
                    debug_print(f"Note {i}: {note['Note']}{note['Octave']} at time {note['Start Time']}, inst: {note.get('Instrument', 0)}")
            
            # Save fallback to track.txt for consistent hash
            try:
                with open("track.txt", "w") as f:
                    f.write(content)
                debug_print("Saved fallback track to track.txt")
            except:
                debug_print("Could not save fallback track to file")
                
            return True
    
    def prepare_for_playback(self):
        """Prepare for playback mode"""
        # Make sure we have song data
        if not self.parsed_song_data:
            debug_print("No song data loaded, trying to load track")
            if not self.load_track():
                debug_print("Failed to load any track for playback")
                self.connection_status = "Error: Could not load track"
                return False
            
        # Reset playback state
        self.local_ready = True
        self.remote_ready = False
        self.playback_completed = False
        self.local_completed = False
        self.remote_completed = False
        self.played_notes = []
        self.upcoming_notes = []
        
        # Calculate the maximum song time for display
        self.max_song_time = 0
        for note in self.parsed_song_data:
            end_time = note['Start Time'] + note['Duration']
            if end_time > self.max_song_time:
                self.max_song_time = end_time
        
        # Make sure we have a reasonable max_song_time (at least 10 seconds)
        if self.max_song_time < 10:
            self.max_song_time = 10
        
        # Add a buffer to the end
        self.max_song_time += 2
                
        # Sort notes by start time for playback
        self.parsed_song_data.sort(key=lambda x: x['Start Time'])
        
        # Update state
        self.state = PLAYING_MODE
        self.playback_status = "Waiting for remote player..."
        
        # Tell the remote player we're ready
        self.send_message({
            "type": MSG_PLAYBACK_READY
        })
        
        # If we're the master, don't wait for confirmation - start right away
        if self.selected_role == 0:  # Master
            debug_print("Master initiating playback")
            self.start_playback()
            
        # Prepare upcoming notes view
        self.update_upcoming_notes(0)
        
        return True
    
    def update_upcoming_notes(self, current_time):
        """Update the list of upcoming notes based on current time"""
        upcoming = []
        for note in self.parsed_song_data:
            # If the note hasn't been played yet and is coming up
            if note['Start Time'] > current_time and note['Start Time'] < current_time + 5:
                upcoming.append(note)
                if len(upcoming) >= 10:  # Limit to 10 upcoming notes
                    break
        
        self.upcoming_notes = upcoming
    
    def start_playback(self):
        """Start the actual playback"""
        debug_print("Starting playback")
        self.playback_status = "Playing..."
        self.start_time = time.time()
        
        # Start the playback thread
        self.playback_running = True
        playback_thread = threading.Thread(target=self.playback_loop)
        playback_thread.daemon = True
        playback_thread.start()
        
        # If we're the master, tell the slave to start
        if self.selected_role == 0:
            self.send_message({
                "type": MSG_START_PLAYBACK
            })
    
    def playback_loop(self):
        """Main playback loop"""
        try:
            debug_print("Playback loop started")
            
            # Get a copy of the song data to avoid thread issues
            song_data = list(self.parsed_song_data)
            
            # Initialize list of notes that haven't been played yet
            pending_notes = list(song_data)
            
            # Main playback loop
            while self.playback_running and not self.playback_completed:
                # Get current time relative to start
                current_time = time.time() - self.start_time
                self.current_time = current_time  # Store for UI
                
                # Update the upcoming notes view
                self.update_upcoming_notes(current_time)
                
                # Find notes to play at this time
                notes_to_play = []
                remaining_notes = []
                
                for note in pending_notes:
                    # If the note should be played now
                    if note['Start Time'] <= current_time:
                        notes_to_play.append(note)
                    else:
                        remaining_notes.append(note)
                
                # Update the pending notes list
                pending_notes = remaining_notes
                
                # Play the notes that should sound now
                for note in notes_to_play:
                    note_name = note['Note']
                    octave = note['Octave']
                    duration = note['Duration']
                    volume = note['Volume']
                    instrument = note.get('Instrument', INSTRUMENTS["PIANO"])
                    
                    # Only play notes for our instrument
                    if instrument == self.local_instrument:
                        debug_print(f"Playing note {note_name}{octave} with {INSTRUMENT_NAMES[instrument]}")
                        # Play the sound locally
                        play_note(note_name, octave, duration, volume, 0.5, instrument)
                        
                        # Send note play message to remote player (just for visualization)
                        self.send_message({
                            "type": MSG_NOTE_PLAYED,
                            "note": note_name,
                            "octave": octave,
                            "instrument": instrument,
                            "start_time": current_time
                        })
                        
                        # Add to played notes for visualization
                        self.played_notes.append({
                            'note': note_name,
                            'octave': octave,
                            'instrument': instrument,
                            'time': current_time
                        })
                
                # Check if we're finished
                if not pending_notes and current_time > self.max_song_time:
                    debug_print("Playback completed")
                    self.local_completed = True
                    self.send_message({
                        "type": MSG_PLAYBACK_COMPLETE
                    })
                    
                    # If remote has already completed too, mark as done
                    if self.remote_completed:
                        self.playback_completed = True
                        self.playback_status = "Completed"
                    else:
                        self.playback_status = "Waiting for remote to finish..."
                    
                    break
                
                # Small sleep to prevent CPU hogging
                time.sleep(0.01)
                
        except Exception as e:
            debug_print(f"Playback error: {e}")
            self.playback_status = f"Error: {e}"
        finally:
            self.playback_running = False
    
    def return_to_connected(self):
        """Return to the connected state after playback"""
        if self.state == PLAYING_MODE:
            self.state = CONNECTION_ACTIVE
            self.playback_status = "Ready"
            self.played_notes = []
            self.upcoming_notes = []
            debug_print("Returned to connected state")
    
    def close_sockets(self):
        """Close all socket connections"""
        debug_print("Closing all sockets")
        
        if hasattr(self, 'socket') and self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            
        if hasattr(self, 'client_socket') and self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
            
        if hasattr(self, 'broadcast_socket') and self.broadcast_socket:
            try:
                self.broadcast_socket.close()
            except:
                pass
            self.broadcast_socket = None
            
        if hasattr(self, 'response_socket') and self.response_socket:
            try:
                self.response_socket.close()
            except:
                pass
            self.response_socket = None
    
    def cleanup(self):
        """Clean up network resources"""
        debug_print("Cleaning up network resources")
        
        # Stop all running threads first
        self.discovery_running = False
        self.connection_active = False
        if hasattr(self, 'heartbeat_running'):
            self.heartbeat_running = False
        if hasattr(self, 'playback_running'):
            self.playback_running = False
        
        # Give threads a moment to respond to the stop signal
        time.sleep(0.2)
        
        # Close all sockets
        self.close_sockets()
    
    def draw_button(self, text, position, size):
        """Draw a button with text"""
        # Draw button background
        rect = pygame.Rect(position, size)
        pygame.draw.rect(self.screen, BUTTON_BG, rect, border_radius=10)
        
        # Draw border
        border_width = 2
        pygame.draw.rect(self.screen, BUTTON_BORDER, rect, width=border_width, border_radius=10)
        
        # Draw text
        text_surface = self.font.render(text, True, TEXT_COLOR)
        text_rect = text_surface.get_rect(
            center=(position[0] + size[0]//2, position[1] + size[1]//2)
        )
        self.screen.blit(text_surface, text_rect)
        
        return rect
        
    def draw_role_selection(self):
        """Draw the role selection screen"""
        # Draw title
        title = self.large_font.render("Select Connection Role", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        
        # Draw role description
        if self.selected_role == 0:
            desc = [
                "Master mode: Host the connection",
                "You will scan for slaves and select one to connect to",
                "You will play Piano by default"
            ]
        else:
            desc = [
                "Slave mode: Wait to be discovered",
                "You will be discovered by a master and selected",
                "You will play Electro Guitar by default"
            ]
        
        y_pos = 180
        for line in desc:
            desc_text = self.font.render(line, True, (200, 200, 200))
            self.screen.blit(desc_text, (WIDTH//2 - desc_text.get_width()//2, y_pos))
            y_pos += 40
        
        # Display network IP
        ip_text = self.font.render(f"Your IP Address: {self.local_ip}", True, ID_YELLOW)
        self.screen.blit(ip_text, (WIDTH//2 - ip_text.get_width()//2, y_pos + 20))
        
        # Draw buttons
        master_btn = self.draw_button(
            "Master", 
            (WIDTH//4 - 100, HEIGHT//2 - 40), 
            (200, 80)
        )
        if self.selected_role == 0:
            # Highlight selected button
            pygame.draw.rect(self.screen, (0, 100, 255), master_btn, width=4, border_radius=10)
        
        slave_btn = self.draw_button(
            "Slave", 
            (WIDTH - WIDTH//4 - 100, HEIGHT//2 - 40), 
            (200, 80)
        )
        if self.selected_role == 1:
            # Highlight selected button
            pygame.draw.rect(self.screen, (0, 100, 255), slave_btn, width=4, border_radius=10)
        
        # Draw instructions
        instructions = [
            "Press 'A' to switch between options",
            "Press 'Enter' to select",
            "Press 'Esc' to return to main menu"
        ]
        
        y_pos = HEIGHT - 150
        for instr in instructions:
            instr_text = self.small_font.render(instr, True, (200, 200, 200))
            self.screen.blit(instr_text, (WIDTH//2 - instr_text.get_width()//2, y_pos))
            y_pos += 30
    
    def draw_master_screen(self):
        """Draw the master connection screen"""
        # Draw title
        title = self.large_font.render("Master Mode", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        
        # Draw status
        status_color = STATUS_RED
        if self.connection_status == "Disconnected":
            status_color = STATUS_RED
        elif "Error" in self.connection_status:
            status_color = STATUS_RED
        elif "Connected" in self.connection_status:
            status_color = STATUS_GREEN
        else:
            status_color = STATUS_ORANGE
            
        status = self.font.render(f"Status: {self.connection_status}", True, status_color)
        self.screen.blit(status, (WIDTH//2 - status.get_width()//2, 180))
        
        # Draw your ID
        id_text = self.font.render(f"Your ID: {self.id}", True, TEXT_COLOR)
        self.screen.blit(id_text, (WIDTH//2 - id_text.get_width()//2, 230))
        
        # Draw your IP
        ip_text = self.font.render(f"Your IP: {self.local_ip}", True, ID_YELLOW)
        self.screen.blit(ip_text, (WIDTH//2 - ip_text.get_width()//2, 270))
        
        # Draw instrument info
        local_instr = self.font.render(f"Your Instrument: {INSTRUMENT_NAMES[self.local_instrument]}", True, TEXT_COLOR)
        self.screen.blit(local_instr, (WIDTH//2 - local_instr.get_width()//2, 320))
        
        remote_instr = self.font.render(f"Remote Instrument: {INSTRUMENT_NAMES[self.remote_instrument]}", True, TEXT_COLOR)
        self.screen.blit(remote_instr, (WIDTH//2 - remote_instr.get_width()//2, 360))
        
        # Draw track info
        track_text = self.font.render(f"Current Track: {self.track_name}", True, TEXT_COLOR)
        self.screen.blit(track_text, (WIDTH//2 - track_text.get_width()//2, 400))
        
        # Draw track note count
        notes_text = self.small_font.render(f"Notes in track: {len(self.parsed_song_data)}", True, (200, 200, 200))
        self.screen.blit(notes_text, (WIDTH//2 - notes_text.get_width()//2, 440))
        
        # Draw track hash for debugging
        hash_text = self.small_font.render(f"Track Hash: {self.track_hash[:16]}...", True, (150, 150, 150))
        self.screen.blit(hash_text, (WIDTH//2 - hash_text.get_width()//2, 470))
        
        # Draw buttons
        scan_btn = self.draw_button(
            "Scan for Slaves", 
            (WIDTH//2 - 150, 510), 
            (300, 60)
        )
        
        load_btn = self.draw_button(
            "Load Track", 
            (WIDTH//2 - 150, 590), 
            (300, 60)
        )
        
        # Draw instructions
        instructions = [
            "Press 'S' to scan for slaves",
            "Press 'L' to load track",
            "Press 'Esc' to return to role selection"
        ]
        
        y_pos = HEIGHT - 120
        for instr in instructions:
            instr_text = self.small_font.render(instr, True, (200, 200, 200))
            self.screen.blit(instr_text, (WIDTH//2 - instr_text.get_width()//2, y_pos))
            y_pos += 30
    
    def draw_slave_screen(self):
        """Draw the slave connection screen"""
        # Draw title
        title = self.large_font.render("Slave Mode", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        
        # Draw status
        status_color = STATUS_ORANGE
        if "Discovered" in self.connection_status:
            status_color = STATUS_ORANGE
        elif "Connected" in self.connection_status:
            status_color = STATUS_GREEN
        elif self.connection_status == "Disconnected" or "Error" in self.connection_status:
            status_color = STATUS_RED
        elif "Limited" in self.connection_status:
            status_color = (255, 200, 0)  # Darker orange for limited discovery
            
        status = self.font.render(f"Status: {self.connection_status}", True, status_color)
        self.screen.blit(status, (WIDTH//2 - status.get_width()//2, 180))
        
        # Draw your ID
        id_text = self.large_font.render(f"Your ID: {self.id}", True, ID_YELLOW)
        self.screen.blit(id_text, (WIDTH//2 - id_text.get_width()//2, 240))
        
        # Draw your IP
        ip_text = self.font.render(f"Your IP: {self.local_ip}", True, ID_YELLOW)
        self.screen.blit(ip_text, (WIDTH//2 - ip_text.get_width()//2, 300))
        
        info_text = self.font.render("Masters will see this ID when scanning", True, (200, 200, 200))
        self.screen.blit(info_text, (WIDTH//2 - info_text.get_width()//2, 340))
        
        # Draw instrument info
        local_instr = self.font.render(f"Your Instrument: {INSTRUMENT_NAMES[self.local_instrument]}", True, TEXT_COLOR)
        self.screen.blit(local_instr, (WIDTH//2 - local_instr.get_width()//2, 390))
        
        remote_instr = self.font.render(f"Remote Instrument: {INSTRUMENT_NAMES[self.remote_instrument]}", True, TEXT_COLOR)
        self.screen.blit(remote_instr, (WIDTH//2 - remote_instr.get_width()//2, 430))
        
        # Draw track info
        track_text = self.font.render(f"Current Track: {self.track_name}", True, TEXT_COLOR)
        self.screen.blit(track_text, (WIDTH//2 - track_text.get_width()//2, 480))
        
        # Draw track note count
        notes_text = self.small_font.render(f"Notes in track: {len(self.parsed_song_data)}", True, (200, 200, 200))
        self.screen.blit(notes_text, (WIDTH//2 - notes_text.get_width()//2, 510))
        
        # Draw track hash for debugging
        hash_text = self.small_font.render(f"Track Hash: {self.track_hash[:16]}...", True, (150, 150, 150))
        self.screen.blit(hash_text, (WIDTH//2 - hash_text.get_width()//2, 540))
        
        # Draw load button
        load_btn = self.draw_button(
            "Load Track", 
            (WIDTH//2 - 150, 580), 
            (300, 60)
        )
        
        # Draw instructions
        instructions = [
            "Press 'L' to load track",
            "Press 'Esc' to return to role selection"
        ]
        
        y_pos = HEIGHT - 100
        for instr in instructions:
            instr_text = self.small_font.render(instr, True, (200, 200, 200))
            self.screen.blit(instr_text, (WIDTH//2 - instr_text.get_width()//2, y_pos))
            y_pos += 30
            
    def draw_slave_select_screen(self):
        """Draw the slave selection screen"""
        # Draw title
        title = self.large_font.render("Select a Slave", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        
        # Draw status
        status_color = STATUS_ORANGE
        if "Error" in self.connection_status:
            status_color = STATUS_RED
        elif "Connected" in self.connection_status:
            status_color = STATUS_GREEN
        elif "timeout" in self.connection_status.lower():
            status_color = STATUS_RED
        
        status = self.font.render(f"Status: {self.connection_status}", True, status_color)
        self.screen.blit(status, (WIDTH//2 - status.get_width()//2, 160))
        
        # Draw IP info
        ip_text = self.font.render(f"Your IP: {self.local_ip}", True, ID_YELLOW)
        self.screen.blit(ip_text, (WIDTH//2 - ip_text.get_width()//2, 200))
        
        # Get available slaves - use a copy to avoid thread issues
        global active_slaves
        slave_ids = list(active_slaves.keys())
        
        # Debug display
        debug_text = self.small_font.render(f"Active slaves: {len(slave_ids)}", True, (100, 255, 100))
        self.screen.blit(debug_text, (20, 10))
        
        if not slave_ids:
            # No slaves found
            no_slaves_text = self.font.render("No slaves found. Make sure they are running in slave mode.", True, STATUS_RED)
            self.screen.blit(no_slaves_text, (WIDTH//2 - no_slaves_text.get_width()//2, HEIGHT//2))
            
            net_info = self.small_font.render("Both computers must be on the same network with same track loaded", True, (200, 200, 200))
            self.screen.blit(net_info, (WIDTH//2 - net_info.get_width()//2, HEIGHT//2 + 40))
            
            # Draw retry button
            retry_btn = self.draw_button(
                "Retry Scan", 
                (WIDTH//2 - 150, HEIGHT//2 + 100), 
                (300, 60)
            )
        else:
            # Draw slave list
            list_y = 240
            list_title = self.font.render("Available Slaves:", True, TEXT_COLOR)
            self.screen.blit(list_title, (WIDTH//2 - list_title.get_width()//2, list_y))
            
            # Adjust selected index if out of bounds
            if self.selected_slave_index >= len(slave_ids):
                self.selected_slave_index = 0
            
            # Draw each slave in the list
            for i, slave_id in enumerate(slave_ids):
                slave_y = list_y + 50 + i * 50
                slave_info = active_slaves[slave_id]
                slave_ip = slave_info.get("ip", "Unknown IP")
                
                # Draw the button for this slave
                slave_btn = self.draw_button(
                    f"Slave ID: {slave_id} ({slave_ip})", 
                    (WIDTH//2 - 200, slave_y), 
                    (400, 40)
                )
                
                # Highlight selected slave
                if i == self.selected_slave_index:
                    pygame.draw.rect(self.screen, (0, 100, 255), slave_btn, width=4, border_radius=10)
            
            # Draw connect button
            if slave_ids:
                connect_btn = self.draw_button(
                    "Connect to Selected Slave", 
                    (WIDTH//2 - 200, HEIGHT - 150), 
                    (400, 60)
                )
        
        # Draw instructions
        instructions = [
            "Up/Down to select a slave",
            "Press 'Enter' to connect",
            "Press 'R' to refresh list",
            "Press 'Esc' to return"
        ]
        
        y_pos = HEIGHT - 100
        for instr in instructions:
            instr_text = self.small_font.render(instr, True, (200, 200, 200))
            self.screen.blit(instr_text, (WIDTH//2 - instr_text.get_width()//2, y_pos))
            y_pos += 25
            
    def draw_active_connection(self):
        """Draw the active connection screen"""
        # Draw title
        role_text = "Master" if self.selected_role == 0 else "Slave"
        title = self.large_font.render(f"Connected - {role_text} Mode", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        
        # Draw connection info
        status = self.font.render(f"Status: {self.connection_status}", True, STATUS_GREEN)
        self.screen.blit(status, (WIDTH//2 - status.get_width()//2, 180))
        
        # Draw IP info
        ip_text = self.font.render(f"Your IP: {self.local_ip}", True, ID_YELLOW)
        self.screen.blit(ip_text, (WIDTH//2 - ip_text.get_width()//2, 220))
        
        # Draw track info
        track_text = self.font.render(f"Current Track: {self.track_name}", True, TEXT_COLOR)
        self.screen.blit(track_text, (WIDTH//2 - track_text.get_width()//2, 260))
        
        # Draw track note count
        notes_text = self.small_font.render(f"Notes in track: {len(self.parsed_song_data)}", True, (200, 200, 200))
        self.screen.blit(notes_text, (WIDTH//2 - notes_text.get_width()//2, 290))
        
        # Draw instrument info
        local_instr = self.font.render(f"Your Instrument: {INSTRUMENT_NAMES[self.local_instrument]}", True, TEXT_COLOR)
        self.screen.blit(local_instr, (WIDTH//2 - local_instr.get_width()//2, 330))
        
        remote_instr = self.font.render(f"Remote Instrument: {INSTRUMENT_NAMES[self.remote_instrument]}", True, TEXT_COLOR)
        self.screen.blit(remote_instr, (WIDTH//2 - remote_instr.get_width()//2, 370))
        
        # Draw "Start Playing" button
        play_btn = self.draw_button(
            "Start Playing", 
            (WIDTH//2 - 150, HEIGHT//2 + 50), 
            (300, 60)
        )
        
        # Draw network info
        net_info = self.small_font.render("Connection established successfully between computers", True, (200, 200, 200))
        self.screen.blit(net_info, (WIDTH//2 - net_info.get_width()//2, HEIGHT//2 + 130))
        
        # Draw instructions
        instructions = [
            "Press 'P' to start playing",
            "Press 'Esc' to disconnect and return"
        ]
        
        y_pos = HEIGHT - 100
        for instr in instructions:
            instr_text = self.small_font.render(instr, True, (200, 200, 200))
            self.screen.blit(instr_text, (WIDTH//2 - instr_text.get_width()//2, y_pos))
            y_pos += 30
    
    def draw_playing_screen(self):
        """Draw the playing screen with visual display of notes"""
        # Draw title
        title = self.large_font.render("Playing Music", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        # Draw playback status
        status_color = STATUS_GREEN if "Playing" in self.playback_status else STATUS_ORANGE
        if "Error" in self.playback_status:
            status_color = STATUS_RED
        elif "Completed" in self.playback_status:
            status_color = STATUS_GREEN
            
        status = self.font.render(f"Status: {self.playback_status}", True, status_color)
        self.screen.blit(status, (WIDTH//2 - status.get_width()//2, 100))
        
        # Draw time progress
        progress_text = self.font.render(f"Time: {self.current_time:.2f}s / {self.max_song_time:.2f}s", True, TEXT_COLOR)
        self.screen.blit(progress_text, (WIDTH//2 - progress_text.get_width()//2, 140))
        
        # Draw progress bar
        progress_width = WIDTH - 200
        progress_height = 20
        progress_x = 100
        progress_y = 180
        
        # Draw background
        pygame.draw.rect(self.screen, (50, 50, 50), (progress_x, progress_y, progress_width, progress_height))
        
        # Draw progress
        if self.max_song_time > 0:
            progress_percentage = min(1.0, self.current_time / self.max_song_time)
            filled_width = int(progress_width * progress_percentage)
            pygame.draw.rect(self.screen, (0, 200, 0), (progress_x, progress_y, filled_width, progress_height))
        
        # Draw divider line between instruments
        divider_y = HEIGHT//2
        pygame.draw.line(self.screen, (100, 100, 100), (0, divider_y), (WIDTH, divider_y), 2)
        
        # Draw instrument labels
        piano_label = self.font.render(f"Piano ({INSTRUMENT_NAMES[INSTRUMENTS['PIANO']]})", True, PIANO_COLOR)
        guitar_label = self.font.render(f"Electro Guitar ({INSTRUMENT_NAMES[INSTRUMENTS['ELECTRO_GUITAR']]})", True, GUITAR_COLOR)
        
        # Position the labels
        self.screen.blit(piano_label, (20, divider_y - 40))
        self.screen.blit(guitar_label, (20, divider_y + 10))
        
        # Draw note visualizations
        self.draw_notes(divider_y)
        
        # Draw instruments for this player
        if self.local_instrument == INSTRUMENTS["PIANO"]:
            local_text = self.small_font.render("You are playing Piano parts", True, PIANO_COLOR)
            self.screen.blit(local_text, (WIDTH - 250, divider_y - 40))
        else:
            local_text = self.small_font.render("You are playing Guitar parts", True, GUITAR_COLOR)
            self.screen.blit(local_text, (WIDTH - 250, divider_y + 10))
        
        # Draw instructions
        if "Completed" in self.playback_status:
            instr_text = self.font.render("Playback Completed! Press 'Esc' to return", True, (200, 200, 200))
            self.screen.blit(instr_text, (WIDTH//2 - instr_text.get_width()//2, HEIGHT - 50))
        else:
            instr_text = self.small_font.render("Press 'Esc' to stop playback and return", True, (200, 200, 200))
            self.screen.blit(instr_text, (WIDTH//2 - instr_text.get_width()//2, HEIGHT - 30))
    
    def draw_notes(self, divider_y):
        """Draw the piano roll display of notes"""
        # Constants for drawing
        note_height = 25
        timeline_x = 100
        timeline_width = WIDTH - 200
        
        # Piano section (above divider)
        piano_y = divider_y - 170
        piano_height = 120
        
        # Guitar section (below divider)
        guitar_y = divider_y + 50
        guitar_height = 120
        
        # Draw piano section background
        pygame.draw.rect(self.screen, (40, 40, 60), (timeline_x, piano_y, timeline_width, piano_height))
        
        # Draw guitar section background
        pygame.draw.rect(self.screen, (60, 40, 40), (timeline_x, guitar_y, timeline_width, guitar_height))
        
        # Draw vertical timeline at current position
        if self.current_time > 0 and self.max_song_time > 0:
            current_x = timeline_x + int((timeline_width / self.max_song_time) * self.current_time)
            pygame.draw.line(self.screen, (255, 255, 0), 
                            (current_x, piano_y - 10), 
                            (current_x, guitar_y + guitar_height + 10), 3)
        
        # Draw played notes
        for note in self.played_notes:
            if note['time'] > self.current_time - 5:  # Only show recent notes
                note_x = timeline_x + int((timeline_width / self.max_song_time) * note['time'])
                note_width = 10  # Fixed width for played notes
                
                # Determine color and position based on instrument
                if note['instrument'] == INSTRUMENTS["PIANO"]:
                    # Draw in piano section
                    # Vary y position based on the note
                    note_index = list(FREQS.keys()).index(note['note'])
                    note_y = piano_y + note_index * (piano_height / len(FREQS))
                    
                    pygame.draw.rect(self.screen, PIANO_COLOR, 
                                    (note_x, note_y, note_width, note_height))
                else:
                    # Draw in guitar section
                    note_index = list(FREQS.keys()).index(note['note'])
                    note_y = guitar_y + note_index * (guitar_height / len(FREQS))
                    
                    pygame.draw.rect(self.screen, GUITAR_COLOR, 
                                    (note_x, note_y, note_width, note_height))
        
        # Draw upcoming notes if we have song data
        if self.upcoming_notes:
            for note in self.upcoming_notes:
                note_start = note['Start Time']
                if note_start > self.current_time:  # Only draw upcoming notes
                    note_x = timeline_x + int((timeline_width / self.max_song_time) * note_start)
                    note_width = max(5, int((timeline_width / self.max_song_time) * note['Duration']))
                    
                    # Determine color and position based on instrument
                    instrument = note.get('Instrument', INSTRUMENTS["PIANO"])
                    if instrument == INSTRUMENTS["PIANO"]:
                        # Draw in piano section - transparent to indicate upcoming
                        note_index = list(FREQS.keys()).index(note['Note'])
                        note_y = piano_y + note_index * (piano_height / len(FREQS))
                        
                        # Draw outline for upcoming notes
                        pygame.draw.rect(self.screen, PIANO_COLOR, 
                                        (note_x, note_y, note_width, note_height), 1)
                    else:
                        # Draw in guitar section - transparent to indicate upcoming
                        note_index = list(FREQS.keys()).index(note['Note'])
                        note_y = guitar_y + note_index * (guitar_height / len(FREQS))
                        
                        # Draw outline for upcoming notes
                        pygame.draw.rect(self.screen, GUITAR_COLOR, 
                                        (note_x, note_y, note_width, note_height), 1)
    
    def handle_events(self):
        """Handle user input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.cleanup()
                return False
            
            if event.type == pygame.KEYDOWN:
                # ESC key handling
                if event.key == pygame.K_ESCAPE:
                    if self.state == ROLE_SELECTION:
                        self.cleanup()
                        return False  # Exit to main menu
                    elif self.state == SLAVE_SELECT:
                        # Return to master mode
                        self.discovery_running = False
                        time.sleep(0.2)  # Give time for thread to clean up
                        self.state = MASTER_MODE
                        self.connection_status = "Disconnected"
                    elif self.state == CONNECTION_ACTIVE:
                        # Disconnect and return to previous mode
                        self.connection_active = False
                        time.sleep(0.2)  # Give time for thread to clean up
                        
                        if self.selected_role == 0:  # Master
                            self.state = MASTER_MODE
                        else:  # Slave
                            self.state = SLAVE_MODE
                            # Auto-restart slave listening
                            self.start_slave_mode()
                        
                        self.connection_status = "Disconnected"
                    elif self.state == PLAYING_MODE:
                        # Stop playback and return to connected state
                        self.playback_running = False
                        self.state = CONNECTION_ACTIVE
                        self.playback_status = "Ready"
                    else:
                        # Clean up any active connections
                        self.cleanup()
                        self.state = ROLE_SELECTION
                        self.connection_status = "Disconnected"
                
                # Role selection state
                elif self.state == ROLE_SELECTION:
                    # A key to toggle between options
                    if event.key == pygame.K_a:
                        self.selected_role = 1 - self.selected_role  # Toggle between Master/Slave
                    
                    # Enter to confirm selection
                    elif event.key == pygame.K_RETURN:
                        if self.selected_role == 0:
                            self.state = MASTER_MODE
                            self.local_instrument = INSTRUMENTS["PIANO"]
                            self.remote_instrument = INSTRUMENTS["ELECTRO_GUITAR"]
                            self.load_track()  # Auto-load track
                        else:
                            self.state = SLAVE_MODE
                            self.local_instrument = INSTRUMENTS["ELECTRO_GUITAR"]
                            self.remote_instrument = INSTRUMENTS["PIANO"]
                            # Auto-start slave mode listening
                            if self.load_track():  # Auto-load track
                                self.start_slave_mode()
                
                # Master mode
                elif self.state == MASTER_MODE:
                    # 'S' to scan for slaves
                    if event.key == pygame.K_s:
                        # Check if track is loaded
                        if not self.track_hash:
                            self.connection_status = "Load a track first"
                            self.load_track()  # Auto-load track.txt
                        else:
                            if self.start_server():
                                self.connection_status = "Scanning for slaves..."
                    
                    # 'L' to load track
                    elif event.key == pygame.K_l:
                        if self.load_track():
                            self.connection_status = "Track loaded"
                
                # Slave mode
                elif self.state == SLAVE_MODE:
                    # 'L' to load track
                    if event.key == pygame.K_l:
                        if self.load_track():
                            self.connection_status = "Track loaded"
                            # Restart slave mode with new track
                            self.start_slave_mode()
                
                # Slave selection screen
                elif self.state == SLAVE_SELECT:
                    global active_slaves
                    slave_ids = list(active_slaves.keys())
                    
                    # Up/Down to navigate the list
                    if event.key == pygame.K_UP:
                        if slave_ids:
                            self.selected_slave_index = (self.selected_slave_index - 1) % len(slave_ids)
                    elif event.key == pygame.K_DOWN:
                        if slave_ids:
                            self.selected_slave_index = (self.selected_slave_index + 1) % len(slave_ids)
                    
                    # Enter to select a slave
                    elif event.key == pygame.K_RETURN:
                        if slave_ids and self.selected_slave_index < len(slave_ids):
                            selected_id = slave_ids[self.selected_slave_index]
                            selected_slave = active_slaves[selected_id]
                            self.connect_to_slave(selected_slave)
                    
                    # R to refresh the scan
                    elif event.key == pygame.K_r:
                        # Clear and restart scan
                        self.discovery_running = False
                        time.sleep(0.2)  # Give time for thread to clean up
                        active_slaves.clear()
                        self.start_server()
                
                # Active connection
                elif self.state == CONNECTION_ACTIVE:
                    # 'P' to start playing
                    if event.key == pygame.K_p:
                        # Switch to playback mode
                        self.prepare_for_playback()
        
        return True
    
    def draw(self):
        """Draw the appropriate screen based on current state"""
        # Clear screen
        self.screen.fill(BG_COLOR)
        
        # Draw appropriate screen based on state
        if self.state == ROLE_SELECTION:
            self.draw_role_selection()
        elif self.state == MASTER_MODE:
            self.draw_master_screen()
        elif self.state == SLAVE_MODE:
            self.draw_slave_screen()
        elif self.state == SLAVE_SELECT:
            self.draw_slave_select_screen()
        elif self.state == CONNECTION_ACTIVE:
            self.draw_active_connection()
        elif self.state == PLAYING_MODE:
            self.draw_playing_screen()
        
        # Update display
        pygame.display.flip()
    
    def run(self):
        """Main loop for connection mode"""
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            self.clock.tick(60)
        
        # Make sure to clean up network resources
        self.cleanup()
        
        pygame.quit()

def main():
    """Main function to run the connection module independently"""
    connection = MusicConnection()
    connection.run()

if __name__ == "__main__":
    main()