export interface Peer {
  peer_id: string;
  address: string;
  port: number;
  status: string;
  metadata?: Record<string, unknown>;
  last_seen: string;
  public_key?: string | null;
}

export interface MessageLogEntry {
  direction: "incoming" | "outgoing";
  payload: Record<string, unknown>;
  sent_at?: string;
  received_at?: string;
}

export interface StatusSummary {
  peer_id: string;
  port: number;
  messages_processed: number;
  messages_failed: number;
  queue_size: number;
  active_connections: string[];
  files_shared_local: number;
  files_known_remote: number;
  transfers_active: number;
}

export interface FileManifest {
  file_id: string;
  file_name: string;
  file_size: number;
  chunk_size: number;
  chunk_count: number;
  checksum?: string;
  owner?: string;
  peers?: string[];
}

export interface FileTransfer {
  file_id: string;
  file_name: string;
  file_size: number;
  chunk_size: number;
  chunk_count: number;
  destination: string;
  started_at: number;
  completed_at: number | null;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  bytes_received: number;
  chunks_completed: number;
  peers_used: string[];
  error?: string | null;
}

export interface FileListing {
  local: FileManifest[];
  remote: FileManifest[];
}

