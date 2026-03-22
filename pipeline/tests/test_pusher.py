from pathlib import Path

from pipeline.agents.pusher import (
    _build_push_idempotency_key,
    _find_existing_push_for_key,
    _write_audit_log,
)
from pipeline.core.config import config
from pipeline.core.models import MobileArchitecture, MobileFramework, NavigationType, RepoCategory, RepoManifest


def _manifest() -> RepoManifest:
    return RepoManifest(
        name="demo-app",
        github_url="https://github.com/user/demo-app",
        category=RepoCategory.WEBAPP,
        commit_sha="abc123",
    )


def _architecture() -> MobileArchitecture:
    return MobileArchitecture(
        framework=MobileFramework.EXPO,
        navigation_type=NavigationType.TABS,
    )


def test_push_idempotency_key_is_deterministic():
    manifest = _manifest()
    arch = _architecture()
    files = {"README.md": "hello", "src/app.ts": "export const x = 1;"}

    key_a = _build_push_idempotency_key(manifest, arch, files)
    key_b = _build_push_idempotency_key(manifest, arch, dict(files))

    assert key_a == key_b


def test_push_idempotency_key_changes_with_file_content():
    manifest = _manifest()
    arch = _architecture()

    key_a = _build_push_idempotency_key(manifest, arch, {"README.md": "hello"})
    key_b = _build_push_idempotency_key(manifest, arch, {"README.md": "hello world"})

    assert key_a != key_b


def test_find_existing_push_for_key_reads_audit_log(tmp_path):
    original_data_dir = config.data_dir
    object.__setattr__(config, "data_dir", tmp_path)

    try:
        manifest = _manifest()
        arch = _architecture()
        key = _build_push_idempotency_key(manifest, arch, {"README.md": "hello"})
        _write_audit_log(manifest, arch, "https://gitlab.com/demo/demo-app", idempotency_key=key)

        found = _find_existing_push_for_key(key)
        assert found == "https://gitlab.com/demo/demo-app"
        assert (Path(tmp_path) / "logs" / "push_audit.jsonl").exists()
    finally:
        object.__setattr__(config, "data_dir", original_data_dir)