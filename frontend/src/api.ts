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
    let errorMessage: string;
    try {
      const errorBody = await response.text();
      // Try to parse as JSON for structured error messages
      try {
        const errorJson = JSON.parse(errorBody);
        errorMessage = errorJson.detail || errorJson.message || errorBody || response.statusText;
      } catch {
        errorMessage = errorBody || response.statusText;
      }
    } catch {
      errorMessage = response.statusText || "Request failed";
    }
    throw new Error(errorMessage);
  }
  return response.json() as Promise<T>;
}

// Wrapper to handle network errors gracefully
async function fetchWithErrorHandling(
  url: string,
  options?: RequestInit
): Promise<Response> {
  try {
    const response = await fetch(url, options);
    return response;
  } catch (error) {
    // Handle network errors (ERR_NETWORK_CHANGED, connection refused, etc.)
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new Error(
        `Network error: Unable to connect to server. Please ensure the backend server is running at ${API_BASE}`
      );
    }
    if (error instanceof Error) {
      // Check for specific network error messages
      if (error.message.includes("ERR_NETWORK_CHANGED")) {
        throw new Error(
          "Network connection changed. Please check your internet connection and ensure the server is still running."
        );
      }
      if (error.message.includes("Failed to fetch") || error.message.includes("NetworkError")) {
        throw new Error(
          `Cannot reach server at ${API_BASE}. Is the backend server running?`
        );
      }
    }
    throw error;
  }
}

export async function fetchStatus(): Promise<StatusSummary> {
  const response = await fetchWithErrorHandling(`${API_BASE}/api/status`);
  return handleResponse<StatusSummary>(response);
}

export async function fetchPeers(): Promise<Peer[]> {
  const response = await fetchWithErrorHandling(`${API_BASE}/api/peers`);
  const data = await handleResponse<{ peers: Peer[] }>(response);
  return data.peers;
}

export async function fetchMessages(limit = 100): Promise<MessageLogEntry[]> {
  const response = await fetchWithErrorHandling(`${API_BASE}/api/messages?limit=${limit}`);
  const data = await handleResponse<{ messages: MessageLogEntry[] }>(response);
  return data.messages;
}

export async function connectPeer(host: string, port: number): Promise<void> {
  const response = await fetchWithErrorHandling(`${API_BASE}/api/peers/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ host, port })
  });
  await handleResponse(response);
}

export async function sendMessage(text: string, recipientId?: string): Promise<void> {
  const response = await fetchWithErrorHandling(`${API_BASE}/api/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, recipient_id: recipientId })
  });
  await handleResponse(response);
}

export async function uploadSharedFile(file: File): Promise<FileManifest> {
  const data = new FormData();
  data.append("file", file);

  const response = await fetchWithErrorHandling(`${API_BASE}/api/files/upload`, {
    method: "POST",
    body: data
  });
  const payload = await handleResponse<{ file: FileManifest }>(response);
  return payload.file;
}

export async function fetchFiles(): Promise<FileListing> {
  const response = await fetchWithErrorHandling(`${API_BASE}/api/files`);
  return handleResponse<FileListing>(response);
}

export async function startDownload(fileId: string): Promise<FileTransfer> {
  const response = await fetchWithErrorHandling(`${API_BASE}/api/files/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_id: fileId })
  });
  const payload = await handleResponse<{ transfer: FileTransfer }>(response);
  return payload.transfer;
}

export async function fetchTransfers(): Promise<FileTransfer[]> {
  const response = await fetchWithErrorHandling(`${API_BASE}/api/files/transfers`);
  const payload = await handleResponse<{ transfers: FileTransfer[] }>(response);
  return payload.transfers;
}

export function getFilePreviewUrl(fileId: string): string {
  return `${API_BASE}/api/files/preview/${fileId}`;
}

export function isImageFile(fileName: string): boolean {
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'];
  const ext = fileName.toLowerCase().substring(fileName.lastIndexOf('.'));
  return imageExtensions.includes(ext);
}

