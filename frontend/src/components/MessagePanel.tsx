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

function getMessageType(payload: any): string {
  return payload.type || "unknown";
}

function getMessageText(payload: any): string | null {
  if (payload.type === "text" && payload.content?.text) {
    return payload.content.text;
  }
  return null;
}

function formatSenderId(senderId: string): string {
  if (!senderId) return "Unknown";
  if (senderId.length > 20) {
    return `${senderId.substring(0, 8)}...`;
  }
  return senderId;
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
          messages.map((message, index) => {
            const msgType = getMessageType(message.payload);
            const textContent = getMessageText(message.payload);
            const isTextMessage = msgType === "text" && textContent;
            const isSystemMessage = ["ping", "pong", "handshake"].includes(msgType);
            
            return (
              <article
                key={`${message.payload.message_id ?? index}-${message.direction}-${index}`}
                className={`message-entry message-entry--${message.direction} ${isTextMessage ? "message-entry--text" : ""}`}
              >
                <header>
                  <span className="badge">
                    {message.direction === "incoming" ? "INCOMING" : "OUTGOING"}
                  </span>
                  <span className="timestamp">{formatTimestamp(message)}</span>
                  {!isTextMessage && (
                    <span className="message-type">{msgType.toUpperCase()}</span>
                  )}
                </header>
                {isTextMessage ? (
                  <div className="message-content">
                    <div className="message-text">{textContent}</div>
                    <div className="message-meta">
                      From: {formatSenderId(message.payload.sender_id)}
                      {message.payload.recipient_id && (
                        <> · To: {formatSenderId(message.payload.recipient_id)}</>
                      )}
                    </div>
                  </div>
                ) : isSystemMessage ? (
                  <div className="message-content">
                    <div className="message-system">
                      {msgType === "ping" && "🔄 Keepalive ping"}
                      {msgType === "pong" && "✅ Keepalive pong"}
                      {msgType === "handshake" && "🤝 Connection handshake"}
                    </div>
                    <div className="message-meta">
                      From: {formatSenderId(message.payload.sender_id)}
                    </div>
                  </div>
                ) : (
                  <details className="message-details">
                    <summary>View message details</summary>
                    <pre>{JSON.stringify(message.payload, null, 2)}</pre>
                  </details>
                )}
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}

