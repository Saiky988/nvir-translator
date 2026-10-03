import discord
from discord import app_commands
from discord.ext import commands
from config.settings import settings


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="settings", description="Display current bot settings")
    async def settings_command(self, interaction: discord.Interaction) -> None:
        message = (
            f"**Sachitone Translator Configuration**\n"
            f"• **AI Model:** `{settings.gemini_model}`\n"
            f"• **Default Source:** `auto`\n"
            f"• **Max Input Length:** `{settings.max_translation_length}` characters\n"
            f"• **Timeout:** `{settings.translation_timeout}s`\n"
            f"• **Rate Limit:** 1 request / 2 seconds per user\n\n"
            f"*Settings are managed centrally via environment configuration in v1.0.*"
        )
        await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SettingsCog(bot))