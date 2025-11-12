import queue
import threading
from typing import Optional, Callable, Dict, Any
import logging
from datetime import datetime
import time

class MessageQueue:
    """Thread-safe message queue with priority support"""
    
    def __init__(self, max_size: int = 1000):
        self.queue = queue.PriorityQueue(maxsize=max_size)
        self.processing_thread = None
        self.is_running = False
        self.message_handler: Optional[Callable] = None
        self.lock = threading.RLock()
        self.logger = logging.getLogger('MessageQueue')
        
        # Statistics
        self.stats = {
            "messages_processed": 0,
            "messages_failed": 0,
            "queue_full_events": 0
        }
    
    def start(self, message_handler: Callable):
        """Start the message queue processor"""
        self.message_handler = message_handler
        self.is_running = True
        
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        self.logger.info("Message queue started")
    
    def stop(self):
        """Stop the message queue"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        self.logger.info("Message queue stopped")
    
    def put_message(self, message: Any, priority: int = 5) -> bool:
        """Add message to queue with priority (1=highest, 10=lowest)"""
        try:
            # Create priority item (priority, timestamp, message)
            # Using timestamp ensures FIFO for same priority
            item = (priority, time.time(), message)
            
            self.queue.put(item, block=False)
            return True
            
        except queue.Full:
            self.stats["queue_full_events"] += 1
            self.logger.warning("Message queue is full")
            return False
    
    def _process_messages(self):
        """Process messages from the queue"""
        while self.is_running:
            try:
                # Get message with timeout to allow checking is_running
                priority, timestamp, message = self.queue.get(timeout=1)
                
                # Process message
                if self.message_handler:
                    try:
                        self.message_handler(message)
                        self.stats["messages_processed"] += 1
                        message.status = "sent"
                        
                    except Exception as e:
                        self.logger.error(f"Error processing message {message.message_id}: {e}")
                        self.stats["messages_failed"] += 1
                        message.status = "failed"
                        message.retry_count += 1
                        
                        # Retry logic (simple version for week 1)
                        if message.retry_count < 3:
                            self.put_message(message, priority=8)  # Lower priority for retry
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error in message processor: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            **self.stats,
            "queue_size": self.queue.qsize(),
            "is_running": self.is_running
        }