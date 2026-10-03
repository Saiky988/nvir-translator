import hashlib
import logging
import re
from typing import Literal
import discord
from discord import app_commands
from discord.ext import commands
from config.settings import settings

logger = logging.getLogger("sachitone.bot.cogs.auto_translate")

POPULAR_LANGUAGES = [
    ("English", "en"),
    ("Vietnamese", "vi"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Chinese", "zh"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Russian", "ru"),
    ("Thai", "th"),
    ("Indonesian", "id"),
    ("Portuguese", "pt"),
    ("Italian", "it"),
]


def has_translatable_content(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    # Strip URLs
    no_urls = re.sub(r"https?://\S+", "", cleaned)
    # Strip Discord mentions (<@123>, <#123>, <@&123>)
    no_mentions = re.sub(r"<@&?!\d+>|<#\d+>", "", no_urls)
    # Strip custom emojis (<:name:123>)
    no_emojis = re.sub(r"<a?:\w+:\d+>", "", no_mentions)
    # Check if any letters or word characters remain
    return bool(re.search(r"[^\W\d_]", no_emojis, re.UNICODE))


class AutoTranslateCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    autotranslate = app_commands.Group(
        name="autotranslate",
        description="Configure automatic channel translation",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    async def lang_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current_lower = current.strip().lower()
        return [
            app_commands.Choice(name=f"{name} ({code})", value=code)
            for name, code in POPULAR_LANGUAGES
            if current_lower in name.lower() or current_lower in code.lower()
        ][:25]

    @autotranslate.command(name="setup", description="Enable auto-translation for a channel")
    @app_commands.describe(
        channel="The text channel to auto-translate",
        lang1="First target language (e.g. en, vi, es)",
        lang2="Optional second target language",
        lang3="Optional third target language",
        mode="Display format: text (compact message) or embed",
        sync_edits="Synchronize edits to original messages",
        sync_deletes="Delete translations when original message is deleted",
    )
    async def setup_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        lang1: str,
        lang2: str | None = None,
        lang3: str | None = None,
        mode: Literal["text", "embed"] = "text",
        sync_edits: bool = True,
        sync_deletes: bool = True,
    ) -> None:
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need the **Manage Server** permission to configure auto-translation.",
                ephemeral=True,
            )
            return

        perms = channel.permissions_for(interaction.guild.me)
        missing = []
        if not perms.view_channel:
            missing.append("View Channel")
        if not perms.send_messages:
            missing.append("Send Messages")
        if not perms.read_message_history:
            missing.append("Read Message History")
        if mode == "embed" and not perms.embed_links:
            missing.append("Embed Links")

        if missing:
            await interaction.response.send_message(
                f"Bot is missing permissions in {channel.mention}: **{', '.join(missing)}**.",
                ephemeral=True,
            )
            return

        raw_langs = [l.strip().lower() for l in [lang1, lang2, lang3] if l and l.strip()]
        unique_langs = list(dict.fromkeys(raw_langs))

        if len(unique_langs) < 1:
            await interaction.response.send_message("Please provide at least 1 target language.", ephemeral=True)
            return

        if len(raw_langs) != len(unique_langs):
            await interaction.response.send_message("Duplicate target languages are not allowed.", ephemeral=True)
            return

        await self.bot.storage.set_channel_config(
            guild_id=interaction.guild_id,
            channel_id=channel.id,
            target_languages=unique_langs,
            output_mode=mode,
            sync_edits=sync_edits,
            sync_deletes=sync_deletes,
            enabled=True,
        )

        lang_tags = " • ".join(f"`{l.upper()}`" for l in unique_langs)
        response_msg = (
            f"**Auto-translation configured for {channel.mention}!**\n"
            f"• **Target Languages:** {lang_tags}\n"
            f"• **Output Mode:** `{mode.upper()}`\n"
            f"• **Source Detection:** `auto` (source language is omitted from output)\n"
            f"• **Sync Edits:** `{'Yes' if sync_edits else 'No'}`\n"
            f"• **Sync Deletes:** `{'Yes' if sync_deletes else 'No'}`"
        )
        await interaction.response.send_message(response_msg, ephemeral=True)

    @setup_channel.autocomplete("lang1")
    @setup_channel.autocomplete("lang2")
    @setup_channel.autocomplete("lang3")
    async def setup_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.lang_autocomplete(interaction, current)

    @autotranslate.command(name="disable", description="Disable auto-translation for a channel")
    @app_commands.describe(channel="The channel to disable auto-translation for")
    async def disable_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need the **Manage Server** permission to disable auto-translation.",
                ephemeral=True,
            )
            return

        config = await self.bot.storage.get_channel_config(channel.id)
        if not config or not config["enabled"]:
            await interaction.response.send_message(
                f"Auto-translation is not active in {channel.mention}.", ephemeral=True
            )
            return

        await self.bot.storage.disable_channel(channel.id)
        await interaction.response.send_message(
            f"Auto-translation has been **disabled** for {channel.mention}. Existing message mappings are preserved for deletion cleanup.",
            ephemeral=True,
        )

    @autotranslate.command(name="config", description="Show current auto-translation settings")
    @app_commands.describe(channel="Optional channel to inspect (defaults to current)")
    async def config_command(
        self, interaction: discord.Interaction, channel: discord.TextChannel | None = None
    ) -> None:
        target_channel = channel or interaction.channel
        config = await self.bot.storage.get_channel_config(target_channel.id)

        if not config:
            await interaction.response.send_message(
                f"{target_channel.mention} is not configured for automatic translation.",
                ephemeral=True,
            )
            return

        lang_tags = " • ".join(f"`{l.upper()}`" for l in config["target_languages"])
        status_text = "🟢 **Enabled**" if config["enabled"] else "🔴 **Disabled**"

        msg = (
            f"**Auto-Translate Configuration for {target_channel.mention}**\n"
            f"• **Status:** {status_text}\n"
            f"• **Target Languages:** {lang_tags}\n"
            f"• **Output Mode:** `{config['output_mode'].upper()}`\n"
            f"• **Sync Edits:** `{'Enabled' if config['sync_edits'] else 'Disabled'}`\n"
            f"• **Sync Deletions:** `{'Enabled' if config['sync_deletes'] else 'Disabled'}`"
        )
        await interaction.response.send_message(msg, ephemeral=True)

    @autotranslate.command(name="languages", description="Update target languages for an auto-translate channel")
    @app_commands.describe(
        channel="Channel to update",
        lang1="First target language",
        lang2="Optional second target language",
        lang3="Optional third target language",
    )
    async def set_languages(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        lang1: str,
        lang2: str | None = None,
        lang3: str | None = None,
    ) -> None:
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Insufficient permissions.", ephemeral=True)
            return

        config = await self.bot.storage.get_channel_config(channel.id)
        if not config:
            await interaction.response.send_message(
                f"{channel.mention} is not configured yet. Run `/autotranslate setup` first.",
                ephemeral=True,
            )
            return

        raw_langs = [l.strip().lower() for l in [lang1, lang2, lang3] if l and l.strip()]
        unique_langs = list(dict.fromkeys(raw_langs))

        if len(unique_langs) < 1:
            await interaction.response.send_message("Please select at least 1 language.", ephemeral=True)
            return

        if len(raw_langs) != len(unique_langs):
            await interaction.response.send_message("Duplicate languages are not allowed.", ephemeral=True)
            return

        await self.bot.storage.update_channel_languages(channel.id, unique_langs)
        lang_tags = " • ".join(f"`{l.upper()}`" for l in unique_langs)
        await interaction.response.send_message(
            f"Updated target languages for {channel.mention}: {lang_tags}", ephemeral=True
        )

    @set_languages.autocomplete("lang1")
    @set_languages.autocomplete("lang2")
    @set_languages.autocomplete("lang3")
    async def languages_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.lang_autocomplete(interaction, current)

    @autotranslate.command(name="mode", description="Switch output mode between text and embed")
    @app_commands.describe(channel="Channel to update", mode="Display mode: text or embed")
    async def set_mode(
        self, interaction: discord.Interaction, channel: discord.TextChannel, mode: Literal["text", "embed"]
    ) -> None:
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Insufficient permissions.", ephemeral=True)
            return

        config = await self.bot.storage.get_channel_config(channel.id)
        if not config:
            await interaction.response.send_message(
                f"{channel.mention} is not configured yet. Run `/autotranslate setup` first.",
                ephemeral=True,
            )
            return

        if mode == "embed":
            perms = channel.permissions_for(interaction.guild.me)
            if not perms.embed_links:
                await interaction.response.send_message(
                    f"Bot lacks **Embed Links** permission in {channel.mention}.", ephemeral=True
                )
                return

        await self.bot.storage.update_channel_mode(channel.id, mode)
        await interaction.response.send_message(
            f"Output mode for {channel.mention} changed to `{mode.upper()}`.", ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.webhook_id is not None or not message.guild:
            return

        if not self.bot.storage.is_channel_enabled(message.channel.id):
            return

        if self.bot.storage.is_translated_message(message.id):
            return

        content = message.content.strip()
        if not has_translatable_content(content):
            return

        if len(content) > settings.max_translation_length:
            return

        config = await self.bot.storage.get_channel_config(message.channel.id)
        if not config or not config["enabled"]:
            return

        async with self.bot.lock_manager.get_lock(message.id):
            async with self.bot.semaphore:
                success, detected_source, translations, error = (
                    await self.bot.translator_service.translate_multiple_text(
                        text=content,
                        target_langs=config["target_languages"],
                        source_lang="auto",
                        user_id=message.author.id,
                        guild_id=message.guild.id,
                    )
                )

            if not success or not translations:
                return

            try:
                translated_msg = await self._send_output(
                    message=message,
                    translations=translations,
                    mode=config["output_mode"],
                )
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                await self.bot.storage.record_translation_message(
                    source_message_id=message.id,
                    source_channel_id=message.channel.id,
                    guild_id=message.guild.id,
                    source_author_id=message.author.id,
                    translated_message_ids=[translated_msg.id],
                    detected_source_language=detected_source,
                    source_content_hash=content_hash,
                )
            except (discord.Forbidden, discord.HTTPException) as exc:
                logger.warning("Failed to send auto-translate output in channel %s: %s", message.channel.id, exc)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.author.bot or after.webhook_id is not None or not after.guild:
            return

        if not self.bot.storage.is_channel_enabled(after.channel.id):
            return

        if before.content == after.content:
            return

        config = await self.bot.storage.get_channel_config(after.channel.id)
        if not config or not config["enabled"] or not config["sync_edits"]:
            return

        async with self.bot.lock_manager.get_lock(after.id):
            mapping = await self.bot.storage.get_translation_message(after.id)
            if not mapping:
                return

            new_content = after.content.strip()

            trans_id = mapping["translated_message_ids"][0] if mapping["translated_message_ids"] else None
            trans_msg = None
            if trans_id:
                try:
                    trans_msg = await after.channel.fetch_message(trans_id)
                except (discord.NotFound, discord.Forbidden):
                    trans_msg = None

            if not has_translatable_content(new_content):
                if trans_msg:
                    try:
                        await trans_msg.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass
                await self.bot.storage.delete_translation_message(after.id)
                return

            new_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
            if mapping.get("source_content_hash") == new_hash:
                return

            async with self.bot.semaphore:
                success, detected_source, translations, _ = (
                    await self.bot.translator_service.translate_multiple_text(
                        text=new_content,
                        target_langs=config["target_languages"],
                        source_lang="auto",
                        user_id=after.author.id,
                        guild_id=after.guild.id,
                    )
                )

            if not success or not translations:
                if trans_msg:
                    try:
                        await trans_msg.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass
                await self.bot.storage.delete_translation_message(after.id)
                return

            try:
                if trans_msg:
                    await self._edit_output(
                        trans_msg=trans_msg,
                        author=after.author,
                        translations=translations,
                        mode=config["output_mode"],
                        jump_url=after.jump_url,
                    )
                    await self.bot.storage.record_translation_message(
                        source_message_id=after.id,
                        source_channel_id=after.channel.id,
                        guild_id=after.guild.id,
                        source_author_id=after.author.id,
                        translated_message_ids=[trans_msg.id],
                        detected_source_language=detected_source,
                        source_content_hash=new_hash,
                    )
                else:
                    new_msg = await self._send_output(
                        message=after,
                        translations=translations,
                        mode=config["output_mode"],
                    )
                    await self.bot.storage.record_translation_message(
                        source_message_id=after.id,
                        source_channel_id=after.channel.id,
                        guild_id=after.guild.id,
                        source_author_id=after.author.id,
                        translated_message_ids=[new_msg.id],
                        detected_source_language=detected_source,
                        source_content_hash=new_hash,
                    )
            except Exception as exc:
                logger.error("Failed to synchronize message edit: %s", exc)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if not message.guild:
            return

        mapping = await self.bot.storage.get_translation_message(message.id)
        if not mapping:
            return

        config = await self.bot.storage.get_channel_config(message.channel.id)
        if config and not config["sync_deletes"]:
            return

        for mid in mapping["translated_message_ids"]:
            try:
                trans_msg = await message.channel.fetch_message(mid)
                await trans_msg.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        await self.bot.storage.delete_translation_message(message.id)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent) -> None:
        deleted_mappings = await self.bot.storage.get_and_delete_batch_translations(list(payload.message_ids))
        if not deleted_mappings:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except Exception:
                return

        for mapping in deleted_mappings:
            for mid in mapping.get("translated_message_ids", []):
                try:
                    m = await channel.fetch_message(mid)
                    await m.delete()
                except Exception:
                    pass

    async def _send_output(
        self,
        message: discord.Message,
        translations: dict[str, str],
        mode: str,
    ) -> discord.Message:
        if mode == "embed":
            embed = self._build_embed(message.author, translations, message.jump_url)
            return await message.reply(
                embed=embed,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )

        text_content = self._build_text(translations)
        return await message.reply(
            content=text_content,
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def _edit_output(
        self,
        trans_msg: discord.Message,
        author: discord.User | discord.Member,
        translations: dict[str, str],
        mode: str,
        jump_url: str,
    ) -> None:
        if mode == "embed":
            embed = self._build_embed(author, translations, jump_url)
            await trans_msg.edit(
                embed=embed,
                content=None,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            text_content = self._build_text(translations)
            await trans_msg.edit(
                content=text_content,
                embed=None,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    def _build_text(self, translations: dict[str, str]) -> str:
        return "\n".join(f"`{lang.upper()}`: {trans}" for lang, trans in translations.items())

    def _build_embed(
        self,
        author: discord.User | discord.Member,
        translations: dict[str, str],
        jump_url: str,
    ) -> discord.Embed:
        content = "\n".join(f"`{lang.upper()}`: {trans}" for lang, trans in translations.items())
        embed = discord.Embed(
            description=content[:4096],
            color=settings.embed_color,
        )
        embed.set_author(
            name=author.display_name,
            icon_url=author.display_avatar.url,
            url=jump_url,
        )
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoTranslateCog(bot))
