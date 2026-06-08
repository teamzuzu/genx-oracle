"""
CLI: txline-subscribe

Interactive wizard that walks through wallet setup and the free-tier
on-chain subscription to produce a .txline-credentials.json file.
"""

import asyncio
import os
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from solders.keypair import Keypair

console = Console()


def _load_keypair(secret_key_env: str | None, keypair_file: str | None) -> Keypair:
    if secret_key_env:
        raw = bytes.fromhex(secret_key_env) if len(secret_key_env) == 128 else None
        if raw is None:
            import base58  # type: ignore[import]
            raw = base58.b58decode(secret_key_env)
        return Keypair.from_bytes(raw)
    if keypair_file:
        import json
        data = json.loads(Path(keypair_file).read_text())
        return Keypair.from_bytes(bytes(data))
    raise click.UsageError(
        "Provide --keypair-file or set TXLINE_SECRET_KEY environment variable."
    )


@click.command()
@click.option("--keypair-file", envvar="SOLANA_KEYPAIR_FILE", help="Path to Solana keypair JSON file")
@click.option("--service-level", default=12, show_default=True, help="1=delayed, 12=realtime (both free)")
@click.option("--duration-weeks", default=4, show_default=True, help="Subscription duration (min 4)")
@click.option("--rpc-url", default="https://api.mainnet-beta.solana.com", show_default=True)
@click.option("--output", default=".txline-credentials.json", show_default=True, help="Where to save credentials")
def main(keypair_file, service_level, duration_weeks, rpc_url, output):
    """Subscribe to the TxLINE free tier and save API credentials."""
    console.print(Panel("[bold cyan]TxLINE Free Tier Setup[/bold cyan]", expand=False))

    secret_key_env = os.environ.get("TXLINE_SECRET_KEY")
    try:
        keypair = _load_keypair(secret_key_env, keypair_file)
    except Exception as exc:
        console.print(f"[red]Failed to load keypair: {exc}[/red]")
        raise SystemExit(1)

    console.print(f"Wallet: [green]{keypair.pubkey()}[/green]")
    console.print(f"Service level: [yellow]{service_level}[/yellow] ({'real-time' if service_level == 12 else '60s delay'})")
    console.print(f"Duration: [yellow]{duration_weeks} weeks[/yellow] (free)")

    from txline.subscription import subscribe_free_tier

    async def run():
        return await subscribe_free_tier(
            keypair,
            service_level=service_level,
            duration_weeks=duration_weeks,
            rpc_url=rpc_url,
            save_path=Path(output),
        )

    try:
        creds = asyncio.run(run())
        console.print(f"\n[bold green]Credentials saved to {output}[/bold green]")
        console.print(f"API token: [dim]{creds.api_token[:20]}…[/dim]")
    except Exception as exc:
        console.print(f"[red]Subscription failed: {exc}[/red]")
        raise SystemExit(1)
