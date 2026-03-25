"""
Centralized configuration management — NO hardcoded secrets.
All sensitive values MUST come from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider configuration."""
    model_heavy: str = "claude-sonnet-4-5-20250514"
    model_light: str = "claude-haiku-4-5-20241022"
    temperature_analysis: float = 0.2
    temperature_codegen: float = 0.1
    temperature_docs: float = 0.3
    max_tokens: int = 8192
    max_retries: int = 3
    retry_delay_seconds: list = field(default_factory=lambda: [5, 15, 30])

    @property
    def api_key(self) -> str:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set. Export it before running.")
        return key

    @property
    def base_url(self) -> Optional[str]:
        return os.environ.get("ANTHROPIC_BASE_URL")


@dataclass(frozen=True)
class OmniRouteConfig:
    """OmniRoute AI gateway configuration (OpenAI-compatible endpoint)."""
    # Models to try in order — OmniRoute handles internal fallback per model
    authorized_models: list[str] = field(default_factory=lambda: [
        "if/kimi-k2-thinking",   # iFlow — unlimited, free
        "kr/claude-sonnet-4-5",  # Kiro (AWS Builder) — unlimited Claude
        "qw/qwen3-coder-plus",   # Qwen — unlimited, free
        "gc/gemini-3-flash-preview",  # Gemini CLI — 1K req/day
        "if/deepseek-r1",        # iFlow DeepSeek — unlimited
    ])

    @property
    def base_url(self) -> str:
        return os.environ.get("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")

    @property
    def api_key(self) -> str:
        # OmniRoute accepts any non-empty string as the API key
        return os.environ.get("OMNIROUTE_API_KEY", "omniroute")

    @property
    def enabled(self) -> bool:
        return os.environ.get("OMNIROUTE_ENABLED", "0").lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class DashScopeConfig:
    """Alibaba DashScope configuration."""
    model_primary: str = "qwen3.5-plus"
    model_secondary: str = "qwen3-max-2026-01-23"
    model_premium: str = "qwen3.5-plus"  # Alias for high-authority tasks
    model_codegen: str = "qwen3-coder-max" # Specialist for code
    model_fallback: str = "qwen3-coder-plus"
    
    # List of all authorized models for rotation
    authorized_models: list[str] = field(default_factory=lambda: [
        "qwen3.5-plus", "qwen3-max-2026-01-23", "qwen3-coder-next", 
        "qwen3-coder-plus", "glm-5", "glm-4.7", "kimi-k2.5", "MiniMax-M2.5"
    ])
    
    @property
    def api_keys(self) -> list[str]:
        keys = os.environ.get("DASHSCOPE_API_KEYS", "")
        if not keys:
            return []
        return [k.strip() for k in keys.split(",") if k.strip()]

    @property
    def openai_url(self) -> str:
        return os.environ.get("DASHSCOPE_OPENAI_URL", "https://coding-intl.dashscope.aliyuncs.com/v1")

    @property
    def anthropic_url(self) -> str:
        return os.environ.get("DASHSCOPE_ANTHROPIC_URL", "https://coding-intl.dashscope.aliyuncs.com/apps/anthropic")


@dataclass(frozen=True)
class GitHubConfig:
    """GitHub source configuration."""
    org: str = "mk-knight23"
    base_url: str = "https://github.com"

    @property
    def token(self) -> str:
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise EnvironmentError("GITHUB_TOKEN not set. Export it before running.")
        return token

    @property
    def api_url(self) -> str:
        return f"{self.base_url}/{self.org}"


@dataclass(frozen=True)
class GitLabConfig:
    """GitLab target configuration."""
    url: str = "https://gitlab.com"
    group: str = "mk-knight23"

    @property
    def token(self) -> str:
        token = os.environ.get("GITLAB_TOKEN", "")
        if not token:
            raise EnvironmentError("GITLAB_TOKEN not set. Export it before running.")
        return token


@dataclass(frozen=True)
class SupabaseConfig:
    """State storage configuration."""

    @property
    def url(self) -> str:
        return os.environ.get("SUPABASE_URL", "")

    @property
    def key(self) -> str:
        return os.environ.get("SUPABASE_KEY", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.key)


@dataclass(frozen=True)
class PipelineConfig:
    """Master pipeline configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    omniroute: OmniRouteConfig = field(default_factory=OmniRouteConfig)
    dashscope: DashScopeConfig = field(default_factory=DashScopeConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    gitlab: GitLabConfig = field(default_factory=GitLabConfig)
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)

    # Processing parameters
    batch_size: int = 5
    max_retries: int = 3
    max_concurrent: int = 3
    source_char_limit: int = 80_000
    max_screens_per_app: int = 8
    max_file_size: int = 50_000

    # Verification (generate → verify loop)
    verification_enabled: bool = field(default_factory=lambda: os.environ.get("PIPELINE_VERIFY", "0").lower() in ("1", "true", "yes"))
    verification_strict: bool = field(default_factory=lambda: os.environ.get("PIPELINE_VERIFY_STRICT", "0").lower() in ("1", "true", "yes"))
    verification_include_web_export: bool = field(default_factory=lambda: os.environ.get("PIPELINE_VERIFY_WEB_EXPORT", "0").lower() in ("1", "true", "yes"))
    verification_timeout_seconds: int = 900
    block_push_on_verification_failure: bool = field(default_factory=lambda: os.environ.get("PIPELINE_BLOCK_PUSH_ON_VERIFY_FAIL", "1").lower() in ("1", "true", "yes"))
    verification_repair_enabled: bool = field(default_factory=lambda: os.environ.get("PIPELINE_REPAIR", "0").lower() in ("1", "true", "yes"))
    verification_repair_attempts: int = field(default_factory=lambda: int(os.environ.get("PIPELINE_REPAIR_ATTEMPTS", "1") or "1"))

    # Circuit Breaker (v3.0)
    circuit_breaker_threshold: int = field(default_factory=lambda: int(os.environ.get("CIRCUIT_BREAKER_THRESHOLD", "5") or "5"))
    circuit_breaker_reset_seconds: int = field(default_factory=lambda: int(os.environ.get("CIRCUIT_BREAKER_RESET_SECONDS", "60") or "60"))

    # Pipeline metadata
    pipeline_version: str = "3.0.0"

    # Stage management
    enabled_stages: list[str] = field(default_factory=lambda: [
        "cloning", "analyzing", "architecting", "generating", "verifying", "quality_check", "pushing"
    ])

    # Paths
    data_dir: Path = field(default_factory=lambda: Path("data"))
    clone_dir: Path = field(default_factory=lambda: Path("/tmp/repo-evolution/source"))
    output_dir: Path = field(default_factory=lambda: Path("/tmp/repo-evolution/mobile"))

    # Framework mappings (deterministic rules)
    framework_map: dict = field(default_factory=lambda: {
        "portfolio": "expo",
        "webapp": "react-native",
        "game": "flutter",
        "tool": "expo",
        "starter": "expo",
        "other": "expo",
    })

    navigation_map: dict = field(default_factory=lambda: {
        "portfolio": "tab",
        "webapp": "hybrid",
        "game": "stack",
        "tool": "drawer",
        "starter": "stack",
        "other": "tab",
    })

    state_management_map: dict = field(default_factory=lambda: {
        "expo": "zustand",
        "react-native": "zustand",
        "flutter": "riverpod",
        "ionic": "pinia",
    })

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.clone_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# Singleton config instance
config = PipelineConfig()
