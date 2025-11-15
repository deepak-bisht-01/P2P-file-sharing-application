import socket
import threading
import time
from typing import Dict, Tuple, List, Optional
import logging
from collections import defaultdict
from src.backend.models import Peer
from src.core.message_protocol import MessageProtocol, MessageType
 # to avoid circular import
class Connection:
    def __init__(self, socket: socket.socket, address: Tuple[str, int], peer_id: str = None):
        self.socket = socket
        self.address = address
        self.peer_id = peer_id
        self.is_active = True
        self.lock = threading.Lock()
        self.last_activity = time.time()
        self.last_ping = time.time()

class ConnectionManager:
    def __init__(self, message_handler=None, peer_registry=None, peer_id: str = None):
        self.connections: Dict[str, Connection] = {}  # peer_id -> Connection
        self.address_to_peer: Dict[Tuple[str, int], str] = {}  # address -> peer_id
        self.lock = threading.RLock()
        self.message_handler = message_handler
        self.peer_registry = peer_registry   # ✅ store registry if provided
        self.peer_id = peer_id  # Store peer_id for creating ping messages
        self.logger = logging.getLogger('ConnectionManager')
        self.read_timeout = 30.0  # 30 second read timeout
        self.ping_interval = 20.0  # Send ping every 20 seconds
        self.connection_timeout = 60.0  # Mark connection dead after 60 seconds of no activity
        self._keepalive_thread = None
        self._start_keepalive_thread()
    
    def _start_keepalive_thread(self):
        """Start the keepalive thread that periodically sends pings to maintain connections"""
        if self._keepalive_thread is None or not self._keepalive_thread.is_alive():
            self._keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            self._keepalive_thread.start()
            self.logger.info("Keepalive thread started")
    
    def _keepalive_loop(self):
        """Periodically check connections and send pings if needed"""
        while True:
            try:
                time.sleep(self.ping_interval)
                current_time = time.time()
                
                with self.lock:
                    connections_to_check = list(self.connections.items())
                
                for peer_id, conn in connections_to_check:
                    if not conn.is_active:
                        continue
                    
                    # Check if connection has timed out
                    time_since_activity = current_time - conn.last_activity
                    if time_since_activity > self.connection_timeout:
                        self.logger.warning(f"Connection {peer_id} timed out (no activity for {time_since_activity:.1f}s)")
                        self.remove_connection(peer_id)
                        continue
                    
                    # Send ping if needed (ping interval has passed)
                    time_since_ping = current_time - conn.last_ping
                    if time_since_ping >= self.ping_interval:
                        try:
                            # Create proper ping message using MessageProtocol
                            if self.peer_id:
                                ping_message = MessageProtocol.create_message(
                                    MessageType.PING,
                                    self.peer_id,
                                    recipient_id=peer_id
                                )
                                ping_msg = MessageProtocol.encode_message(ping_message)
                            else:
                                # Fallback: simple ping if peer_id not available
                                ping_msg = b'\x00\x00\x00\x0c{"type":"ping"}'
                            with conn.lock:
                                conn.socket.sendall(ping_msg)
                            conn.last_ping = current_time
                            conn.last_activity = current_time
                        except (ConnectionResetError, BrokenPipeError, OSError) as e:
                            errno = getattr(e, 'winerror', getattr(e, 'errno', None))
                            if errno in (10054, 10053, 10038):
                                self.logger.info(f"Connection {peer_id} closed during ping")
                            else:
                                self.logger.warning(f"Failed to send ping to {peer_id}: {e}")
                            self.remove_connection(peer_id)
                        except Exception as e:
                            self.logger.error(f"Error sending ping to {peer_id}: {e}")
                            self.remove_connection(peer_id)
            except Exception as e:
                self.logger.error(f"Error in keepalive loop: {e}")
                time.sleep(1)  # Brief pause before retrying
    
    def add_connection(self, sock: socket.socket, address: Tuple[str, int], peer_id: str = None):
        """Add a new connection"""
        with self.lock:
            if not peer_id:
                peer_id = f"{address[0]}:{address[1]}"
            
            # Check by address first to avoid duplicate connections from same address
            if address in self.address_to_peer:
                old_peer_id = self.address_to_peer[address]
                if old_peer_id in self.connections:
                    existing_conn = self.connections[old_peer_id]
                    # Check if it's the same socket (shouldn't happen, but be safe)
                    if existing_conn.socket == sock:
                        self.logger.debug(f"Connection from {address} already registered with same socket")
                        return
                    # If old connection is still active, close it (reconnection scenario)
                    if existing_conn.is_active:
                        self.logger.info(f"Replacing existing connection from {address} (old peer_id: {old_peer_id})")
                        existing_conn.is_active = False
                        try:
                            existing_conn.socket.close()
                        except:
                            pass
                    # Remove old connection
                    del self.connections[old_peer_id]
                    del self.address_to_peer[address]
            
            # Check if peer_id already exists (might be from a different address)
            if peer_id in self.connections:
                existing_conn = self.connections[peer_id]
                if existing_conn.socket == sock:
                    # Same socket, already registered
                    self.logger.debug(f"Connection {peer_id} already registered with same socket")
                    return
                # Different socket with same peer_id - close old one
                if existing_conn.is_active:
                    self.logger.warning(f"Duplicate connection for peer_id {peer_id}, closing old socket")
                    existing_conn.is_active = False
                    try:
                        existing_conn.socket.close()
                    except:
                        pass
                # Clean up old connection
                if existing_conn.address in self.address_to_peer:
                    del self.address_to_peer[existing_conn.address]
                del self.connections[peer_id]
        
            # Set socket options for better reliability
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                # Set read timeout to detect dead connections
                sock.settimeout(self.read_timeout)
            except Exception as e:
                self.logger.warning(f"Could not set socket options: {e}")
        
            conn = Connection(sock, address, peer_id)
            self.connections[peer_id] = conn
            self.address_to_peer[address] = peer_id

        # ✅ also register the peer (outside lock to avoid deadlock)
        if self.peer_registry:
            from src.backend.models import Peer  # avoid circular import
            peer = Peer(peer_id=peer_id, address=str(address[0]), port=address[1], status="online")
            self.peer_registry.register_peer(peer)

        # Start handler thread for this connection
        handler_thread = threading.Thread(
            target=self._handle_connection,
            args=(conn,)
        )
        handler_thread.daemon = True
        handler_thread.start()
        
        self.logger.info(f"Added connection for peer {peer_id} (remote address={address})")
    
    def _handle_connection(self, conn: Connection):
        """Handle incoming messages from a connection"""
        buffer = b""
        
        while conn.is_active:
            try:
                data = conn.socket.recv(4096)
                if not data:
                    # Remote peer closed connection gracefully
                    self.logger.info(f"Connection {conn.peer_id} closed by remote peer")
                    break
                
                # Update last activity time
                conn.last_activity = time.time()
                buffer += data
                
                # Try to extract complete messages (length-prefixed format)
                while len(buffer) >= 4:
                    # Read the length prefix (4 bytes, big-endian)
                    msg_length = int.from_bytes(buffer[:4], byteorder='big')
                    
                    # Sanity check: reject unreasonably large messages
                    if msg_length > 10 * 1024 * 1024:  # 10MB max
                        self.logger.error(f"Message too large from {conn.peer_id}: {msg_length} bytes")
                        break
                    
                    # Check if we have the complete message
                    if len(buffer) < 4 + msg_length:
                        break  # Wait for more data
                    
                    # Extract the message
                    msg_bytes = buffer[4:4+msg_length]
                    buffer = buffer[4+msg_length:]  # Remove from buffer
                    
                    if self.message_handler:
                        try:
                            msg_json = msg_bytes.decode('utf-8')
                            import json
                            msg_dict = json.loads(msg_json)
                            sender_id = msg_dict.get('sender_id', conn.peer_id)
                            
                            # Update connection peer_id if needed (handshake)
                            # Only associate if sender_id is different and looks like a real peer_id
                            # (not a temp address:port format, unless it's actually the same)
                            current_peer_id = conn.peer_id
                            if sender_id != current_peer_id:
                                # Check if sender_id looks like a real peer_id (not address:port)
                                # Real peer_ids are typically UUIDs or long strings, not simple address:port
                                is_real_peer_id = (':' not in sender_id) or (len(sender_id) > 50)
                                # Also associate if conn.peer_id looks like temp (address:port format)
                                is_temp_id = ':' in current_peer_id and len(current_peer_id) < 50
                                
                                # Always associate if we have a temp ID and receive a real peer_id
                                # Also associate if both are real peer_ids but different (shouldn't happen, but handle it)
                                should_associate = (is_temp_id and is_real_peer_id) or (is_real_peer_id and sender_id != current_peer_id)
                                
                                if should_associate:
                                    self.logger.info(f"Associating connection {current_peer_id} with sender_id {sender_id} from message type {msg_dict.get('type', 'unknown')}")
                                    # Use a lock-safe association
                                    with self.lock:
                                        # Re-check after acquiring lock - connection might have been removed
                                        if current_peer_id in self.connections and self.connections[current_peer_id] == conn:
                                            if self.associate_temp_id_with_peer_id(current_peer_id, sender_id, lock_held=True):
                                                # After association, the connection is now under sender_id
                                                # Update our reference if it exists
                                                if sender_id in self.connections:
                                                    conn = self.connections[sender_id]
                                                    # Update the current_peer_id for this iteration
                                                    current_peer_id = sender_id
                                                    self.logger.info(f"Connection successfully associated: {current_peer_id} -> {sender_id}")
                                                else:
                                                    self.logger.warning(f"Association completed but connection {sender_id} not found in connections dict")
                                            else:
                                                self.logger.warning(f"Failed to associate {current_peer_id} with {sender_id}")
                                        else:
                                            self.logger.warning(f"Connection {current_peer_id} not found or changed during association")
                            
                            # Use the updated sender_id for message handling
                            self.message_handler(sender_id, msg_json)
                        except Exception as e:
                            self.logger.error(f"Error parsing message: {e}")
                            # Fallback
                            try:
                                self.message_handler(conn.peer_id, msg_bytes.decode('utf-8', errors='replace'))
                            except:
                                pass
                        
            except socket.timeout:
                # Read timeout - check if connection is still alive
                if time.time() - conn.last_activity > self.connection_timeout:
                    self.logger.warning(f"Connection {conn.peer_id} timed out (no activity for {self.connection_timeout}s)")
                    break
                # Otherwise, continue waiting
                continue
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                # Connection was reset or closed
                errno = getattr(e, 'winerror', getattr(e, 'errno', None))
                if errno == 10054 or errno == 10053:  # Windows: connection reset/aborted
                    self.logger.info(f"Connection {conn.peer_id} reset by remote host")
                else:
                    self.logger.warning(f"Connection {conn.peer_id} error: {e}")
                break
            except Exception as e:
                # Check if socket is still valid
                if not conn.is_active:
                    break
                errno = getattr(e, 'winerror', getattr(e, 'errno', None))
                if errno == 10038:  # Windows: not a socket
                    self.logger.warning(f"Socket for {conn.peer_id} is no longer valid")
                    break
                self.logger.error(f"Error handling connection {conn.peer_id}: {e}")
                break
        
        # Clean up connection
        self.remove_connection(conn.peer_id)
    
    def send_message(self, peer_id: str, message: bytes) -> bool:
        """Send message to a specific peer (message should be length-prefixed)"""
        with self.lock:
            if peer_id in self.connections:
                conn = self.connections[peer_id]
                if not conn.is_active:
                    return False
                try:
                    with conn.lock:
                        conn.socket.sendall(message)
                    # Update last activity on successful send
                    conn.last_activity = time.time()
                    return True
                except (ConnectionResetError, BrokenPipeError, OSError) as e:
                    errno = getattr(e, 'winerror', getattr(e, 'errno', None))
                    if errno in (10054, 10053, 10038):  # Windows connection errors
                        self.logger.warning(f"Connection {peer_id} closed during send: {e}")
                    else:
                        self.logger.error(f"Failed to send message to {peer_id}: {e}")
                    self.remove_connection(peer_id)
                except Exception as e:
                    self.logger.error(f"Failed to send message to {peer_id}: {e}")
                    self.remove_connection(peer_id)
        return False
    
    def broadcast_message(self, message: bytes, exclude_peer: str = None):
        """Broadcast message to all connected peers"""
        with self.lock:
            for peer_id, conn in list(self.connections.items()):
                if peer_id != exclude_peer:
                    self.send_message(peer_id, message)
    
    def remove_connection(self, peer_id: str):
        """Remove a connection"""
        with self.lock:
            if peer_id in self.connections:
                conn = self.connections[peer_id]
                conn.is_active = False
                try:
                    conn.socket.close()
                except:
                    pass
                
                del self.connections[peer_id]
                if conn.address in self.address_to_peer:
                    del self.address_to_peer[conn.address]
                
                self.logger.info(f"Removed connection for peer {peer_id}")
    
    def get_active_connections(self) -> List[str]:
        """Get list of active peer IDs"""
        with self.lock:
            # Only return connections that are actually active
            return [peer_id for peer_id, conn in self.connections.items() if conn.is_active]
    def associate_temp_id_with_peer_id(self, temp_id: str, real_id: str, lock_held: bool = False) -> bool:
        """Replace a temporary peer_id (like 'host:port') with the real peer_id after handshake
        
        Args:
            temp_id: Temporary peer ID (usually address:port)
            real_id: Real peer ID from handshake
            lock_held: If True, assumes lock is already held (for RLock compatibility)
        """
        # Use context manager only if lock is not already held
        if not lock_held:
            self.lock.acquire()
        try:
            if temp_id not in self.connections:
                self.logger.warning(f"Cannot associate {temp_id} with {real_id}: temp_id not in connections")
                return False

            new_conn = self.connections[temp_id]
            
            # If real_id already exists, we need to handle the duplicate connection
            if real_id in self.connections:
                existing_conn = self.connections[real_id]
                
                # Check if they're actually the same connection (same socket)
                if existing_conn.socket == new_conn.socket:
                    # Same connection, just update the temp_id mapping
                    del self.connections[temp_id]
                    # Update address→peer map
                    for addr, pid in list(self.address_to_peer.items()):
                        if pid == temp_id:
                            self.address_to_peer[addr] = real_id
                    self.logger.info(f"Connection {temp_id} already associated with {real_id}")
                    return True
                
                # Different connections to the same peer - keep the newer one (the one we're updating)
                self.logger.warning(f"Duplicate connection to {real_id}: closing old connection (socket: {existing_conn.socket.fileno()})")
                existing_conn.is_active = False
                try:
                    existing_conn.socket.close()
                except:
                    pass
                # Clean up old connection's address mapping
                if existing_conn.address in self.address_to_peer:
                    del self.address_to_peer[existing_conn.address]
                del self.connections[real_id]

            # Move connection under new key
            conn = self.connections.pop(temp_id)
            conn.peer_id = real_id
            self.connections[real_id] = conn

            # Update address→peer map
            for addr, pid in list(self.address_to_peer.items()):
                if pid == temp_id:
                    self.address_to_peer[addr] = real_id

            self.logger.info(f"Associated temp_id {temp_id} with real_id {real_id}")
            return True
        finally:
            if not lock_held:
                self.lock.release()

    def dump_state(self) -> Dict:
        """Return a serializable snapshot of the connection manager state for diagnostics."""
        with self.lock:
            return {
                "connections": [
                    {
                        "peer_id": pid,
                        "address": f"{conn.address[0]}:{conn.address[1]}",
                        "is_active": conn.is_active
                    }
                    for pid, conn in self.connections.items()
                ],
                "address_to_peer": {f"{addr[0]}:{addr[1]}": pid for addr, pid in self.address_to_peer.items()}
            }
    
    def on_handshake(self, conn, peer_id_from_handshake):
    # remove the temporary mapping
        old_id = conn.peer_id
        if old_id in self.connections:
            del self.connections[old_id]

    # replace with proper peer_id
        conn.peer_id = peer_id_from_handshake
        self.connections[peer_id_from_handshake] = conn

