"""Check wallet balance and whether it has enough SOL to submit a transaction."""

import asyncio
import json
from pathlib import Path

from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient

WALLET_FILE = Path("wallet.json")
RPC_URL = "https://api.mainnet-beta.solana.com"
MIN_SOL = 0.005  # plenty for a single transaction fee (~0.000005 SOL typical)


async def main():
    if not WALLET_FILE.exists():
        print("No wallet.json found. Run:  python scripts/generate_wallet.py")
        return

    kp = Keypair.from_bytes(bytes(json.loads(WALLET_FILE.read_text())))
    pubkey = kp.pubkey()
    print(f"Wallet address: {pubkey}")

    async with AsyncClient(RPC_URL) as client:
        resp = await client.get_balance(pubkey)
        lamports = resp.value
        sol = lamports / 1e9
        print(f"Balance:        {sol:.6f} SOL  ({lamports} lamports)")

        if sol < MIN_SOL:
            needed = MIN_SOL - sol
            print()
            print(f"⚠  Low balance — need at least {MIN_SOL} SOL to pay transaction fees.")
            print(f"   Send ~{needed:.4f} SOL (or ~0.01 SOL to be safe) to:  {pubkey}")
            print()
            print("Options to fund:")
            print("  1. Buy SOL on Coinbase/Kraken/Binance, then withdraw to the address above.")
            print("  2. If someone you know has SOL, ask them to send ~0.01 SOL to that address.")
            print()
            print("Once funded, re-run this script to confirm, then run txline-subscribe.")
        else:
            print(f"✓ Balance sufficient. Ready to subscribe.")
            print()
            print("Next step:")
            print(f"  SOLANA_KEYPAIR_FILE={WALLET_FILE} .venv/bin/txline-subscribe")


asyncio.run(main())
