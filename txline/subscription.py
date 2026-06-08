"""
On-chain subscription flow for the TxLINE free tier.

Submits a zero-cost transaction to the TxLINE Solana program to activate
a subscription, then exchanges the resulting tx signature + wallet proof
for a long-lived API token.

Program:  9ExbZjAapQww1vfcisDmrngPinHTEfpjYRWMunJgcKaA
TxL mint: sLX1i9dfmsuyFBmJTWuGjjRmG4VPWYK6dRRKSM4BCSx
"""

import asyncio
import json
import logging
from pathlib import Path

import httpx
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from txline.auth import (
    get_guest_jwt,
    build_activation_message,
    sign_message,
    activate_token,
    save_credentials,
)
from txline.models import TokenCredentials

logger = logging.getLogger(__name__)

PROGRAM_ID = Pubkey.from_string("9ExbZjAapQww1vfcisDmrngPinHTEfpjYRWMunJgcKaA")
TXL_MINT = Pubkey.from_string("sLX1i9dfmsuyFBmJTWuGjjRmG4VPWYK6dRRKSM4BCSx")
SOLANA_RPC = "https://api.mainnet-beta.solana.com"

# Free-tier service levels:  1 = 60-second delay,  12 = real-time
SERVICE_LEVEL_FREE_DELAYED = 1
SERVICE_LEVEL_FREE_REALTIME = 12
MIN_DURATION_WEEKS = 4

# Empty list = use the bundled league package for the chosen service level
FREE_TIER_LEAGUES: list[int] = []


async def subscribe_free_tier(
    keypair: Keypair,
    service_level: int = SERVICE_LEVEL_FREE_REALTIME,
    duration_weeks: int = MIN_DURATION_WEEKS,
    rpc_url: str = SOLANA_RPC,
    save_path: Path = Path(".txline-credentials.json"),
) -> TokenCredentials:
    """
    Full subscription + activation flow for the free tier.

    1. Get guest JWT.
    2. Build and send the on-chain subscribe transaction.
    3. Sign the activation message with the wallet key.
    4. Exchange for a long-lived API token.
    5. Persist credentials to disk.
    """
    async with httpx.AsyncClient() as http_client:
        logger.info("Fetching guest JWT…")
        jwt = await get_guest_jwt(http_client)

        logger.info(
            "Submitting on-chain subscription (level=%d, weeks=%d)…",
            service_level,
            duration_weeks,
        )
        tx_sig = await _submit_subscription(keypair, service_level, duration_weeks, rpc_url)
        logger.info("On-chain tx confirmed: %s", tx_sig)

        message = build_activation_message(tx_sig, FREE_TIER_LEAGUES, jwt)
        wallet_sig_b64 = sign_message(bytes(keypair.secret()), message)

        logger.info("Activating API token…")
        api_token = await activate_token(
            http_client, jwt, tx_sig, wallet_sig_b64, FREE_TIER_LEAGUES
        )

    creds = TokenCredentials(jwt=jwt, api_token=api_token)
    save_credentials(creds, save_path)
    return creds


async def _fetch_idl(program_id: Pubkey, rpc_url: str) -> dict:
    """
    Fetch the Anchor IDL stored on-chain at the canonical IDL account
    (PDA seeded with b'anchor:idl' + program_id bytes).
    Falls back to a local cache at txline/idl/txline.json if available.
    """
    cache = Path(__file__).parent / "idl" / "txline.json"
    if cache.exists():
        logger.debug("Loading IDL from local cache %s", cache)
        return json.loads(cache.read_text())

    from anchorpy.idl import _fetch_idl as anchorpy_fetch_idl
    from solana.rpc.async_api import AsyncClient

    async with AsyncClient(rpc_url) as conn:
        idl = await anchorpy_fetch_idl(program_id, conn)

    if idl is None:
        raise RuntimeError(
            "Could not fetch IDL from chain and no local cache found at txline/idl/txline.json. "
            "Download the IDL from the TxLINE docs and place it there."
        )

    # Cache for future runs
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(json.dumps(idl, indent=2))
    logger.info("IDL cached at %s", cache)
    return idl


async def _submit_subscription(
    keypair: Keypair,
    service_level: int,
    duration_weeks: int,
    rpc_url: str,
) -> str:
    """Build and send the subscribe transaction; return the confirmed tx signature."""
    from anchorpy import Program, Provider, Wallet, Context, Idl
    from anchorpy.provider import DEFAULT_OPTIONS
    from solana.rpc.async_api import AsyncClient

    idl_raw = await _fetch_idl(PROGRAM_ID, rpc_url)
    idl = Idl.from_json(json.dumps(idl_raw))

    connection = AsyncClient(rpc_url)
    provider = Provider(connection, Wallet(keypair), DEFAULT_OPTIONS)
    program = Program(idl, PROGRAM_ID, provider)

    # Derive the subscriber's associated token account for TxL
    # (required by the program even though the free tier transfers 0 tokens)
    try:
        from spl.token.instructions import get_associated_token_address
        subscriber_ata = get_associated_token_address(keypair.pubkey(), TXL_MINT)
    except ImportError:
        # spl-token may not be installed; derive PDA manually
        subscriber_ata = _derive_ata(keypair.pubkey(), TXL_MINT)

    tx_sig = await program.rpc["subscribe"](
        service_level,
        duration_weeks,
        ctx=Context(
            accounts={
                "subscriber": keypair.pubkey(),
                "subscriberTokenAccount": subscriber_ata,
                "tokenMint": TXL_MINT,
            }
        ),
    )

    await connection.close()
    return str(tx_sig)


def _derive_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    """Derive Associated Token Account PDA without the spl library."""
    from solders.pubkey import Pubkey as Pk
    TOKEN_PROGRAM_ID = Pk.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    ATA_PROGRAM_ID = Pk.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJe1bRS")
    seeds = [bytes(owner), bytes(TOKEN_PROGRAM_ID), bytes(mint)]
    return Pk.find_program_address(seeds, ATA_PROGRAM_ID)[0]
