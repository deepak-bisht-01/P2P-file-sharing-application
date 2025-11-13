import {
  FileListing,
  FileManifest,
  FileTransfer,
  MessageLogEntry,
  Peer,
  StatusSummary
} from "./types";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || response.statusText);
  }
  return response.json() as Promise<T>;
}

export async function fetchStatus(): Promise<StatusSummary> {
  const response = await fetch(`${API_BASE}/api/status`);
  return handleResponse<StatusSummary>(response);
}

export async function fetchPeers(): Promise<Peer[]> {
  const response = await fetch(`${API_BASE}/api/peers`);
  const data = await handleResponse<{ peers: Peer[] }>(response);
  return data.peers;
}

export async function fetchMessages(limit = 100): Promise<MessageLogEntry[]> {
  const response = await fetch(`${API_BASE}/api/messages?limit=${limit}`);
  const data = await handleResponse<{ messages: MessageLogEntry[] }>(response);
  return data.messages;
}

export async function connectPeer(host: string, port: number): Promise<void> {
  const response = await fetch(`${API_BASE}/api/peers/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ host, port })
  });
  await handleResponse(response);
}

export async function sendMessage(text: string, recipientId?: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, recipient_id: recipientId })
  });
  await handleResponse(response);
}

export async function uploadSharedFile(file: File): Promise<FileManifest> {
  const data = new FormData();
  data.append("file", file);

  const response = await fetch(`${API_BASE}/api/files/upload`, {
    method: "POST",
    body: data
  });
  const payload = await handleResponse<{ file: FileManifest }>(response);
  return payload.file;
}

export async function fetchFiles(): Promise<FileListing> {
  const response = await fetch(`${API_BASE}/api/files`);
  return handleResponse<FileListing>(response);
}

export async function startDownload(fileId: string): Promise<FileTransfer> {
  const response = await fetch(`${API_BASE}/api/files/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_id: fileId })
  });
  const payload = await handleResponse<{ transfer: FileTransfer }>(response);
  return payload.transfer;
}

export async function fetchTransfers(): Promise<FileTransfer[]> {
  const response = await fetch(`${API_BASE}/api/files/transfers`);
  const payload = await handleResponse<{ transfers: FileTransfer[] }>(response);
  return payload.transfers;
}

