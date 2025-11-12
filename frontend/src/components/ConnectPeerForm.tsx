import { FormEvent, useState } from "react";

interface Props {
  onConnect: (host: string, port: number) => Promise<void>;
  isBusy: boolean;
}

export function ConnectPeerForm({ onConnect, isBusy }: Props) {
  const [host, setHost] = useState("127.0.0.1");
  const [port, setPort] = useState(5001);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!host || !port) {
      setError("Provide host and port");
      return;
    }

    try {
      await onConnect(host.trim(), Number(port));
    } catch (err) {
      setError((err as Error).message || "Failed to connect");
    }
  }

  return (
    <section className="card card--form">
      <h2>Connect to Peer</h2>
      <form className="form" onSubmit={handleSubmit}>
        <div className="form__group">
          <label htmlFor="host">Host</label>
          <input
            id="host"
            name="host"
            type="text"
            value={host}
            onChange={(event) => setHost(event.target.value)}
            placeholder="127.0.0.1"
          />
        </div>
        <div className="form__group">
          <label htmlFor="port">Port</label>
          <input
            id="port"
            name="port"
            type="number"
            min={1}
            max={65535}
            value={port}
            onChange={(event) => setPort(Number(event.target.value))}
          />
        </div>
        {error ? <p className="form__error">{error}</p> : null}
        <button className="btn btn--primary" type="submit" disabled={isBusy}>
          {isBusy ? "Connecting…" : "Connect"}
        </button>
      </form>
    </section>
  );
}

