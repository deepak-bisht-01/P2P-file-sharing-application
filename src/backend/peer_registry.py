import threading
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import logging
from src.backend.models import Peer


class PeerRegistry:
    """In-memory registry of known peers"""
    
    def __init__(self):
        self.peers: Dict[str, Peer] = {}  # peer_id -> Peer
        self.lock = threading.RLock()
        self.logger = logging.getLogger('PeerRegistry')
        
        # Cleanup thread for offline peers
        self.cleanup_interval = 60  # seconds
        self.offline_threshold = 300  # 5 minutes
        self.cleanup_thread = None
        self.is_running = False
    
    def start(self):
        """Start the registry with cleanup thread"""
        self.is_running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        self.logger.info("Peer registry started")
    
    def stop(self):
        """Stop the registry"""
        self.is_running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
    
    def register_peer(self, peer: Peer) -> bool:
        """Register a new peer or update existing"""
        with self.lock:
            is_new = peer.peer_id not in self.peers
            self.peers[peer.peer_id] = peer
            
            action = "registered" if is_new else "updated"
            self.logger.info(f"Peer {peer.peer_id} {action}")
            
            return is_new
    
    def get_peer(self, peer_id: str) -> Optional[Peer]:
        """Get peer by ID"""
        with self.lock:
            return self.peers.get(peer_id)
    
    def get_all_peers(self) -> List[Peer]:
        """Get all registered peers"""
        with self.lock:
            return list(self.peers.values())
    
    def get_online_peers(self) -> List[Peer]:
        """Get only online peers"""
        with self.lock:
            return [p for p in self.peers.values() if p.status == "online"]
    
    def update_peer_status(self, peer_id: str, status: str):
        """Update peer status"""
        with self.lock:
            if peer_id in self.peers:
                self.peers[peer_id].status = status
                self.peers[peer_id].last_seen = datetime.now()
    
    def mark_peer_seen(self, peer_id: str):
        """Update last seen timestamp"""
        with self.lock:
            if peer_id in self.peers:
                self.peers[peer_id].last_seen = datetime.now()
                self.peers[peer_id].status = "online"
    
    def remove_peer(self, peer_id: str) -> bool:
        """Remove a peer from registry"""
        with self.lock:
            if peer_id in self.peers:
                del self.peers[peer_id]
                self.logger.info(f"Peer {peer_id} removed")
                return True
            return False
    
    def _cleanup_loop(self):
        """Periodically check and mark offline peers"""
        while self.is_running:
            try:
                self._check_peer_status()
                threading.Event().wait(self.cleanup_interval)
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    def _check_peer_status(self):
        """Check and update peer status based on last seen"""
        threshold = datetime.now() - timedelta(seconds=self.offline_threshold)
        
        with self.lock:
            for peer in self.peers.values():
                if peer.status == "online" and peer.last_seen < threshold:
                    peer.status = "offline"
                    self.logger.info(f"Peer {peer.peer_id} marked offline")
    
    def find_route_to_peer(self, target_peer_id: str) -> Optional[List[str]]:
        """Simple routing - for week 1, just direct connection"""
        # Week 2 will implement proper routing
        with self.lock:
            if target_peer_id in self.peers and self.peers[target_peer_id].status == "online":
                return [target_peer_id]  # Direct route
            return None
    def list_connected_peers(self) -> List[Peer]:
    
        with self.lock:
            connected = [p for p in self.peers.values() if p.status == "online"]
            self.logger.debug(f"Listing {len(connected)} connected peers")
            return connected
