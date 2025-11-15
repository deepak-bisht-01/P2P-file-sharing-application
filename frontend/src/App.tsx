import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  connectPeer,
  fetchFiles,
  fetchMessages,
  fetchPeers,
  fetchStatus,
  fetchTransfers,
  sendMessage,
  startDownload,
  uploadSharedFile
} from "./api";
import "./App.css";
import { StatusSummaryCard } from "./components/StatusSummaryCard";
import { PeerList } from "./components/PeerList";
import { ConnectPeerForm } from "./components/ConnectPeerForm";
import { MessageComposer } from "./components/MessageComposer";
import { MessagePanel } from "./components/MessagePanel";
import {
  FileListing,
  FileTransfer,
  MessageLogEntry,
  Peer,
  StatusSummary
} from "./types";
import { FileTransferPanel } from "./components/FileTransferPanel";

const POLL_INTERVAL = 5_000;

function usePolling<T>(
  callback: () => Promise<T>,
  deps: unknown[] = [],
  intervalMs = POLL_INTERVAL
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isInitialLoadRef = useRef(true);

  const fetchData = useCallback(async () => {
    // Only show loading state on initial load, not on every refresh
    const isInitial = isInitialLoadRef.current;
    if (isInitial) {
      setLoading(true);
    }
    try {
      const result = await callback();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      if (isInitial) {
        setLoading(false);
        isInitialLoadRef.current = false;
      }
    }
  }, deps);

  useEffect(() => {
    void fetchData();
    const timer = window.setInterval(() => {
      void fetchData();
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [fetchData, intervalMs]);

  return { data, loading, refresh: fetchData, error };
}

export default function App() {
  const [selectedPeer, setSelectedPeer] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isStartingDownload, setIsStartingDownload] = useState(false);
  const [activeDownloadId, setActiveDownloadId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const {
    data: status,
    loading: statusLoading,
    refresh: refreshStatus,
    error: statusError
  } = usePolling<StatusSummary>(fetchStatus, []);

  const {
    data: peers,
    loading: peersLoading,
    refresh: refreshPeers,
    error: peersError
  } = usePolling<Peer[]>(fetchPeers, []);

  const {
    data: messages,
    loading: messagesLoading,
    refresh: refreshMessages,
    error: messagesError
  } = usePolling<MessageLogEntry[]>(() => fetchMessages(200), []);

  const {
    data: files,
    loading: filesLoading,
    refresh: refreshFiles,
    error: filesError
  } = usePolling<FileListing>(fetchFiles, [], POLL_INTERVAL);

  const {
    data: transfers,
    loading: transfersLoading,
    refresh: refreshTransfers,
    error: transfersError
  } = usePolling<FileTransfer[]>(fetchTransfers, [], 5_000);

  const handleConnect = useCallback(
    async (host: string, port: number) => {
      setIsConnecting(true);
      try {
        await connectPeer(host, port);
        await Promise.all([refreshPeers(), refreshStatus()]);
      } finally {
        setIsConnecting(false);
      }
    },
    [refreshPeers, refreshStatus]
  );

  const handleSend = useCallback(
    async (text: string, recipientId?: string) => {
      setIsSending(true);
      try {
        await sendMessage(text, recipientId);
        await Promise.all([refreshMessages()]);
      } finally {
        setIsSending(false);
      }
    },
    [refreshMessages]
  );

  const handleUpload = useCallback(
    async (file: File) => {
      setIsUploading(true);
      setUploadError(null);
      try {
        await uploadSharedFile(file);
        await Promise.all([refreshFiles(), refreshStatus()]);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to upload file";
        setUploadError(message);
        throw error;
      } finally {
        setIsUploading(false);
      }
    },
    [refreshFiles, refreshStatus]
  );

  const handleStartDownload = useCallback(
    async (fileId: string) => {
      setIsStartingDownload(true);
      setActiveDownloadId(fileId);
      setDownloadError(null);
      try {
        await startDownload(fileId);
        await Promise.all([refreshTransfers(), refreshStatus(), refreshFiles()]);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to start download";
        setDownloadError(message);
      } finally {
        setIsStartingDownload(false);
        setActiveDownloadId(null);
      }
    },
    [refreshTransfers, refreshStatus, refreshFiles]
  );

  useEffect(() => {
    if (!peers || peers.length === 0) {
      setSelectedPeer(null);
      return;
    }

    if (selectedPeer) {
      const stillExists = peers.some((peer) => peer.peer_id === selectedPeer);
      if (!stillExists) {
        setSelectedPeer(null);
      }
    }
  }, [peers, selectedPeer]);

  const peersWithoutSelf = useMemo(() => {
    if (!peers || !status) {
      return peers ?? [];
    }
    return peers.filter((peer) => peer.peer_id !== status.peer_id);
  }, [peers, status]);

  return (
    <div className="app">
      <header className="app__header">
        <h1>P2P Messaging Dashboard</h1>
        <p className="muted">
          Monitor peers, connect to the network, exchange messages, and share files in real time.
        </p>
      </header>

      <main className="app__grid">
        <div className="app__column">
          <StatusSummaryCard
            status={status ?? null}
            isLoading={statusLoading}
            error={statusError}
          />
          <ConnectPeerForm onConnect={handleConnect} isBusy={isConnecting} />
          <MessageComposer onSend={handleSend} selectedPeer={selectedPeer} isBusy={isSending} />
          <FileTransferPanel
            listing={files ?? null}
            transfers={transfers ?? []}
            listingLoading={filesLoading}
            listingError={filesError}
            transfersLoading={transfersLoading}
            transfersError={transfersError}
            onUpload={handleUpload}
            onRefresh={async () => {
              await Promise.all([refreshFiles(), refreshTransfers()]);
            }}
            onStartDownload={handleStartDownload}
            isUploading={isUploading}
            uploadError={uploadError}
            isStartingDownload={isStartingDownload}
            activeDownloadId={activeDownloadId}
            downloadError={downloadError}
          />
        </div>

        <div className="app__column app__column--grow">
          <PeerList
            peers={peersWithoutSelf}
            selectedPeer={selectedPeer}
            onSelect={setSelectedPeer}
            onRefresh={refreshPeers}
            isLoading={peersLoading}
            error={peersError}
          />
          <MessagePanel
            messages={messages ?? []}
            isLoading={messagesLoading}
            error={messagesError}
          />
        </div>
      </main>

      <footer className="app__footer">
        <span>API endpoint: {import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}</span>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => {
            void Promise.all([
              refreshStatus(),
              refreshPeers(),
              refreshMessages(),
              refreshFiles(),
              refreshTransfers()
            ]).catch(() => undefined);
          }}
        >
          Refresh All
        </button>
      </footer>
    </div>
  );
}

