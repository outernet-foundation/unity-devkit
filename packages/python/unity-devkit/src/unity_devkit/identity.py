from __future__ import annotations


def cache_key(project: str, platform: str, pr_number: int | None) -> str:
    scope = f"pr-{pr_number}" if pr_number is not None else "dev"
    return f"{project.lower()}-{platform}-{scope}"


def cache_registry(root: str) -> str:
    return f"{root}/cache"


def builds_registry(root: str) -> str:
    return f"{root}/builds"
