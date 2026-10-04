import discord
from discord import app_commands
from discord.ext import commands
from config.settings import settings


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping_command(self, interaction: discord.Interaction) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! Latency: {latency_ms}ms")

    @app_commands.command(name="about", description="Information about Nvirya Translator")
    async def about_command(self, interaction: discord.Interaction) -> None:
        about_text = (
            "**Nvirya Translator**\n"
            "AI-powered Discord contextual translator\n"
            f"Version: `{settings.running_version}`\n"
            f"GitHub: https://github.com/{settings.github_repo}"
        )
        await interaction.response.send_message(about_text)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))