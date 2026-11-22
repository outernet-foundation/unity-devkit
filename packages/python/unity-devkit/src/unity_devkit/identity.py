from __future__ import annotations

from typing import NamedTuple

BUILD_CHANNELS = ("pr", "dev", "stable")


class ChannelSuffix(NamedTuple):
    id_suffix: str
    display_suffix: str


def cache_key(project: str, platform: str, pr_number: int | None) -> str:
    scope = f"pr-{pr_number}" if pr_number is not None else "dev"
    return f"{project.lower()}-{platform}-{scope}"


def channel_suffix(channel: str, pr_number: int | None) -> ChannelSuffix:
    if not channel:
        return ChannelSuffix("", "")
    if channel == "pr":
        if pr_number is None:
            raise SystemExit("channel 'pr' requires a pull-request number")
        return ChannelSuffix(f".pr{pr_number}", f" (pr {pr_number})")
    if channel == "dev":
        return ChannelSuffix(".dev", " (dev)")
    if channel == "stable":
        return ChannelSuffix("", "")
    raise SystemExit(f"unknown channel '{channel}' (expected pr, dev, or stable)")


def builds_tag(channel: str, sha: str) -> str:
    if channel not in BUILD_CHANNELS:
        raise SystemExit(f"unknown channel '{channel}' (expected pr, dev, or stable)")
    return f"{channel}-sha-{sha}"


def cache_registry(root: str) -> str:
    return f"{root}/cache"


def builds_registry(root: str) -> str:
    return f"{root}/builds"
