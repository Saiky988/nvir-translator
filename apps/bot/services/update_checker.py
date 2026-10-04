import asyncio
import json
import logging
import random
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

import discord

from apps.bot.storage import AutoTranslateStorage
from config.settings import settings
from config.version import GITHUB_API_RELEASES_URL, GITHUB_RELEASES_URL, GITHUB_REPO, VERSION

logger = logging.getLogger("sachitone.bot.updates")


def parse_semver(version_str: str) -> tuple[int, int, int, tuple, bool]:
    if not version_str:
        return (0, 0, 0, (("zzz",),), False)

    clean = version_str.strip().lstrip("vV")
    pattern = r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[.-]?([a-zA-Z0-9.-]+))?$"
    m = re.match(pattern, clean)
    if not m:
        digits = [int(x) for x in re.findall(r"\d+", clean)]
        major = digits[0] if len(digits) > 0 else 0
        minor = digits[1] if len(digits) > 1 else 0
        patch = digits[2] if len(digits) > 2 else 0
        return (major, minor, patch, (("zzz",),), False)

    major = int(m.group(1))
    minor = int(m.group(2)) if m.group(2) is not None else 0
    patch = int(m.group(3)) if m.group(3) is not None else 0
    prerelease_str = m.group(4)

    if prerelease_str:
        parts = []
        for part in re.split(r"[.-]", prerelease_str):
            if part.isdigit():
                parts.append((0, int(part)))
            else:
                p_lower = part.lower()
                weight = 1
                if "alpha" in p_lower:
                    weight = 1
                elif "beta" in p_lower:
                    weight = 2
                elif "rc" in p_lower:
                    weight = 3
                parts.append((weight, p_lower))
        return (major, minor, patch, tuple(parts), True)
    return (major, minor, patch, (("zzz",),), False)


def compare_versions(v1: str, v2: str) -> int:
    p1 = parse_semver(v1)
    p2 = parse_semver(v2)

    if p1[:3] > p2[:3]:
        return 1
    if p1[:3] < p2[:3]:
        return -1

    if not p1[4] and p2[4]:
        return 1
    if p1[4] and not p2[4]:
        return -1
    if not p1[4] and not p2[4]:
        return 0

    if p1[3] > p2[3]:
        return 1
    if p1[3] < p2[3]:
        return -1
    return 0


def is_newer_version(latest_tag: str, current_tag: str) -> bool:
    return compare_versions(latest_tag, current_tag) > 0


def sanitize_changelog(body: str, max_chars: int = 1000) -> str:
    if not body or not body.strip():
        return "*No changelog provided for this release.*"

    cleaned = body.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    cleaned = re.sub(r"<@&?(\d+)>", r"@user_\1", cleaned).strip()

    if len(cleaned) <= max_chars:
        return cleaned

    truncated = cleaned[:max_chars]
    last_newline = truncated.rfind("\n")
    if last_newline > max_chars * 0.7:
        truncated = truncated[:last_newline]
    return truncated.rstrip() + "\n\n*(Changelog truncated. Click release link below to read full notes)*"


