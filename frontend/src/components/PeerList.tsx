import { clsx } from "clsx";
import { Peer } from "../types";

interface Props {
  peers: Peer[];
  selectedPeer: string | null;
  onSelect: (peerId: string) => void;
  onRefresh: () => void;
  isLoading: boolean;
  error: string | null;
}

export function PeerList({
  peers,
  selectedPeer,
  onSelect,
  onRefresh,
  isLoading,
  error
}: Props) {
  return (
    <section className="card card--peers">
      <header>
        <h2>Peers</h2>
        <button type="button" className="btn btn--ghost" onClick={onRefresh}>
          Refresh
        </button>
      </header>
      {isLoading ? (
        <p className="muted">Loading peers…</p>
      ) : error ? (
        <p className="form__error">{error}</p>
      ) : (
        <ul className="peer-list">
          {peers
            .filter((peer) => peer.peer_id && peer.peer_id.length > 0)
            .map((peer) => {
              const isSelected = peer.peer_id === selectedPeer;
              const isOnline = peer.status === "online";

              return (
                <li
                  key={peer.peer_id}
                  className={clsx("peer-list__item", {
                    "peer-list__item--selected": isSelected,
                    "peer-list__item--online": isOnline,
                    "peer-list__item--offline": !isOnline
                  })}
                  onClick={() => onSelect(peer.peer_id)}
                >
                  <div>
                    <p className="peer-list__id monospace">{peer.peer_id}</p>
                    <p className="peer-list__meta">
                      {peer.address}:{peer.port}
                    </p>
                  </div>
                  <span className="peer-list__status">{isOnline ? "Online" : "Offline"}</span>
                </li>
              );
            })}
        </ul>
      )}
      {peers.length === 0 && !isLoading ? (
        <p className="muted">No peers discovered yet. Connect to a peer to get started.</p>
      ) : null}
    </section>
  );
}

