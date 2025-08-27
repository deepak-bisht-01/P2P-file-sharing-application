import uuid
import hashlib
import json
import os
from typing import Dict
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class PeerIdentity:
    def __init__(self, identity_file: str = None):
        """
        Initializes the PeerIdentity object.
        Loads identity from file or creates a new one if it doesn't exist.
        """
        self.identity_file = identity_file or "peer_identity.json"
        self.peer_id = None
        self.public_key = None
        self.private_key = None
        self.peer_info: Dict = {}

        if os.path.exists(self.identity_file):
            self.load_identity()
        else:
            self.create_identity()

    def create_identity(self) -> str:
        """
        Generates a new identity with UUID and RSA key pair.
        Returns the generated peer ID.
        """
        base_uuid = str(uuid.uuid4())

        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

        pub_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        key_hash = hashlib.sha256(pub_key_bytes).hexdigest()[:16]
        self.peer_id = f"{base_uuid}-{key_hash}"

        self.peer_info = {
            "peer_id": self.peer_id,
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }

        self.save_identity()
        return self.peer_id

    def save_identity(self):
        """
        Saves identity (peer ID and RSA key pair) to a file.
        """
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        identity_data = {
            "peer_id": self.peer_id,
            "private_key": private_pem.decode("utf-8"),
            "public_key": public_pem.decode("utf-8"),
            "peer_info": self.peer_info
        }

        with open(self.identity_file, "w") as f:
            json.dump(identity_data, f, indent=2)

    def load_identity(self):
        """
        Loads identity from file, including peer ID and RSA keys.
        """
        try:
            with open(self.identity_file, "r") as f:
                identity_data = json.load(f)

            self.peer_id = identity_data["peer_id"]
            self.peer_info = identity_data.get("peer_info", {})

            self.private_key = serialization.load_pem_private_key(
                identity_data["private_key"].encode("utf-8"),
                password=None
            )
            self.public_key = serialization.load_pem_public_key(
                identity_data["public_key"].encode("utf-8")
            )

        except Exception as e:
            raise RuntimeError(f"Failed to load identity from {self.identity_file}: {e}")

    def get_public_key_string(self) -> str:
        """
        Returns public key in PEM string format.
        """
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

    def verify_peer_id(self, peer_id: str, public_key_string: str) -> bool:
        """
        Verifies that a peer ID matches the given public key string.
        """
        try:
            if "-" in peer_id:
                _, key_hash = peer_id.rsplit("-", 1)
                actual_hash = hashlib.sha256(public_key_string.encode()).hexdigest()[:16]
                return key_hash == actual_hash
        except Exception:
            pass
        return False
