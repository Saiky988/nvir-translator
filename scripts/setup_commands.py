import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import discord
from apps.bot.client import SachitoneBot
from config.settings import settings, setup_logging
from packages.translation.translator import get_default_translator


async def verify_environment() -> bool:
    setup_logging()
    print("=" * 60)
    print(" Sachitone Translator - Configuration & Health Check")
    print("=" * 60)
    all_ok = True

    if not settings.discord_token:
        print("[!] DISCORD_TOKEN is empty. Discord bot process will not connect.")
        all_ok = False
    else:
        print("[✓] DISCORD_TOKEN is set.")

    if not settings.gemini_api_key:
        print("[!] GEMINI_API_KEY is empty. Translations will fail.")
        all_ok = False
    else:
        print(f"[✓] GEMINI_API_KEY is set. (Model: {settings.gemini_model})")

    if all_ok and settings.gemini_api_key:
        print("\nTesting Gemini contextual translation...")
        try:
            translator = get_default_translator()
            result = await translator.translate(
                text="hnay mik hok biet lam j",
                source_language="vi",
                target_language="en",
            )
            print("[✓] Translation test passed!")
            print(f"    Input:    hnay mik hok biet lam j")
            print(f"    Output:   {result.translation}")
            print(f"    Provider: {result.provider} ({result.model})")
        except Exception as exc:
            print(f"[!] Test translation failed: {exc}")
            all_ok = False

    return all_ok


async def sync_guild_commands(guild_id: int) -> None:
    setup_logging()
    print(f"\nAttempting to sync slash commands directly to Guild ID: {guild_id}...")
    if not settings.discord_token:
        print("[!] DISCORD_TOKEN is missing. Cannot sync commands.")
        return

    bot = SachitoneBot()

    @bot.event
    async def on_ready():
        guild = discord.Object(id=guild_id)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"[✓] Successfully synced {len(synced)} commands to guild {guild_id}!")
        await bot.close()

    try:
        await bot.start(settings.discord_token)
    except Exception as exc:
        print(f"[!] Failed to sync guild commands: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sachitone setup and verification script")
    parser.add_argument("--guild", type=int, help="Optional guild ID to instantly sync slash commands")
    args = parser.parse_args()

    success = asyncio.run(verify_environment())
    if args.guild:
        asyncio.run(sync_guild_commands(args.guild))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()