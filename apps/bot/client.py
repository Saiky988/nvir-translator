import asyncio
import logging
import discord
from discord.ext import commands
from apps.bot.services.translator import BotTranslatorService
from apps.bot.storage import AutoTranslateStorage
from config.settings import settings

logger = logging.getLogger("sachitone.bot.client")


class MessageLockManager:
    def __init__(self, max_locks: int = 1000):
        self._locks: dict[int, asyncio.Lock] = {}
        self._max_locks = max_locks

    def get_lock(self, message_id: int) -> asyncio.Lock:
        if message_id not in self._locks:
            if len(self._locks) > self._max_locks:
                for k in list(self._locks.keys())[:200]:
                    del self._locks[k]
            self._locks[message_id] = asyncio.Lock()
        return self._locks[message_id]


class SachitoneBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=settings.bot_prefix,
            intents=intents,
            help_command=None,
        )
        self.storage = AutoTranslateStorage(db_path=settings.database_path)
        self.translator_service = BotTranslatorService()
        self.semaphore = asyncio.Semaphore(settings.auto_translate_semaphore)
        self.lock_manager = MessageLockManager()

    async def setup_hook(self) -> None:
        await self.storage.connect()
        logger.info("Auto-translate persistence initialized at %s", settings.database_path)

        cogs = [
            "apps.bot.cogs.translate",
            "apps.bot.cogs.settings",
            "apps.bot.cogs.admin",
            "apps.bot.cogs.auto_translate",
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

    async def close(self) -> None:
        logger.info("Closing database connections and shutting down...")
        await self.storage.close()
        await super().close()