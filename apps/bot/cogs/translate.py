import logging
import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("sachitone.bot.cogs.translate")

POPULAR_LANGUAGES = [
    ("English", "en"),
    ("Vietnamese", "vi"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Chinese", "zh"),
    ("French", "fr"),
    ("German", "de"),
    ("Spanish", "es"),
    ("Russian", "ru"),
    ("Thai", "th"),
    ("Indonesian", "id"),
]


class TranslateCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Translate to English",
            callback=self.translate_message_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def target_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current_lower = current.strip().lower()
        choices = [
            app_commands.Choice(name=f"{name} ({code})", value=code)
            for name, code in POPULAR_LANGUAGES
            if current_lower in name.lower() or current_lower in code.lower()
        ]
        return choices[:25]

    @app_commands.command(name="translate", description="Translate text into another language")
    @app_commands.describe(
        text="The message or text to translate",
        target="Target language code (e.g. en, vi, ja, ko, fr, es, de, zh, ru, th, id)",
        source="Source language code (default: auto)",
    )
    @app_commands.autocomplete(target=target_autocomplete)
    async def translate(
        self,
        interaction: discord.Interaction,
        text: str,
        target: str,
        source: str = "auto",
    ) -> None:
        await interaction.response.defer()

        success, chunks = await self.bot.translator_service.translate_text(
            text=text,
            target_lang=target,
            source_lang=source,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
        )

        for chunk in chunks:
            await interaction.followup.send(chunk)

    async def translate_message_context_menu(
        self,
        interaction: discord.Interaction,
        message: discord.Message,
    ) -> None:
        content = message.clean_content.strip()
        if not content:
            await interaction.response.send_message(
                "Selected message does not contain readable text to translate.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        success, chunks = await self.bot.translator_service.translate_text(
            text=content,
            target_lang="en",
            source_lang="auto",
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
        )

        for chunk in chunks:
            await interaction.followup.send(chunk)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TranslateCog(bot))