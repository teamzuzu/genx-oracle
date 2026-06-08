"""
Generate a new Solana keypair and save it to a file.
Run once — keep the file safe, it is your wallet secret key.
"""

import json
import sys
from pathlib import Path

from solders.keypair import Keypair

OUTPUT = Path("wallet.json")

if OUTPUT.exists():
    print(f"[skip] {OUTPUT} already exists — not overwriting.")
    kp = Keypair.from_bytes(bytes(json.loads(OUTPUT.read_text())))
    print(f"Public key: {kp.pubkey()}")
    sys.exit(0)

kp = Keypair()
# Solana CLI-compatible format: array of 64 bytes (secret || public)
key_bytes = list(bytes(kp))
OUTPUT.write_text(json.dumps(key_bytes))
OUTPUT.chmod(0o600)  # owner read-only

print(f"Wallet saved to: {OUTPUT}")
print(f"Public key:      {kp.pubkey()}")
print()
print("IMPORTANT: back up wallet.json somewhere safe — it cannot be recovered.")
print("wallet.json is in .gitignore so it will not be committed.")
