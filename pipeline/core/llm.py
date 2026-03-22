"""
LLM client factory with retry logic, rate limiting, cost tracking,
and circuit breaker resilience (v3.0).
Supports multiple providers (Anthropic direct, Alibaba Coding, etc.)
"""

from __future__ import annotations

import json
import re
import logging
import time
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field

from pipeline.core.config import config

logger = logging.getLogger("pipeline.llm")


# ── Cost Tracking ──────────────────────────────────────────────────────────

COST_PER_1K_INPUT = {
    "claude-sonnet-4-5-20250514": 0.003,
    "claude-haiku-4-5-20241022": 0.001,
}

COST_PER_1K_OUTPUT = {
    "claude-sonnet-4-5-20250514": 0.015,
    "claude-haiku-4-5-20241022": 0.005,
}


@dataclass
class CostTracker:
    """Track LLM API costs across the pipeline run."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    calls_by_model: dict = field(default_factory=dict)
    cost_by_stage: dict = field(default_factory=dict)

    def record(self, model: Optional[str], input_tokens: int, output_tokens: int, stage: str = "unknown"):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_calls += 1

        model_key: str = model or "unknown"
        if model_key not in self.calls_by_model:
            self.calls_by_model[model_key] = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
        self.calls_by_model[model_key]["calls"] += 1
        self.calls_by_model[model_key]["input_tokens"] += input_tokens
        self.calls_by_model[model_key]["output_tokens"] += output_tokens

        input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT.get(model_key, 0.003)
        output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT.get(model_key, 0.015)
        total_cost = input_cost + output_cost

        if stage not in self.cost_by_stage:
            self.cost_by_stage[stage] = 0.0
        self.cost_by_stage[stage] += total_cost

    @property
    def total_cost_usd(self) -> float:
        return sum(self.cost_by_stage.values())

    def summary(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": float(round(float(self.total_cost_usd), 4)),
            "cost_by_stage": {k: float(round(float(v), 4)) for k, v in dict(self.cost_by_stage).items()},
            "calls_by_model": self.calls_by_model,
        }


# Singleton cost tracker
cost_tracker = CostTracker()


# ── Circuit Breaker ────────────────────────────────────────────────────────

class CircuitState(str, Enum):
    CLOSED = "closed"        # Normal operation — requests flow through
    OPEN = "open"            # Tripped — all requests are rejected immediately
    HALF_OPEN = "half_open"  # Testing — allow one request to probe recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for LLM provider resilience.

    Prevents cascading failures by tracking consecutive errors per provider
    and temporarily disabling providers that are failing.

    States:
      CLOSED   → requests pass through normally
      OPEN     → all requests rejected (provider is down)
      HALF_OPEN → one probe request allowed to test recovery
    """
    failure_threshold: int = 5
    reset_timeout_seconds: int = 60

    # Internal state per provider key
    _states: dict[str, CircuitState] = field(default_factory=dict)
    _failure_counts: dict[str, int] = field(default_factory=dict)
    _last_failure_time: dict[str, float] = field(default_factory=dict)

    def get_state(self, provider: str) -> CircuitState:
        """Get current circuit state for a provider."""
        state = self._states.get(provider, CircuitState.CLOSED)

        # Auto-transition from OPEN → HALF_OPEN after reset timeout
        if state == CircuitState.OPEN:
            last_fail = self._last_failure_time.get(provider, 0)
            if time.time() - last_fail >= self.reset_timeout_seconds:
                self._states[provider] = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker for {provider}: OPEN → HALF_OPEN (reset timeout elapsed)")
                return CircuitState.HALF_OPEN

        return state

    def is_available(self, provider: str) -> bool:
        """Check if a provider is available (not in OPEN state)."""
        return self.get_state(provider) != CircuitState.OPEN

    def record_success(self, provider: str) -> None:
        """Record a successful call — reset the circuit to CLOSED."""
        previous = self._states.get(provider, CircuitState.CLOSED)
        self._states[provider] = CircuitState.CLOSED
        self._failure_counts[provider] = 0
        if previous != CircuitState.CLOSED:
            logger.info(f"Circuit breaker for {provider}: {previous.value} → CLOSED (success)")

    def record_failure(self, provider: str) -> None:
        """Record a failed call — may trip the circuit to OPEN."""
        count = self._failure_counts.get(provider, 0) + 1
        self._failure_counts[provider] = count
        self._last_failure_time[provider] = time.time()

        state = self._states.get(provider, CircuitState.CLOSED)

        if state == CircuitState.HALF_OPEN:
            # Probe failed — back to OPEN
            self._states[provider] = CircuitState.OPEN
            logger.warning(f"Circuit breaker for {provider}: HALF_OPEN → OPEN (probe failed)")
        elif count >= self.failure_threshold:
            self._states[provider] = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker for {provider}: CLOSED → OPEN "
                f"(threshold {self.failure_threshold} reached)"
            )

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of all circuit states."""
        return {
            provider: self.get_state(provider).value
            for provider in set(list(self._states.keys()) + list(self._failure_counts.keys()))
        }


# Singleton circuit breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=config.circuit_breaker_threshold
    if hasattr(config, 'circuit_breaker_threshold') else 5,
    reset_timeout_seconds=config.circuit_breaker_reset_seconds
    if hasattr(config, 'circuit_breaker_reset_seconds') else 60,
)


# ── Prompt Sanitization (SENTINEL) ─────────────────────────────────────────

def sanitize_prompt(prompt: str) -> str:
    """Strip potential injection patterns from LLM prompts.

    Removes:
      - System prompt override attempts
      - Encoded payloads that could confuse the model
      - Excessively long single lines (potential buffer overflow attempts)
    """
    # Remove system prompt injection attempts
    prompt = re.sub(
        r"(?i)(system\s*:\s*|<\|system\|>|\[SYSTEM\]|<<SYS>>)",
        "[FILTERED] ",
        prompt,
    )

    # Remove null bytes and control characters (except newline/tab)
    prompt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", prompt)

    return prompt


# ── JSON Extraction ────────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    """Robustly extract JSON from LLM response.

    Handles:
      1. <think>...</think> chain-of-thought blocks (Qwen3, DeepSeek)
      2. ```json ... ``` code fences
      3. Raw JSON objects
      4. Regex fallback for embedded JSON
    """
    # Strip chain-of-thought
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Code fence extraction
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1]

    # Direct parse
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        pass

    # Regex fallback: find outermost { ... }
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        json_str = match.group(1)
        # Attempt to clean common JSON errors (trailing commas)
        json_str = re.sub(r",\s*([\]}])", r"\1", json_str)
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

    raise ValueError(f"No valid JSON found in LLM response (first 200 chars: {str(text)[:200]})")


# ── Knowledge Base Accessor ────────────────────────────────────────────────

class KnowledgeBaseAccessor:
    """Injects framework-specific best practices into LLM prompts."""
    
    BEST_PRACTICES = {
        "expo": [
            "Use expo-router for file-based navigation.",
            "Prefer standard Expo SDK libraries (expo-blur, expo-image) for reliability.",
            "Use Reanimated for 60fps animations.",
            "Implement Expo Font for custom typography loading."
        ],
        "premium_ui": [
            "Use Glassmorphism (BlurView + transparent borders) for high-end feel.",
            "Implement micro-interactions on all Pressables using Reanimated.",
            "Use a sophisticated spacing scale (4pt grid).",
            "Apply semantic color tokens (primary, surface, glass) from the theme."
        ],
        "performance": [
            "Use FlashList for large lists instead of FlatList.",
            "Memoize heavy components with React.memo.",
            "Avoid anonymous arrow functions in render props.",
            "Optimize images with responsive sizing."
        ],
        "authority": [
            "You have full creative authority to reinvent the UI for mobile excellence.",
            "Do not follow the source web components literally if they feel clunky on mobile.",
            "Optimize for one-handed operation (bottom-heavy actions).",
            "Build 'Alive' interfaces: use haptic feedback and micro-interactions generously.",
            "NEVER use placeholders. If a component is missing, brainstorm and implement a best-in-class version."
        ]
    }

    @classmethod
    def get_context(cls, categories: list[str]) -> str:
        """Fetch consolidated best practices for the given categories."""
        context = []
        for cat in categories:
            practices = cls.BEST_PRACTICES.get(cat.lower(), [])
            if practices:
                context.append(f"### Best Practices: {cat.upper()}")
                context.extend([f"- {p}" for p in practices])
        
        return "\n".join(context) if context else ""

# Global accessor
kb_accessor = KnowledgeBaseAccessor()


# ── LLM Client ─────────────────────────────────────────────────────────────

# ── LLM Client ─────────────────────────────────────────────────────────────

def create_llm(
    provider: str = "dashscope",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    heavy: bool = True,
    temperature: Optional[float] = None
):
    """Create a LangChain LLM instance (OpenAI or Anthropic)."""
    temp = temperature if temperature is not None else (
        config.llm.temperature_codegen if heavy else config.llm.temperature_docs
    )

    if provider == "dashscope":
        from langchain_openai import ChatOpenAI
        model_name = model or config.dashscope.model_primary
        return ChatOpenAI(
            model=model_name,
            api_key=api_key or config.dashscope.api_keys[0],
            base_url=config.dashscope.openai_url,
            temperature=temp,
            max_tokens=config.llm.max_tokens,
        )
    else:
        from langchain_anthropic import ChatAnthropic
        model_name = model or (config.llm.model_heavy if heavy else config.llm.model_light)
        kwargs = {
            "model": model_name,
            "temperature": temp,
            "max_tokens": config.llm.max_tokens,
            "api_key": api_key or config.llm.api_key,
        }
        if config.llm.base_url:
            kwargs["anthropic_api_url"] = config.llm.base_url
        return ChatAnthropic(**kwargs)


async def invoke_with_retry(
    prompt: str,
    heavy: bool = True,
    temperature: Optional[float] = None,
    stage: str = "unknown",
    parse_json: bool = True,
    include_practices: Optional[list[str]] = None,
) -> dict | str:
    """Invokes LLM with massive fallback chain: DashScope Keys -> DashScope Models -> Anthropic.

    v3.0: Integrates circuit breaker pattern to skip providers experiencing outages,
    and sanitizes prompts to prevent injection attacks.
    """
    # Sanitize prompt (SENTINEL)
    prompt = sanitize_prompt(prompt)

    if include_practices:
        kb_context = kb_accessor.get_context(include_practices)
        if kb_context:
            prompt = f"{prompt}\n\n## Technical Context / Best Practices\n{kb_context}"

    # Fallback Chain Configuration
    dash_keys = config.dashscope.api_keys
    dash_models = config.dashscope.authorized_models
    
    # 1. Try DashScope with Key Rotation & Model Fallback (circuit-breaker aware)
    for model_name in dash_models:
        provider_key = f"dashscope:{model_name}"

        if not circuit_breaker.is_available(provider_key):
            logger.debug(f"[{stage}] Skipping {model_name} — circuit breaker OPEN")
            continue

        for idx, key in enumerate(dash_keys):
            try:
                llm = create_llm(
                    provider="dashscope", 
                    model=model_name, 
                    api_key=key, 
                    heavy=heavy, 
                    temperature=temperature
                )
                
                logger.info(f"[{stage}] Calling DashScope ({model_name}) with key index {idx}")
                response = await llm.ainvoke(prompt)
                content = response.content

                # Track cost
                input_tokens = int(len(prompt) / 3.5)
                output_tokens = int(len(content) / 3.5)
                cost_tracker.record(model_name, input_tokens, output_tokens, stage)

                # Success — reset circuit breaker
                circuit_breaker.record_success(provider_key)

                if parse_json:
                    return extract_json(content)
                return content

            except Exception as e:
                logger.warning(f"DashScope {model_name} failed with key {idx}: {str(e)[:100]}")
                circuit_breaker.record_failure(provider_key)
                continue

    # 2. Final Fallback to Anthropic (The "Golden" Reference)
    anthropic_provider = "anthropic:direct"
    if not circuit_breaker.is_available(anthropic_provider):
        logger.critical(f"[{stage}] ALL providers have open circuit breakers.")
        raise RuntimeError("All LLM providers are unavailable (circuit breakers open)")

    logger.error(f"[{stage}] ALL DashScope models/keys failed. Falling back to Anthropic.")
    try:
        llm = create_llm(provider="anthropic", heavy=heavy, temperature=temperature)
        response = await llm.ainvoke(prompt)
        content = response.content
        
        # Track cost
        model = config.llm.model_heavy if heavy else config.llm.model_light
        cost_tracker.record(model, int(len(prompt)/4), int(len(content)/4), stage)

        circuit_breaker.record_success(anthropic_provider)
        
        if parse_json:
            return extract_json(content)
        return content
    except Exception as e:
        circuit_breaker.record_failure(anthropic_provider)
        logger.critical(f"FATAL: All LLM providers failed. Last error: {e}")
        raise e
