"""Tests for pipeline.agents.scanner — file extraction and analysis."""


from pathlib import Path

from pipeline.agents.scanner import (
    deep_clone_and_read,
    detect_framework_from_files,
    extract_routes,
    WEB_EXTENSIONS,
    IGNORE_DIRS,
)
from pipeline.core.config import config


class TestDetectFramework:
    def test_detect_nextjs(self, sample_source_files):
        fw = detect_framework_from_files(sample_source_files)
        assert fw == "Next.js"

    def test_detect_react(self):
        files = {"package.json": '{"dependencies": {"react": "18.2.0", "react-dom": "18.2.0"}}'}
        fw = detect_framework_from_files(files)
        assert fw == "React"

    def test_detect_vue(self):
        files = {"package.json": '{"dependencies": {"vue": "3.4.0"}}'}
        fw = detect_framework_from_files(files)
        assert fw == "Vue"

    def test_no_package_json(self):
        files = {"src/main.ts": "console.log('hello')"}
        fw = detect_framework_from_files(files)
        assert fw is None

    def test_invalid_json(self):
        files = {"package.json": "not json"}
        fw = detect_framework_from_files(files)
        assert fw is None


class TestExtractRoutes:
    def test_nextjs_app_router(self, sample_source_files):
        routes = extract_routes(sample_source_files)
        assert "/" in routes or "/app" in routes or len(routes) > 0

    def test_nextjs_pages_router(self):
        files = {
            "pages/index.tsx": "",
            "pages/about.tsx": "",
            "pages/blog/[slug].tsx": "",
        }
        routes = extract_routes(files)
        assert "/" in routes
        assert "/about" in routes

    def test_empty_files(self):
        routes = extract_routes({})
        assert routes == []


class TestConstants:
    def test_web_extensions_include_common(self):
        assert ".ts" in WEB_EXTENSIONS
        assert ".tsx" in WEB_EXTENSIONS
        assert ".js" in WEB_EXTENSIONS
        assert ".json" in WEB_EXTENSIONS

    def test_ignore_dirs_include_node_modules(self):
        assert "node_modules" in IGNORE_DIRS
        assert ".git" in IGNORE_DIRS


class TestCloneIdempotency:
    def test_clone_cache_hit_skips_clone(self, monkeypatch, tmp_path):
        original_data_dir = config.data_dir
        object.__setattr__(config, "data_dir", tmp_path)

        try:
            calls = {"clone": 0}
            expected = {"package.json": "{}"}

            def fake_clone(github_url, repo_name):
                calls["clone"] += 1
                return expected

            monkeypatch.setattr("pipeline.agents.scanner._clone_and_extract", fake_clone)
            monkeypatch.setattr("pipeline.agents.scanner._fetch_via_api", lambda repo_name: {})

            first = deep_clone_and_read(
                "demo",
                github_url="https://github.com/user/demo",
                commit_sha="abc123",
            )
            second = deep_clone_and_read(
                "demo",
                github_url="https://github.com/user/demo",
                commit_sha="abc123",
            )

            assert first == expected
            assert second == expected
            assert calls["clone"] == 1
            assert list((Path(tmp_path) / "clone-cache").glob("*.json"))
        finally:
            object.__setattr__(config, "data_dir", original_data_dir)

    def test_clone_cache_requires_commit_sha(self, monkeypatch, tmp_path):
        original_data_dir = config.data_dir
        object.__setattr__(config, "data_dir", tmp_path)

        try:
            calls = {"clone": 0}

            def fake_clone(github_url, repo_name):
                calls["clone"] += 1
                return {"README.md": "hello"}

            monkeypatch.setattr("pipeline.agents.scanner._clone_and_extract", fake_clone)
            monkeypatch.setattr("pipeline.agents.scanner._fetch_via_api", lambda repo_name: {})

            deep_clone_and_read("demo", github_url="https://github.com/user/demo")
            deep_clone_and_read("demo", github_url="https://github.com/user/demo")

            assert calls["clone"] == 2
            assert not (Path(tmp_path) / "clone-cache").exists()
        finally:
            object.__setattr__(config, "data_dir", original_data_dir)
