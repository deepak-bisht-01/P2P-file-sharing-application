import { FormEvent, useState } from "react";

interface Props {
  onSend: (text: string, recipientId?: string) => Promise<void>;
  selectedPeer: string | null;
  isBusy: boolean;
}

export function MessageComposer({ onSend, selectedPeer, isBusy }: Props) {
  const [text, setText] = useState("");
  const [broadcast, setBroadcast] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!text.trim()) {
      setError("Enter a message to send.");
      return;
    }

    if (!broadcast && !selectedPeer) {
      setError("Select a peer or enable broadcast.");
      return;
    }

    try {
      await onSend(text.trim(), broadcast ? undefined : selectedPeer || undefined);
      setText("");
    } catch (err) {
      setError((err as Error).message || "Failed to send message");
    }
  }

  return (
    <section className="card card--form">
      <h2>Send Message</h2>
      <form className="form" onSubmit={handleSubmit}>
        <div className="form__group">
          <label htmlFor="message">Message</label>
          <textarea
            id="message"
            name="message"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={3}
            placeholder="Hello, peer!"
          />
        </div>
        <div className="form__group form__group--inline">
          <label className="checkbox">
            <input
              type="checkbox"
              checked={broadcast}
              onChange={(event) => setBroadcast(event.target.checked)}
            />
            Broadcast to all peers
          </label>
          {!broadcast && selectedPeer ? (
            <span className="muted monospace">Selected peer: {selectedPeer}</span>
          ) : null}
        </div>
        {error ? <p className="form__error">{error}</p> : null}
        <button className="btn btn--primary" type="submit" disabled={isBusy}>
          {isBusy ? "Sending…" : "Send"}
        </button>
      </form>
    </section>
  );
}

