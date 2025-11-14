import { useMemo, useRef, useState } from "react";
import { FileListing, FileManifest, FileTransfer } from "../types";
import { getFilePreviewUrl, isImageFile } from "../api";

interface Props {
  listing: FileListing | null;
  transfers: FileTransfer[];
  listingLoading: boolean;
  listingError: string | null;
  transfersLoading: boolean;
  transfersError: string | null;
  onUpload: (file: File) => Promise<void>;
  onRefresh: () => Promise<void>;
  onStartDownload: (fileId: string) => Promise<void>;
  isUploading: boolean;
  uploadError: string | null;
  isStartingDownload: boolean;
  activeDownloadId: string | null;
  downloadError: string | null;
}

function formatSize(size: number): string {
  if (size <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const idx = Math.min(units.length - 1, Math.floor(Math.log(size) / Math.log(1024)));
  const value = size / Math.pow(1024, idx);
  return `${value.toFixed(value >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}

function percent(value: number, total: number): number {
  if (total === 0) {
    return 0;
  }
  return Math.min(100, Math.round((value / total) * 100));
}

export function FileTransferPanel({
  listing,
  transfers,
  listingLoading,
  listingError,
  transfersLoading,
  transfersError,
  onUpload,
  onRefresh,
  onStartDownload,
  isUploading,
  uploadError,
  isStartingDownload,
  activeDownloadId,
  downloadError
}: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<{ fileId: string; fileName: string } | null>(null);

  const localFiles = listing?.local ?? [];
  const remoteFiles = listing?.remote ?? [];

  const activeTransfers = useMemo(
    () => transfers.filter((transfer) => transfer.status !== "completed"),
    [transfers]
  );

  const completedTransfers = useMemo(
    () => transfers.filter((transfer) => transfer.status === "completed"),
    [transfers]
  );

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    if (!files || files.length === 0) {
      return;
    }
    const file = files[0];
    setSelectedFileName(file.name);
    try {
      await onUpload(file);
      setSelectedFileName(null);
    } catch (error) {
      // error handled upstream
    } finally {
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  }

  return (
    <section className="card card--files">
      <header>
        <h2>File Sharing</h2>
        <button className="btn btn--ghost" type="button" onClick={() => void onRefresh()}>
          Refresh
        </button>
      </header>

      <div className="file-uploader">
        <input
          ref={inputRef}
          type="file"
          hidden
          onChange={(event) => void handleFileChange(event)}
        />
        <button
          className="btn btn--primary"
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
        >
          {isUploading ? "Uploading…" : "Share File"}
        </button>
        {selectedFileName ? (
          <span className="file-uploader__name">{selectedFileName}</span>
        ) : null}
      </div>
      {uploadError ? <p className="form__error">{uploadError}</p> : null}

      <div className="file-section">
        <h3>Local Files</h3>
        {listingLoading ? (
          <p className="muted">Loading shared files…</p>
        ) : listingError ? (
          <p className="form__error">{listingError}</p>
        ) : localFiles.length === 0 ? (
          <p className="muted">No files shared yet. Upload a file to share it with peers.</p>
        ) : (
          <ul className="file-list">
            {localFiles.map((file: FileManifest) => (
              <li key={file.file_id} className="file-list__item">
                <div>
                  <p className="file-list__name">{file.file_name}</p>
                  <p className="file-list__meta">
                    {formatSize(file.file_size)} · {file.chunk_count} chunks
                  </p>
                </div>
                <div className="file-list__actions">
                  {isImageFile(file.file_name) && (
                    <button
                      className="btn btn--ghost btn--small"
                      type="button"
                      onClick={() => setPreviewFile({ fileId: file.file_id, fileName: file.file_name })}
                    >
                      Preview
                    </button>
                  )}
                  <span className="badge badge--neutral">Shared</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="file-section">
        <h3>Available Downloads</h3>
        {listingLoading ? (
          <p className="muted">Discovering files…</p>
        ) : listingError ? (
          <p className="form__error">{listingError}</p>
        ) : remoteFiles.length === 0 ? (
          <p className="muted">No remote files announced by peers yet.</p>
        ) : (
          <ul className="file-list">
            {remoteFiles.map((file: FileManifest) => (
              <li key={file.file_id} className="file-list__item">
                <div>
                  <p className="file-list__name">{file.file_name}</p>
                  <p className="file-list__meta">
                    {formatSize(file.file_size)} · {file.chunk_count} chunks ·{" "}
                    {file.peers?.length ?? 1} peer(s)
                  </p>
                </div>
                <button
                  className="btn btn--ghost"
                  type="button"
                  onClick={() => void onStartDownload(file.file_id)}
                  disabled={isStartingDownload}
                >
                  {isStartingDownload && activeDownloadId === file.file_id ? "Starting…" : "Download"}
                </button>
              </li>
            ))}
          </ul>
        )}
        {downloadError ? <p className="form__error">{downloadError}</p> : null}
      </div>

      <div className="file-section">
        <h3>Transfers</h3>
        {transfersLoading ? (
          <p className="muted">Updating transfer status…</p>
        ) : transfersError ? (
          <p className="form__error">{transfersError}</p>
        ) : transfers.length === 0 ? (
          <p className="muted">No transfers yet. Start a download to track progress here.</p>
        ) : (
          <div className="transfer-lists">
            {activeTransfers.length > 0 ? (
              <div>
                <h4>In Progress</h4>
                <ul className="transfer-list">
                  {activeTransfers.map((transfer) => (
                    <li key={transfer.file_id} className="transfer-list__item">
                      <div className="transfer-list__summary">
                        <span className="file-list__name">{transfer.file_name}</span>
                        <div className="transfer-list__actions">
                          {isImageFile(transfer.file_name) && transfer.status === "running" && (
                            <button
                              className="btn btn--ghost btn--small"
                              type="button"
                              onClick={() => setPreviewFile({ fileId: transfer.file_id, fileName: transfer.file_name })}
                              title="Preview (may show partial image)"
                            >
                              Preview
                            </button>
                          )}
                          <span className="transfer-list__status">{transfer.status}</span>
                        </div>
                      </div>
                      <div className="transfer-list__meta">
                        <span>{formatSize(transfer.bytes_received)}</span>
                        <span>{formatSize(transfer.file_size)}</span>
                      </div>
                      <div className="progress-bar">
                        <div
                          className="progress-bar__value"
                          style={{
                            width: `${percent(
                              transfer.chunks_completed,
                              transfer.chunk_count
                            )}%`
                          }}
                        />
                      </div>
                      <p className="transfer-list__details">
                        {transfer.chunks_completed}/{transfer.chunk_count} chunks ·{" "}
                        {transfer.peers_used.length} peer(s)
                      </p>
                      {transfer.error ? (
                        <p className="form__error">{transfer.error}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {completedTransfers.length > 0 ? (
              <div>
                <h4>Completed</h4>
                <ul className="transfer-list transfer-list--completed">
                  {completedTransfers.map((transfer) => (
                    <li key={transfer.file_id} className="transfer-list__item">
                      <div className="transfer-list__summary">
                        <span className="file-list__name">{transfer.file_name}</span>
                        <div className="transfer-list__actions">
                          {isImageFile(transfer.file_name) && (
                            <button
                              className="btn btn--ghost btn--small"
                              type="button"
                              onClick={() => setPreviewFile({ fileId: transfer.file_id, fileName: transfer.file_name })}
                            >
                              Preview
                            </button>
                          )}
                          <span className="transfer-list__status transfer-list__status--done">
                            {transfer.status}
                          </span>
                        </div>
                      </div>
                      <p className="transfer-list__details">
                        {formatSize(transfer.file_size)} · {transfer.chunk_count} chunks ·{" "}
                        {transfer.peers_used.length} peer(s)
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}
      </div>

      {previewFile && (
        <div className="preview-modal" onClick={() => setPreviewFile(null)}>
          <div className="preview-modal__content" onClick={(e) => e.stopPropagation()}>
            <div className="preview-modal__header">
              <h3>{previewFile.fileName}</h3>
              <button
                className="btn btn--ghost"
                type="button"
                onClick={() => setPreviewFile(null)}
              >
                ×
              </button>
            </div>
            <div className="preview-modal__body">
              {isImageFile(previewFile.fileName) ? (
                <img
                  src={getFilePreviewUrl(previewFile.fileId)}
                  alt={previewFile.fileName}
                  className="preview-image"
                />
              ) : (
                <div className="preview-placeholder">
                  <p>Preview not available for this file type</p>
                  <a
                    href={getFilePreviewUrl(previewFile.fileId)}
                    download={previewFile.fileName}
                    className="btn btn--primary"
                  >
                    Download File
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

