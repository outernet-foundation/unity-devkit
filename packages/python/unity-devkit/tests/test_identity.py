from unity_devkit.identity import builds_registry, cache_key, cache_registry


def test_cache_key_scopes_to_pr_when_present() -> None:
    assert cache_key("Tool", "AndroidMobile", 5) == "tool-AndroidMobile-pr-5"


def test_cache_key_falls_back_to_dev_scope() -> None:
    assert cache_key("Tool", "Linux", None) == "tool-Linux-dev"


def test_cache_key_lowercases_project_name_only() -> None:
    assert cache_key("CaptureTool", "Linux", None) == "capturetool-Linux-dev"


def test_registry_namespaces_derive_from_the_repo_root() -> None:
    assert cache_registry("ghcr.io/org/repo") == "ghcr.io/org/repo/cache"
    assert builds_registry("ghcr.io/org/repo") == "ghcr.io/org/repo/builds"
