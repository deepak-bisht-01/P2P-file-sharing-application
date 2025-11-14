import click
import threading
import sys
import time
from colorama import init, Fore, Style
import logging
import logging.config
import yaml
import os
import socket

# Import all components
from src.core.peer_node import PeerNode
from src.core.connection_manager import ConnectionManager
from src.core.message_protocol import MessageProtocol, MessageType
from src.security.peer_identity import PeerIdentity
from src.security.message_validator import MessageValidator
from src.backend.message_queue import MessageQueue
from src.backend.peer_registry import PeerRegistry
from src.backend.models import Peer, Message

# Initialize colorama for Windows support
init()

class P2PCLI:
    def __init__(self, port: int, identity_file: str = None):
        self.port = port
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.identity = PeerIdentity(identity_file)
        self.validator = MessageValidator()
        self.peer_registry = PeerRegistry()
        self.message_queue = MessageQueue()
        
        # Initialize peer node
        self.peer_node = PeerNode(port=port, peer_id=self.identity.peer_id)
        self.connection_manager = ConnectionManager(self._handle_incoming_message)
        self.peer_node.connection_manager = self.connection_manager
        


        
        # UI state
        self.running = True
        self.current_peer = None
        
        print(f"{Fore.GREEN}P2P Messaging System{Style.RESET_ALL}")
        print(f"Peer ID: {Fore.CYAN}{self.identity.peer_id}{Style.RESET_ALL}")
        print(f"Listening on port: {Fore.YELLOW}{port}{Style.RESET_ALL}")
        print("-" * 50)
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Load logging config
        with open('config/logging.yaml', 'r') as f:
            config = yaml.safe_load(f)
            logging.config.dictConfig(config)
    
    def start(self):
        """Start all components"""
        # Start backend services
        self.peer_registry.start()
        self.message_queue.start(self._send_message_handler)
        
        # Start network node
        self.peer_node.start()
        
        # Register self in registry
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_addr = s.getsockname()[0]
            s.close()
        except Exception:
            local_addr = "localhost"
        self_peer = Peer(
            peer_id=self.identity.peer_id,
            address=local_addr,
            port=self.port,
            public_key=self.identity.get_public_key_string()
        )
        self.peer_registry.register_peer(self_peer)
        
        # Start CLI loop
        self._cli_loop()
    
    def _handle_incoming_message(self, peer_id: str, raw_message: str):
        """Handle incoming messages from network"""
        try:
            # Decode message
            message_dict = MessageProtocol.decode_message(raw_message.encode())
            if not message_dict:
                return
            
            # Validate message
            is_valid, error = self.validator.validate_message(message_dict)
            if not is_valid:
                print(f"{Fore.RED}Invalid message from {peer_id}: {error}{Style.RESET_ALL}")
                return
            
            # Update peer registry
            self.peer_registry.mark_peer_seen(message_dict['sender_id'])
            
            # Handle based on message type
            msg_type = message_dict['type']
            
            if msg_type == 'handshake':
                self._handle_handshake(message_dict)
            elif msg_type == 'text':
                self._handle_text_message(message_dict)
            elif msg_type == 'ping':
                self._handle_ping(message_dict)
                
        except Exception as e:
            logging.error(f"Error handling message: {e}")
    
    def _handle_handshake(self, message: dict):
        """Handle handshake message"""
        sender_id = message['sender_id']
        peer_info = message.get('content', {})
        
        # Register peer
        peer = Peer(
            peer_id=sender_id,
            address=peer_info.get('address', 'unknown'),
            port=peer_info.get('port', 0),
            public_key=peer_info.get('public_key')
        )
        self.peer_registry.register_peer(peer)
        temp_id = f"{peer.address}:{peer.port}"
        self.connection_manager.associate_temp_id_with_peer_id(temp_id, sender_id)
        print(f"{Fore.GREEN}✓ Handshake from {sender_id}{Style.RESET_ALL}")
    
    def _handle_text_message(self, message: dict):
        """Handle text message"""
        sender_id = message['sender_id']
        text = message['content']['text']
        
        # Display message
        print(f"\n{Fore.CYAN}[{sender_id[:8]}...]: {Style.RESET_ALL}{text}")
        print(f"{Fore.YELLOW}> {Style.RESET_ALL}", end='', flush=True)
    
    def _handle_ping(self, message: dict):
        """Handle ping message"""
        # Send pong response
        pong = MessageProtocol.create_message(
            MessageType.PONG,
            self.identity.peer_id,
            message['sender_id']
        )
        self.connection_manager.send_message(
            message['sender_id'],
            MessageProtocol.encode_message(pong)
        )
    
    def _send_message_handler(self, message: Message):
        """Handler for message queue - sends messages over network"""
        try:
            wire_format = message.to_wire_format()
            encoded = MessageProtocol.encode_message(wire_format)
            
            if message.recipient_id:
                # Direct message
                success = self.connection_manager.send_message(
                    message.recipient_id,
                    encoded
                )
                if not success:
                    print(f"{Fore.RED}Failed to send message to {message.recipient_id}{Style.RESET_ALL}")
            else:
                # Broadcast
                self.connection_manager.broadcast_message(encoded)
                
        except Exception as e:
            logging.error(f"Error sending message: {e}")
    
    def _cli_loop(self):
        """Main CLI interaction loop"""
        self._print_help()
        
        while self.running:
            try:
                command = input(f"{Fore.YELLOW}> {Style.RESET_ALL}").strip()
                
                if not command:
                    continue
                
                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if cmd == 'help' or cmd == 'h':
                    self._print_help()
                elif cmd == 'connect' or cmd == 'c':
                    self._connect_to_peer(args)
                elif cmd == 'list' or cmd == 'l':
                    self._list_peers()
                elif cmd == 'send' or cmd == 's':
                    self._send_message(args)
                elif cmd == 'select' or cmd == 'sel':
                    self._select_peer(args)
                elif cmd == 'info' or cmd == 'i':
                    self._show_info()
                elif cmd == 'quit' or cmd == 'q':
                    self._quit()
                else:
                    print(f"{Fore.RED}Unknown command: {cmd}{Style.RESET_ALL}")
                    
            except KeyboardInterrupt:
                print("\n")
                self._quit()
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
    
    def _print_help(self):
        """Print help information"""
        print(f"\n{Fore.GREEN}Available Commands:{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}connect <host:port>{Style.RESET_ALL} - Connect to a peer")
        print(f"  {Fore.CYAN}list{Style.RESET_ALL} - List connected peers")
        print(f"  {Fore.CYAN}select <peer_id>{Style.RESET_ALL} - Select peer for messaging")
        print(f"  {Fore.CYAN}send <message>{Style.RESET_ALL} - Send message to selected peer")
        print(f"  {Fore.CYAN}info{Style.RESET_ALL} - Show system information")
        print(f"  {Fore.CYAN}help{Style.RESET_ALL} - Show this help")
        print(f"  {Fore.CYAN}quit{Style.RESET_ALL} - Exit the application\n")
    
    def _connect_to_peer(self, args: str):
        """Connect to a peer"""
        try:
            if ':' not in args:
                print(f"{Fore.RED}Usage: connect <host:port>{Style.RESET_ALL}")
                return
            
            host, port = args.split(':')
            port = int(port)
            
            print(f"Connecting to {host}:{port}...")
            
            # Connect
            sock = self.peer_node.connect_to_peer(host, port)
            if not sock:
                print(f"{Fore.RED}Failed to connect{Style.RESET_ALL}")
                return
            
            # Create temporary peer ID
            temp_peer_id = f"{host}:{port}"
            
            # Add to connection manager
            self.connection_manager.add_connection(sock, (host, port), temp_peer_id)
            
            # Send handshake
            try:
                local_addr = sock.getsockname()[0]
            except Exception:
                local_addr = "localhost"
            handshake = MessageProtocol.create_handshake(
                self.identity.peer_id,
                {
                    "address": local_addr,
                    "port": self.port,
                    "public_key": self.identity.get_public_key_string()
                }
            )
            self.connection_manager.send_message(temp_peer_id, handshake)
            peer = Peer(
                    peer_id=temp_peer_id,   # placeholder, will be replaced by their real ID on handshake
                    address=host,
                    port=port,
                    public_key=None
)
            self.peer_registry.register_peer(peer)
            print(f"{Fore.GREEN}✓ Connected to {host}:{port}{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}Connection failed: {e}{Style.RESET_ALL}")
    
    def _list_peers(self):
        """List all known peers"""
        peers = self.peer_registry.get_all_peers()
        active_connections = self.connection_manager.get_active_connections()
        
        print(f"\n{Fore.GREEN}Known Peers:{Style.RESET_ALL}")
        for peer in peers:
            if peer.peer_id == self.identity.peer_id:
                continue
                
            status_color = Fore.GREEN if peer.status == "online" else Fore.RED
            connected = "✓" if peer.peer_id in active_connections else "✗"
            selected = "◄" if peer.peer_id == self.current_peer else " "
            
            print(f"  {selected} [{connected}] {peer.peer_id[:16]}... "
                  f"{status_color}({peer.status}){Style.RESET_ALL}")
        
        if len(peers) == 1:  # Only self
            print(f"  {Fore.YELLOW}No other peers discovered yet{Style.RESET_ALL}")
    
    def _select_peer(self, peer_id: str):
        """Select a peer for messaging"""
        if not peer_id:
            print(f"{Fore.RED}Usage: select <peer_id>{Style.RESET_ALL}")
            return
        
        # Allow partial peer ID
        peers = self.peer_registry.get_all_peers()
        matches = [p for p in peers if p.peer_id.startswith(peer_id)]
        
        if not matches:
            print(f"{Fore.RED}No peer found matching: {peer_id}{Style.RESET_ALL}")
        elif len(matches) > 1:
            print(f"{Fore.YELLOW}Multiple matches found. Be more specific:{Style.RESET_ALL}")
            for p in matches:
                print(f"  - {p.peer_id}")
        else:
            self.current_peer = matches[0].peer_id
            print(f"{Fore.GREEN}Selected peer: {self.current_peer}{Style.RESET_ALL}")
    
    def _send_message(self, text: str):
        """Send a message"""
        if not text:
            print(f"{Fore.RED}Usage: send <message>{Style.RESET_ALL}")
            return
        
        if not self.current_peer:
            print(f"{Fore.RED}No peer selected. Use 'select <peer_id>' first{Style.RESET_ALL}")
            return
        
        # Create message
        import uuid
        message = Message(
            message_id=str(uuid.uuid4()),
            sender_id=self.identity.peer_id,
            recipient_id=self.current_peer,
            message_type="text",
            content={"text": text}
        )
        
        # Queue for sending
        if self.message_queue.put_message(message):
            print(f"{Fore.GREEN}✓ Message queued{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to queue message{Style.RESET_ALL}")
    
    def _show_info(self):
        """Show system information"""
        stats = self.message_queue.get_stats()
        connections = self.connection_manager.get_active_connections()
        
        print(f"\n{Fore.GREEN}System Information:{Style.RESET_ALL}")
        print(f"  Peer ID: {self.identity.peer_id}")
        print(f"  Port: {self.port}")
        print(f"  Active Connections: {len(connections)}")
        print(f"  Messages Processed: {stats['messages_processed']}")
        print(f"  Messages Failed: {stats['messages_failed']}")
        print(f"  Queue Size: {stats['queue_size']}")
    
    def _quit(self):
        """Quit the application"""
        print(f"\n{Fore.YELLOW}Shutting down...{Style.RESET_ALL}")
        self.running = False
        
        # Stop all components
        self.message_queue.stop()
        self.peer_registry.stop()
        self.peer_node.stop()
        
        print(f"{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
        sys.exit(0)

@click.command()
@click.option('--port', '-p', default=5000, help='Port to listen on')
@click.option('--identity', '-i', help='Identity file path')
def main(port, identity):
    """P2P Messaging System CLI"""
    cli = P2PCLI(port, identity)
    cli.start()

if __name__ == '__main__':
    main()