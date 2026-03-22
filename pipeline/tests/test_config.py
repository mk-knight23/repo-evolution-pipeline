"""Tests for pipeline.core.config — configuration management."""

import pytest
import os
from unittest.mock import patch

from pipeline.core.config import PipelineConfig


class TestPipelineConfig:
    def test_default_config(self):
        cfg = PipelineConfig()
        assert cfg.max_concurrent == 3
        assert cfg.batch_size == 5
        assert cfg.max_retries == 3

    def test_custom_config(self):
        cfg = PipelineConfig(max_concurrent=10, batch_size=3)
        assert cfg.max_concurrent == 10
        assert cfg.batch_size == 3

    def test_framework_map(self):
        cfg = PipelineConfig()
        assert "portfolio" in cfg.framework_map
        assert "webapp" in cfg.framework_map

    def test_navigation_map(self):
        cfg = PipelineConfig()
        assert "portfolio" in cfg.navigation_map


class TestSecretManagement:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-12345"})
    def test_anthropic_key_from_env(self):
        cfg = PipelineConfig()
        assert cfg.llm.api_key == "test-key-12345"

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key_raises(self):
        cfg = PipelineConfig()
        with pytest.raises(EnvironmentError):
            _ = cfg.llm.api_key
