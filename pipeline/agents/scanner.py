"""
Repository Scanner Agent — deep clone and source file extraction.
Handles GitHub API access, file filtering, and content extraction.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from pipeline.core.config import config

logger = logging.getLogger("pipeline.scanner")

# ── File Extension Filters ────────────────────────────────────────────────

WEB_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx",
    ".vue", ".svelte",
    ".html", ".css", ".scss", ".sass", ".less",
    ".json", ".yaml", ".yml", ".toml",
    ".md", ".mdx",
    ".py", ".rb", ".go", ".rs",
}

ASSET_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"
}

IGNORE_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt",
    "__pycache__", ".cache", "coverage", ".turbo", ".vercel",
    "vendor", "target", "out", ".output",
}

MAX_FILE_SIZE = 100_000  # 100KB per file
MAX_ASSET_SIZE = 500_000 # 500KB per asset
MAX_TOTAL_FILES = 150
MAX_TOTAL_CHARS = 500_000  # 500K chars total budget


# ── Deep Clone & Read ─────────────────────────────────────────────────────


def deep_clone_and_read(repo_name: str, github_url: str = "", commit_sha: str = "") -> dict[str, str]:
    """
    Clone a GitHub repo and extract source files for analysis.
    
    Returns:
        dict mapping relative file paths to their contents.
    """
    if not github_url:
        github_url = f"https://github.com/{config.github.org}/{repo_name}"

    cache_key = _build_clone_cache_key(repo_name, github_url, commit_sha)
    if cache_key:
        cached_files = _load_cached_clone(cache_key)
        if cached_files is not None:
            logger.info(f"Using cached clone payload for {repo_name} ({commit_sha[:8]})")
            return cached_files

    logger.info(f"Cloning {github_url}...")

    try:
        files = _clone_and_extract(github_url, repo_name)
        if files and cache_key:
            _save_cached_clone(cache_key, repo_name, github_url, commit_sha, files)
        logger.info(f"Extracted {len(files)} source files from {repo_name}")
        return files
    except Exception as e:
        logger.warning(f"Clone failed for {repo_name}: {e}")
        # Fallback: try GitHub API
        files = _fetch_via_api(repo_name)
        if files and cache_key:
            _save_cached_clone(cache_key, repo_name, github_url, commit_sha, files)
        return files


def _build_clone_cache_key(repo_name: str, github_url: str, commit_sha: str) -> str:
    """Build a deterministic cache key for source extraction.

    We only cache when a commit SHA is available so the cache is content-addressable,
    not tied to a moving branch head.
    """
    if not commit_sha:
        return ""

    hasher = hashlib.sha256()
    hasher.update(repo_name.encode("utf-8"))
    hasher.update(github_url.encode("utf-8"))
    hasher.update(commit_sha.encode("utf-8"))
    return hasher.hexdigest()[:24]


def _clone_cache_path(cache_key: str) -> Path:
    return Path(config.data_dir) / "clone-cache" / f"{cache_key}.json"


def _load_cached_clone(cache_key: str) -> Optional[dict[str, str]]:
    if not cache_key:
        return None

    path = _clone_cache_path(cache_key)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    files = payload.get("files")
    return files if isinstance(files, dict) else None


def _save_cached_clone(
    cache_key: str,
    repo_name: str,
    github_url: str,
    commit_sha: str,
    files: dict[str, str],
) -> None:
    if not cache_key:
        return

    path = _clone_cache_path(cache_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "repo_name": repo_name,
        "github_url": github_url,
        "commit_sha": commit_sha,
        "files": files,
    }
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp_path, path)


def _clone_and_extract(github_url: str, repo_name: str) -> dict[str, str]:
    """Clone repo to temp dir, extract matching files."""
    import subprocess

    tmpdir = tempfile.mkdtemp(prefix="repo-evo-")
    clone_dir = os.path.join(tmpdir, repo_name.replace("/", "-"))

    try:
        # Shallow clone for speed
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", github_url, clone_dir],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr[:200]}")

        return _extract_files(Path(clone_dir))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _extract_files(root: Path) -> dict[str, str]:
    """Walk directory tree and extract source files within budget."""
    files: dict[str, str] = {}
    total_chars = 0

    # Priority order: config files first, then source files
    priority_files = [
        "package.json", "tsconfig.json", "app.json", "expo.json",
        "next.config.js", "next.config.ts", "nuxt.config.ts",
        "vite.config.ts", "svelte.config.js", "astro.config.mjs",
        "pubspec.yaml", "Cargo.toml", "go.mod",
        "README.md", "readme.md",
    ]

    # Collect priority files first
    for pf in priority_files:
        fp = root / pf
        if fp.exists() and fp.stat().st_size <= MAX_FILE_SIZE:
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                files[pf] = content
                total_chars += len(content)
            except Exception:
                pass

    # Then walk for source files
    for path in sorted(root.rglob("*")):
        if len(files) >= MAX_TOTAL_FILES or total_chars >= MAX_TOTAL_CHARS:
            break

        if not path.is_file():
            continue

        # Skip ignored directories
        rel = path.relative_to(root)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue

        # Skip already-added priority files
        rel_str = str(rel)
        if rel_str in files:
            continue

        # Filter by extension
        ext = path.suffix.lower()
        if ext not in WEB_EXTENSIONS and ext not in ASSET_EXTENSIONS:
            continue

        # Size check
        is_asset = ext in ASSET_EXTENSIONS
        if is_asset and path.stat().st_size > MAX_ASSET_SIZE:
            continue
        elif not is_asset and path.stat().st_size > MAX_FILE_SIZE:
            continue

        try:
            if is_asset:
                import base64
                with open(path, "rb") as f:
                    content = f"data:image/{ext.replace('.', '')};base64," + base64.b64encode(f.read()).decode("utf-8")
                    files[rel_str] = content
            else:
                content = path.read_text(encoding="utf-8", errors="replace")
                files[rel_str] = content
                total_chars += len(content)
        except Exception:
            pass

    return files


def _fetch_via_api(repo_name: str) -> dict[str, str]:
    """Fallback: fetch key files via GitHub REST API."""
    try:
        import requests
    except ImportError:
        logger.warning("requests not installed — cannot use GitHub API fallback")
        return {}

    token = config.github.token
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    files: dict[str, str] = {}
    api_base = f"https://api.github.com/repos/{config.github.org}/{repo_name}"

    # Fetch repo tree
    try:
        tree_resp = requests.get(
            f"{api_base}/git/trees/HEAD?recursive=1",
            headers=headers, timeout=30,
        )
        if tree_resp.status_code != 200:
            logger.warning(f"GitHub API returned {tree_resp.status_code}")
            return {}

        tree = tree_resp.json().get("tree", [])
        total_chars = 0

        for item in tree:
            if len(files) >= MAX_TOTAL_FILES or total_chars >= MAX_TOTAL_CHARS:
                break
            if item["type"] != "blob":
                continue

            path = item["path"]
            ext = os.path.splitext(path)[1].lower()
            if ext not in WEB_EXTENSIONS and ext not in ASSET_EXTENSIONS:
                continue
            if any(d in path.split("/") for d in IGNORE_DIRS):
                continue

            # Fetch file content
            is_asset = ext in ASSET_EXTENSIONS
            try:
                if is_asset:
                    # Download binary data for assets
                    content_resp = requests.get(
                        f"{api_base}/contents/{path}",
                        headers={**headers, "Accept": "application/vnd.github.v3.raw"},
                        timeout=15,
                    )
                    if content_resp.status_code == 200:
                        import base64
                        content_bytes = content_resp.content
                        if len(content_bytes) <= MAX_ASSET_SIZE:
                            encoded = base64.b64encode(content_bytes).decode("utf-8")
                            files[path] = f"data:image/{ext.replace('.', '')};base64,{encoded}"
                else:
                    content_resp = requests.get(
                        f"{api_base}/contents/{path}",
                        headers={**headers, "Accept": "application/vnd.github.v3.raw"},
                        timeout=15,
                    )
                    if content_resp.status_code == 200:
                        content = content_resp.text
                        if len(content) <= MAX_FILE_SIZE:
                            files[path] = content
                            total_chars += len(content)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"GitHub API fetch failed: {e}")

    return files


# ── Utility Functions ─────────────────────────────────────────────────────

def detect_framework_from_files(files: dict[str, str]) -> Optional[str]:
    """Detect the web framework from package.json and config files."""
    import json

    pkg = files.get("package.json", "")
    if not pkg:
        return None

    try:
        pkg_data = json.loads(pkg)
    except json.JSONDecodeError:
        return None

    all_deps = {
        **pkg_data.get("dependencies", {}),
        **pkg_data.get("devDependencies", {}),
    }

    # Detection priority order
    framework_signals = [
        ("next", "Next.js"),
        ("nuxt", "Nuxt"),
        ("@sveltejs/kit", "SvelteKit"),
        ("svelte", "Svelte"),
        ("astro", "Astro"),
        ("gatsby", "Gatsby"),
        ("vue", "Vue"),
        ("@angular/core", "Angular"),
        ("react", "React"),
        ("express", "Express"),
        ("fastify", "Fastify"),
        ("django", "Django"),
        ("flask", "Flask"),
    ]

    for signal, name in framework_signals:
        if signal in all_deps:
            return name

    # Check config files
    if "next.config.js" in files or "next.config.ts" in files:
        return "Next.js"
    if "nuxt.config.ts" in files:
        return "Nuxt"
    if "svelte.config.js" in files:
        return "SvelteKit"
    if "astro.config.mjs" in files:
        return "Astro"

    return "Unknown"


def extract_routes(files: dict[str, str]) -> list[str]:
    """Extract route/page paths from file structure."""
    routes = []

    for path in files:
        # Next.js pages/app router
        if path.startswith("src/app/") or path.startswith("app/"):
            if path.endswith("page.tsx") or path.endswith("page.js"):
                route = "/" + "/".join(path.split("/")[1:-1])
                if route.endswith("/"):
                    route = route[:-1] or "/"
                routes.append(route)

        elif path.startswith("src/pages/") or path.startswith("pages/"):
            if not path.endswith("_app.tsx") and not path.endswith("_document.tsx"):
                route = "/" + path.split("pages/")[1].rsplit(".", 1)[0]
                route = route.replace("/index", "").replace("index", "")
                if not route:
                    route = "/"
                routes.append(route)

        # Nuxt pages
        elif path.startswith("pages/") and path.endswith(".vue"):
            route = "/" + path.replace("pages/", "").rsplit(".", 1)[0]
            route = route.replace("/index", "").replace("index", "")
            if not route:
                route = "/"
            routes.append(route)

    return sorted(set(routes))
