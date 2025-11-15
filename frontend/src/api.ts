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
      // Check if it's a connection refused error
      const errorMessage = error.message.toLowerCase();
      if (errorMessage.includes("failed to fetch") || 
          errorMessage.includes("networkerror") ||
          errorMessage.includes("connection refused") ||
          errorMessage.includes("err_connection_refused")) {
        throw new Error(
          `Connection refused: Cannot connect to backend server at ${API_BASE}. ` +
          `Please ensure the backend server is running. Start it with: python start_api.py --api-port 8000`
        );
      }
      throw new Error(
        `Network error: Unable to connect to server. Please ensure the backend server is running at ${API_BASE}`
      );
    }
    if (error instanceof Error) {
      // Check for specific network error messages
      const errorMessage = error.message.toLowerCase();
      if (errorMessage.includes("err_network_changed")) {
        throw new Error(
          "Network connection changed. Please check your internet connection and ensure the server is still running."
        );
      }
      if (errorMessage.includes("err_connection_refused") || 
          errorMessage.includes("connection refused")) {
        throw new Error(
          `Connection refused: Backend server is not running at ${API_BASE}. ` +
          `Please start the server with: python start_api.py --api-port 8000`
        );
      }
      if (errorMessage.includes("failed to fetch") || errorMessage.includes("networkerror")) {
        throw new Error(
          `Cannot reach server at ${API_BASE}. Is the backend server running? ` +
          `Start it with: python start_api.py --api-port 8000`
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

