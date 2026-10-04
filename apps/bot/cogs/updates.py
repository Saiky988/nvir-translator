import logging
import discord
from discord import app_commands
from discord.ext import commands

from config.version import GITHUB_RELEASES_URL, GITHUB_REPO, VERSION

logger = logging.getLogger("sachitone.bot.cogs.updates")


def is_admin_or_owner(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    if interaction.client.owner_id and interaction.user.id == interaction.client.owner_id:
        return True
    return False


class UpdatesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    updates = app_commands.Group(
        name="updates",
        description="Software update management and notifications",
        default_permissions=discord.Permissions(administrator=True),
    )

    @updates.command(name="check", description="Check GitHub immediately for new releases")
    async def check_updates(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        checker = getattr(self.bot, "update_service", None)
        if not checker:
            await interaction.followup.send("Update checker service is not initialized.", ephemeral=True)
            return

        success, msg, release_dict, has_update = await checker.check_and_notify(manual=True)

        if not success or not release_dict:
            await interaction.followup.send(f"**Update Check Failed:** {msg}", ephemeral=True)
            return

        config = await self.bot.storage.get_update_config()
        embed = checker.build_update_embed(
            release_dict=release_dict,
            running_version=config["running_version"],
            is_test=False,
        )

        if not has_update:
            embed.color = 0x5865F2  # Blurple
            embed.title = f"You are up to date! (`v{config['running_version']}`)"
            embed.description = f"Current running version `v{config['running_version']}` matches the latest applicable release on GitHub."

        await interaction.followup.send(embed=embed, ephemeral=True)

    @updates.command(name="version", description="Show running version and latest known release")
    async def show_version(self, interaction: discord.Interaction) -> None:
        config = await self.bot.storage.get_update_config()
        latest_tag = config.get("latest_release_tag") or "Not checked yet"

        embed = discord.Embed(
            title="Nvirya Translator Version",
            color=0x5865F2,
            description=(
                f"• **Running Version:** `v{config['running_version']}`\n"
                f"• **Latest Discovered:** `{latest_tag}`\n"
                f"• **Repository:** [{GITHUB_REPO}](https://github.com/{GITHUB_REPO})\n"
                f"• **Releases:** [GitHub Releases]({GITHUB_RELEASES_URL})"
            ),
        )
        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @updates.command(name="status", description="Display update checker status and notification destinations")
    async def show_status(self, interaction: discord.Interaction) -> None:
        config = await self.bot.storage.get_update_config()

        status_icon = "Active" if config["enabled"] else "Disabled"
        channel_str = f"<#{config['notification_channel_id']}>" if config.get("notification_channel_id") else "*None configured*"
        prerelease_str = "Yes (Include Beta/RC)" if config["include_prereleases"] else "No (Stable only)"
        owner_dm_str = "Enabled" if config["notify_owner"] else "Disabled"

        last_check = config.get("last_check_timestamp") or "Never"
        last_status = config.get("last_check_status") or "pending"
        error_info = f"\n• **Last Error:** `{config['last_check_error']}`" if config.get("last_check_error") else ""

        embed = discord.Embed(
            title="Update Management Status",
            color=0x5865F2,
            description=(
                f"• **Automatic Checks:** {status_icon}\n"
                f"• **Check Interval:** Every `{config['check_interval_hours']}` hours\n"
                f"• **Prerelease Tracking:** {prerelease_str}\n"
                f"• **Announcement Channel:** {channel_str}\n"
                f"• **Bot Owner DM:** {owner_dm_str}\n"
                f"• **Last Check:** `{last_check}` (Status: `{last_status}`){error_info}\n"
                f"• **Last Notified Release:** `{config.get('last_notified_tag') or 'None'}`"
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @updates.command(name="set-channel", description="Set a Discord channel to receive update announcements")
    @app_commands.describe(channel="Text channel for announcements")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("Administrator permission required.", ephemeral=True)
            return

        perms = channel.permissions_for(channel.guild.me)
        missing = []
        if not perms.view_channel:
            missing.append("View Channel")
        if not perms.send_messages:
            missing.append("Send Messages")
        if not perms.embed_links:
            missing.append("Embed Links")

        if missing:
            await interaction.response.send_message(
                f"Bot lacks required permissions in {channel.mention}: **{', '.join(missing)}**.",
                ephemeral=True,
            )
            return

        await self.bot.storage.update_update_settings(notification_channel_id=channel.id)
        await interaction.response.send_message(
            f"Update announcements will now be sent to {channel.mention}.",
            ephemeral=True,
        )

    @updates.command(name="remove-channel", description="Unset the announcement channel")
    async def remove_channel(self, interaction: discord.Interaction) -> None:
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("⚠️ Administrator permission required.", ephemeral=True)
            return

        await self.bot.storage.update_update_settings(notification_channel_id=None)
        await interaction.response.send_message(
            "Notification channel removed. Update announcements will no longer be broadcast to a guild channel.",
            ephemeral=True,
        )

    @updates.command(name="enable", description="Enable automatic background update checks")
    async def enable_checks(self, interaction: discord.Interaction) -> None:
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("Administrator permission required.", ephemeral=True)
            return

        await self.bot.storage.update_update_settings(enabled=True)
        await interaction.response.send_message(
            "Automatic update checks have been **enabled**.",
            ephemeral=True,
        )

    @updates.command(name="disable", description="Disable automatic background update checks")
    async def disable_checks(self, interaction: discord.Interaction) -> None:
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("Administrator permission required.", ephemeral=True)
            return

        await self.bot.storage.update_update_settings(enabled=False)
        await interaction.response.send_message(
            "Automatic update checks have been **disabled**.",
            ephemeral=True,
        )

    @updates.command(name="interval", description="Set background check interval in hours")
    @app_commands.describe(hours="Check frequency in hours (1 to 168)")
    async def set_interval(self, interaction: discord.Interaction, hours: app_commands.Range[int, 1, 168]) -> None:
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("Administrator permission required.", ephemeral=True)
            return

        await self.bot.storage.update_update_settings(check_interval_hours=hours)
        await interaction.response.send_message(
            f"Update check interval set to every **{hours} hour(s)**.",
            ephemeral=True,
        )

    @updates.command(name="prereleases", description="Configure whether to track prereleases (Beta, Alpha, RC)")
    @app_commands.describe(include="True to track prereleases, False for stable releases only")
    async def set_prereleases(self, interaction: discord.Interaction, include: bool) -> None:
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("Administrator permission required.", ephemeral=True)
            return

        await self.bot.storage.update_update_settings(include_prereleases=include)
        state_str = "**included** (Beta/RC releases will be announced)" if include else "**excluded** (Stable releases only)"
        await interaction.response.send_message(
            f"Prerelease releases are now {state_str}.",
            ephemeral=True,
        )

    @updates.command(name="test-notification", description="Send a test notification to verify delivery")
    async def test_notification(self, interaction: discord.Interaction) -> None:
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("Administrator permission required.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        checker = getattr(self.bot, "update_service", None)
        if not checker:
            await interaction.followup.send("Update checker service is unavailable.", ephemeral=True)
            return

        test_release = {
            "tag_name": f"v{VERSION}-test",
            "name": f"Release v{VERSION} (Test Broadcast)",
            "html_url": GITHUB_RELEASES_URL,
            "published_at": None,
            "body": "### Test Release Notes\n- Verified delivery to configured notification channels\n- Verified owner direct messaging delivery\n- Mentions are disabled.",
        }

        results = await checker.notify_destinations(test_release, is_test=True)

        report_lines = ["**Update Notification Test Report:**"]
        if "owner_dm" in results:
            report_lines.append(f"• **Owner DM:** {results['owner_dm']}")
        else:
            report_lines.append("• **Owner DM:** Disabled in configuration")

        if "channel" in results:
            report_lines.append(f"• **Channel Broadcast:** {results['channel']}")
        else:
            report_lines.append("• **Channel Broadcast:** *No channel configured (use `/updates set-channel`)*")

        await interaction.followup.send("\n".join(report_lines), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UpdatesCog(bot))