class UpdateCheckerService:
    def __init__(self, bot: discord.Client, storage: AutoTranslateStorage):
        self.bot = bot
        self.storage = storage
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop(), name="UpdateChecker-Loop")
            logger.info("UpdateCheckerService background worker started")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("UpdateCheckerService background worker stopped cleanly")

    async def _run_loop(self) -> None:
        await self.bot.wait_until_ready()

        jitter = random.uniform(5.0, 30.0)
        logger.info("Initial update check scheduled in %.1f seconds", jitter)
        await asyncio.sleep(jitter)

        while not self.bot.is_closed():
            try:
                config = await self.storage.get_update_config()
                if config["enabled"]:
                    await self.check_and_notify(manual=False)
            except Exception as exc:
                logger.error("Unhandled error in scheduled update check: %s", exc)

            config = await self.storage.get_update_config()
            interval_hours = max(1, config["check_interval_hours"])
            try:
                await asyncio.sleep(interval_hours * 3600)
            except asyncio.CancelledError:
                break

    async def fetch_latest_release(self, include_prereleases: bool = False) -> tuple[bool, dict[str, Any] | None, str | None]:
        url = f"{GITHUB_API_RELEASES_URL}?per_page=10"
        headers = {
            "User-Agent": f"Nvirya-Translator/{VERSION} (Discord Bot)",
            "Accept": "application/vnd.github.v3+json",
        }

        retries = 2
        backoff = 2.0

        for attempt in range(retries + 1):
            try:
                def _fetch():
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        status = resp.status
                        body = resp.read().decode("utf-8")
                        resp_headers = dict(resp.headers)
                        return status, body, resp_headers

                status, body_text, resp_headers = await asyncio.to_thread(_fetch)

                if status == 200:
                    releases = json.loads(body_text)
                    if not isinstance(releases, list) or not releases:
                        return False, None, "No releases found in GitHub repository."

                    for rel in releases:
                        if rel.get("draft"):
                            continue
                        if not include_prereleases and rel.get("prerelease"):
                            continue
                        return True, rel, None

                    return False, None, "No matching release found for the current configuration."

            except urllib.error.HTTPError as exc:
                headers_dict = dict(exc.headers)
                rate_remaining = headers_dict.get("X-RateLimit-Remaining")
                rate_reset = headers_dict.get("X-RateLimit-Reset")

                if exc.code in (403, 429) and rate_remaining == "0":
                    reset_time_str = ""
                    if rate_reset and rate_reset.isdigit():
                        reset_dt = datetime.fromtimestamp(int(rate_reset))
                        reset_time_str = f" Resets at {reset_dt.strftime('%H:%M:%S UTC')}."
                    return False, None, f"GitHub API rate limit exceeded.{reset_time_str}"

                if exc.code == 404:
                    return False, None, f"Repository '{GITHUB_REPO}' was not found on GitHub."

                if exc.code >= 500 and attempt < retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue

                return False, None, f"GitHub API returned HTTP {exc.code}."

            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                return False, None, "Connection to GitHub API timed out."

            except Exception as exc:
                return False, None, f"Unexpected error checking releases: {type(exc).__name__}"

        return False, None, "Failed to connect to GitHub API after multiple attempts."

    def build_update_embed(
        self, release_dict: dict[str, Any], running_version: str, is_test: bool = False
    ) -> discord.Embed:
        tag = release_dict.get("tag_name", "Unknown")
        title = release_dict.get("name") or tag
        url = release_dict.get("html_url") or GITHUB_RELEASES_URL
        published_raw = release_dict.get("published_at")
        body = release_dict.get("body") or ""

        published_str = "Recently"
        if published_raw:
            try:
                dt = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                published_str = f"<t:{int(dt.timestamp())}:D> (<t:{int(dt.timestamp())}:R>)"
            except Exception:
                published_str = published_raw[:10]

        color = 0xFEE75C if is_test else 0x57F287  # Yellow for test, Green for release
        embed_title = f"[TEST] Update Notification System" if is_test else f"New Release Available: {title}"

        embed = discord.Embed(
            title=embed_title,
            url=url,
            color=color,
            description="A new update is available for **Nvirya Translator**." if not is_test else (
                "This is a test notification verifying that update announcements deliver correctly."
            ),
        )

        avatar_url = self.bot.user.display_avatar.url if self.bot.user else None
        embed.set_author(name="Nvirya Translator • Update System", icon_url=avatar_url)

        embed.add_field(name="Running Version", value=f"`v{running_version}`", inline=True)
        embed.add_field(name="Latest Version", value=f"`{tag}`", inline=True)
        embed.add_field(name="Published", value=published_str, inline=True)

        changelog_snippet = sanitize_changelog(body, max_chars=800)
        embed.add_field(name="Release Notes", value=changelog_snippet, inline=False)

        embed.add_field(
            name="How to Update",
            value=(
                "• **Docker:** `docker compose pull && docker compose up -d`\n"
                "• **Git / Shared:** `git pull && pip install -r requirements.txt`"
            ),
            inline=False,
        )

        embed.add_field(
            name="Quick Links",
            value=f"[View Release Notes on GitHub]({url}) • [Source Repository](https://github.com/{GITHUB_REPO})",
            inline=False,
        )

        embed.set_footer(text="Self-hosted notification • Updates are never applied automatically.")
        return embed

    async def notify_destinations(
        self, release_dict: dict[str, Any], is_test: bool = False
    ) -> dict[str, str]:
        config = await self.storage.get_update_config()
        tag = release_dict.get("tag_name", "v1.0.0")
        embed = self.build_update_embed(release_dict, config["running_version"], is_test=is_test)

        results: dict[str, str] = {}

        if config["notify_owner"]:
            owner_user = None
            owner_id = settings.bot_owner_id

            if not owner_id and self.bot.application:
                if self.bot.application.owner:
                    owner_user = self.bot.application.owner
                    owner_id = owner_user.id
                elif hasattr(self.bot.application, "team") and self.bot.application.team:
                    owner_id = self.bot.application.team.owner_user_id

            if not owner_user and owner_id:
                try:
                    owner_user = self.bot.get_user(owner_id) or await self.bot.fetch_user(owner_id)
                except Exception:
                    pass

            if owner_user:
                can_notify = True
                if not is_test:
                    can_notify = await self.storage.claim_notification(tag, "owner_dm", owner_user.id)

                if can_notify:
                    try:
                        await owner_user.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
                        results["owner_dm"] = f"Sent to Owner ({owner_user.name})"
                        if not is_test:
                            await self.storage.mark_notification_result(tag, "owner_dm", owner_user.id, "sent")
                    except discord.Forbidden:
                        logger.warning("Failed to send update DM to bot owner: DMs disabled/blocked.")
                        results["owner_dm"] = "Failed: Bot Owner has DMs disabled or blocked the bot."
                        if not is_test:
                            await self.storage.mark_notification_result(tag, "owner_dm", owner_user.id, "failed")
                    except Exception as exc:
                        logger.warning("Error sending update DM to bot owner: %s", exc)
                        results["owner_dm"] = f"Failed: {type(exc).__name__}"
                        if not is_test:
                            await self.storage.mark_notification_result(tag, "owner_dm", owner_user.id, "failed")
                else:
                    results["owner_dm"] = "Already notified previously"
            else:
                results["owner_dm"] = "Could not resolve Bot Owner"

        channel_id = config.get("notification_channel_id")
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except Exception:
                    channel = None

            if channel and isinstance(channel, (discord.TextChannel, discord.Thread)):
                can_notify = True
                if not is_test:
                    can_notify = await self.storage.claim_notification(tag, "channel", channel.id)

                if can_notify:
                    try:
                        perms = channel.permissions_for(channel.guild.me)
                        if not perms.send_messages or not perms.embed_links:
                            results["channel"] = f"Failed: Missing 'Send Messages' or 'Embed Links' in {channel.mention}."
                            if not is_test:
                                await self.storage.mark_notification_result(tag, "channel", channel.id, "failed")
                        else:
                            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
                            results["channel"] = f"Sent to {channel.mention}"
                            if not is_test:
                                await self.storage.mark_notification_result(tag, "channel", channel.id, "sent")
                    except Exception as exc:
                        logger.warning("Failed to send update to channel %s: %s", channel_id, exc)
                        results["channel"] = f"Failed: {type(exc).__name__}"
                        if not is_test:
                            await self.storage.mark_notification_result(tag, "channel", channel.id, "failed")
                else:
                    results["channel"] = "Already notified previously"
            else:
                results["channel"] = "Configured channel no longer exists"

        if not is_test and ("owner_dm" in results or "channel" in results):
            await self.storage.set_last_notified_tag(tag)

        return results

    async def check_and_notify(
        self, manual: bool = False
    ) -> tuple[bool, str, dict[str, Any] | None, bool]:
        async with self._lock:
            config = await self.storage.get_update_config()
            include_prereleases = config["include_prereleases"]

            success, release_dict, error_msg = await self.fetch_latest_release(
                include_prereleases=include_prereleases
            )

            if not success or not release_dict:
                await self.storage.record_update_check_failure(
                    status="error", error_message=error_msg or "Unknown error"
                )
                return False, error_msg or "Could not fetch releases from GitHub.", None, False

            await self.storage.record_update_check_success(release_dict)

            latest_tag = release_dict.get("tag_name", "")
            running_version = config["running_version"]

            update_available = is_newer_version(latest_tag, running_version)

            if update_available:
                last_notified = config.get("last_notified_tag")
                if latest_tag != last_notified:
                    logger.info("New release discovered: %s (running: %s). Broadcasting notifications.", latest_tag, running_version)
                    await self.notify_destinations(release_dict, is_test=False)
                msg = f"A new version is available: **{latest_tag}** (running: `v{running_version}`)."
            else:
                msg = f"You are running the latest version (`v{running_version}`)."

            return True, msg, release_dict, update_available