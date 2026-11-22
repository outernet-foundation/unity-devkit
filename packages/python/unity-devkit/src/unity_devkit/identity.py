from __future__ import annotations

BUILD_CHANNELS = ("pr", "dev", "stable")


def cache_key(project: str, platform: str, pr_number: int | None) -> str:
    scope = f"pr-{pr_number}" if pr_number is not None else "dev"
    return f"{project.lower()}-{platform}-{scope}"


def builds_tag(channel: str, sha: str) -> str:
    if channel not in BUILD_CHANNELS:
        raise SystemExit(f"unknown channel '{channel}' (expected pr, dev, or stable)")
    return f"{channel}-sha-{sha}"


def cache_registry(root: str) -> str:
    return f"{root}/cache"


def builds_registry(root: str) -> str:
    return f"{root}/builds"
