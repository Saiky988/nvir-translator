import logging
import discord
from discord.ext import commands
from apps.bot.services.translator import BotTranslatorService
from config.settings import settings

logger = logging.getLogger("sachitone.bot.client")


class SachitoneBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=settings.bot_prefix,
            intents=intents,
            help_command=None,
        )
        self.translator_service = BotTranslatorService()

    async def setup_hook(self) -> None:
        cogs = [
            "apps.bot.cogs.translate",
            "apps.bot.cogs.settings",
            "apps.bot.cogs.admin",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info("Loaded cog: %s", cog)
            except Exception as exc:
                logger.error("Failed to load cog %s: %s", cog, exc)

        logger.info("Synchronizing application command tree...")
        try:
            synced = await self.tree.sync()
            logger.info("Successfully synced %d application commands", len(synced))
        except Exception as exc:
            logger.error("Failed to sync commands: %s", exc)

    async def on_ready(self) -> None:
        logger.info(
            "Bot connected as %s (ID: %s) across %d guilds",
            self.user,
            self.user.id if self.user else "Unknown",
            len(self.guilds),
        )