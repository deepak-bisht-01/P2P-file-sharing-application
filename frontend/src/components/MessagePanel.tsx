import { MessageLogEntry } from "../types";

interface Props {
  messages: MessageLogEntry[];
  isLoading: boolean;
  error: string | null;
}

function formatTimestamp(entry: MessageLogEntry): string {
  const timestamp = entry.sent_at || entry.received_at;
  if (!timestamp) {
    return "—";
  }
  return new Date(timestamp).toLocaleTimeString();
}

export function MessagePanel({ messages, isLoading, error }: Props) {
  return (
    <section className="card card--messages">
      <header>
        <h2>Message Log</h2>
      </header>
      <div className="message-log">
        {isLoading ? (
          <p className="muted">Loading messages…</p>
        ) : error ? (
          <p className="form__error">{error}</p>
        ) : messages.length === 0 ? (
          <p className="muted">No messages yet. Start a conversation to see updates here.</p>
        ) : (
          messages.map((message, index) => (
            <article
              key={`${message.payload.message_id ?? index}-${message.direction}-${index}`}
              className={`message-entry message-entry--${message.direction}`}
            >
              <header>
                <span className="badge">
                  {message.direction === "incoming" ? "Incoming" : "Outgoing"}
                </span>
                <span className="timestamp">{formatTimestamp(message)}</span>
              </header>
              <pre>{JSON.stringify(message.payload, null, 2)}</pre>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

