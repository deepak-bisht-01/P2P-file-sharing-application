import { StatusSummary } from "../types";

interface Props {
  status: StatusSummary | null;
  isLoading: boolean;
  error: string | null;
}

export function StatusSummaryCard({ status, isLoading, error }: Props) {
  return (
    <section className="card card--status">
      <h2>Network Status</h2>
      {isLoading ? (
        <p className="muted">Loading status…</p>
      ) : error ? (
        <p className="form__error">{error}</p>
      ) : !status ? (
        <p className="muted">No status data available.</p>
      ) : (
        <div className="status-grid">
          <dl>
            <dt>Peer ID</dt>
            <dd className="monospace">{status.peer_id}</dd>
          </dl>
          <dl>
            <dt>Listening Port</dt>
            <dd>{status.port}</dd>
          </dl>
          <dl>
            <dt>Active Connections</dt>
            <dd>{status.active_connections.length}</dd>
          </dl>
          <dl>
            <dt>Processed Messages</dt>
            <dd>{status.messages_processed}</dd>
          </dl>
          <dl>
            <dt>Failed Messages</dt>
            <dd>{status.messages_failed}</dd>
          </dl>
          <dl>
            <dt>Queue Size</dt>
            <dd>{status.queue_size}</dd>
          </dl>
        </div>
      )}
    </section>
  );
}

