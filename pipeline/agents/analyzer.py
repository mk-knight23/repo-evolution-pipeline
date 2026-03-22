"""
Repository Analyzer Agent — deep and shallow analysis using LLM.
Extracts architecture patterns, components, routes, and design briefs.
"""

from __future__ import annotations

import logging
from typing import Optional, Callable, cast

from pipeline.core.llm import invoke_with_retry
from pipeline.core.models import (
    RepoManifest,
    DesignBrief,
    ScreenSpec,
    NavigationType,
)

logger = logging.getLogger("pipeline.analyzer")


# ── Deep Analysis (with source files) ────────────────────────────────────

async def analyze_repo_deep(
    manifest: RepoManifest,
    source_files: dict[str, str],
) -> Optional[dict]:
    """
    Perform deep analysis of a repo using its actual source code.
    Returns a dict matching DeepAnalysis model fields.
    """
    # Build a condensed view of the source files
    file_summary = _build_file_summary(source_files)

    prompt = f"""Analyze this web application's source code for mobile conversion.

## Repository
- Name: {manifest.name}
- Category: {manifest.category.value}
- Description: {manifest.description}
- Stars: {manifest.stars}

## Source Files
{file_summary}

## Analysis Required
Return a JSON object with these exact fields:
{{
  "detected_framework": "string — the web framework (Next.js, React, Vue, etc.)",
  "detected_patterns": ["list of architecture patterns found (MVC, component-based, etc.)"],
  "key_components": ["list of main UI components found"],
  "routes_found": ["list of route/page paths"],
  "state_management": "how state is managed (Redux, Zustand, Context, Vuex, etc.)",
  "api_endpoints": ["list of API routes or external API calls"],
  "styling_approach": "CSS modules, Tailwind, styled-components, etc.",
  "data_models": ["key data types/interfaces found"],
  "accessibility_notes": ["any a11y patterns or issues noted"],
  "performance_considerations": ["caching, SSR, lazy loading, etc."],
  "complexity_score": 1-10,
  "conversion_notes": "specific notes about converting this to mobile",
    "extracted_theme": {{
    "primary_color": "hex code",
    "secondary_color": "hex code",
    "background_color": "hex code",
    "brand_font": "string (e.g. Inter, Roboto, or generic)",
    "style_vibe": "minimal, vibrant, dark, professional, etc.",
    "glassmorphism": "boolean",
    "gradients": ["list of gradient colors found"],
    "border_radius": "number (default 8)"
  }},
  "ui_patterns": ["list of common UI patterns found like cards, glassmorphism, etc."],
  "readiness_score": 1-10,
  "critical_roadblocks": ["list of structural issues that might block conversion"]
}}

Be thorough but concise. 
Focus on 'Elite' mobile conversion: 
- Identify opportunities for micro-interactions.
- Flag any web patterns that should be COMPLETELY REINVENTED for a premium touch experience.
- Brainstorm a high-end mobile-first theme that honors the brand but feels native to iOS/Android.
"""

    result = await invoke_with_retry(
        prompt=prompt,
        stage="deep_analysis",
        heavy=True,
        parse_json=True,
    )

    if result:
        logger.info(f"Deep analysis complete for {manifest.name}: "
                    f"framework={result.get('detected_framework', '?')}, "
                    f"complexity={result.get('complexity_score', '?')}")
    return result


def _build_file_summary(source_files: dict[str, str], max_chars: int = 80_000) -> str:
    """Build a condensed summary of source files for LLM context."""
    parts = []
    total: int = 0

    # Priority: config files, then pages/routes, then components, then others
    priority_order: list[Callable[[str], bool]] = [
        lambda p: p == "package.json",
        lambda p: "config" in p.lower(),
        lambda p: any(d in p for d in ["pages/", "app/", "routes/"]),
        lambda p: any(d in p for d in ["components/", "views/", "screens/"]),
        lambda p: any(d in p for d in ["store/", "stores/", "state/"]),
        lambda p: any(d in p for d in ["api/", "services/", "lib/"]),
        lambda p: True,  # everything else
    ]

    added = set()
    for priority_fn in priority_order:
        for path, content in sorted(source_files.items()):
            if path in added:
                continue
            if not priority_fn(path):
                continue
            if total >= max_chars:
                break

            # Truncate large files
            if len(content) > 3000:
                content = cast(str, content)[:3000] + "\n... (truncated)"

            entry = f"\n### {path}\n```\n{content}\n```\n"
            parts.append(entry)
            total += len(entry)
            added.add(path)

        if total >= max_chars:
            break

    return "".join(parts)


# ── Shallow Analysis (metadata only) ─────────────────────────────────────

async def analyze_repo_shallow(manifest: RepoManifest) -> Optional[DesignBrief]:
    """
    Perform shallow analysis using only repo metadata.
    Used when source files are unavailable.
    """
    prompt = f"""Design a mobile app based on this web project's metadata.

## Repository
- Name: {manifest.name}
- Category: {manifest.category.value}
- Description: {manifest.description}
- Stars: {manifest.stars}
- Language: {manifest.language}
- Features: {', '.join(manifest.features)}

## Task
Create a mobile app design brief. Return JSON:
{{
  "app_name": "human-readable mobile app name",
  "tagline": "one-line description",
  "screens": [
    {{
      "name": "ScreenName",
      "purpose": "what this screen does",
      "components": ["list", "of", "UI", "components"],
      "data_sources": ["what data this screen needs"]
    }}
  ],
  "primary_color": "#hex color that fits the app theme",
  "navigation_type": "tabs|stack|drawer",
  "key_features": ["list of main features"],
  "accessibility_requirements": ["key a11y requirements"],
  "performance_targets": {{
    "initial_load_ms": 2000,
    "interaction_delay_ms": 100,
    "bundle_size_mb": 15
  }},
  "extracted_theme": {{
    "primary_color": "hex code",
    "secondary_color": "hex code",
    "background_color": "hex code",
    "brand_font": "string",
    "style_vibe": "minimal, vibrant, etc.",
    "glassmorphism": "boolean",
    "gradients": ["list of colors"]
  }},
  "readiness_score": 1-10,
  "critical_roadblocks": ["list of missing info that might block design"]
}}

Design 3-8 screens appropriate for the category. Be creative but practical."""

    result = await invoke_with_retry(
        prompt=prompt,
        stage="shallow_analysis",
        heavy=True,
        parse_json=True,
    )

    if not result:
        return _fallback_design_brief(manifest)

    try:
        screens = [
            ScreenSpec(
                name=s.get("name", f"Screen{i}"),
                purpose=s.get("purpose", ""),
                components=s.get("components", []),
                data_sources=s.get("data_sources", []),
            )
            for i, s in enumerate(result.get("screens", []))
        ]

        nav_map = {"tabs": NavigationType.TABS, "stack": NavigationType.STACK, "drawer": NavigationType.DRAWER}

        brief = DesignBrief(
            app_name=result.get("app_name", manifest.name),
            tagline=result.get("tagline", manifest.description),
            screens=screens,
            primary_color=result.get("primary_color", "#2563EB"),
            navigation_type=nav_map.get(
                result.get("navigation_type", "tabs"),
                NavigationType.TABS
            ),
            key_features=result.get("key_features", []),
            accessibility_requirements=result.get("accessibility_requirements", []),
            performance_targets=result.get("performance_targets", {}),
            extracted_theme=result.get("extracted_theme", {}),
            readiness_score=result.get("readiness_score", 5),
            critical_roadblocks=result.get("critical_roadblocks", []),
        )
        return brief

    except Exception as e:
        logger.error(f"Failed to parse design brief: {e}")
        return _fallback_design_brief(manifest)


def _fallback_design_brief(manifest: RepoManifest) -> DesignBrief:
    """Generate a minimal design brief when LLM analysis fails."""
    category = manifest.category.value

    # Category-based screen templates
    screen_templates = {
        "portfolio": [
            ScreenSpec(name="Home", purpose="Landing/hero screen", components=["Header", "HeroSection", "FeaturedWork"]),
            ScreenSpec(name="Projects", purpose="Portfolio gallery", components=["ProjectGrid", "FilterBar", "ProjectCard"]),
            ScreenSpec(name="ProjectDetail", purpose="Single project view", components=["ImageCarousel", "Description", "TechStack"]),
            ScreenSpec(name="About", purpose="Bio/about section", components=["Avatar", "Bio", "Skills", "Timeline"]),
            ScreenSpec(name="Contact", purpose="Contact form", components=["ContactForm", "SocialLinks", "Map"]),
        ],
        "webapp": [
            ScreenSpec(name="Home", purpose="Main dashboard", components=["Header", "StatsCards", "RecentActivity"]),
            ScreenSpec(name="List", purpose="Item listing", components=["SearchBar", "FilterChips", "ItemList"]),
            ScreenSpec(name="Detail", purpose="Item detail view", components=["DetailHeader", "Content", "Actions"]),
            ScreenSpec(name="Settings", purpose="App settings", components=["SettingsGroup", "Toggle", "Select"]),
        ],
        "game": [
            ScreenSpec(name="Menu", purpose="Main menu", components=["Logo", "PlayButton", "SettingsButton"]),
            ScreenSpec(name="Game", purpose="Game screen", components=["GameCanvas", "ScoreDisplay", "Controls"]),
            ScreenSpec(name="GameOver", purpose="Results screen", components=["Score", "HighScores", "PlayAgain"]),
            ScreenSpec(name="Leaderboard", purpose="Rankings", components=["LeaderboardList", "PlayerRank"]),
        ],
    }

    screens = screen_templates.get(category, screen_templates["webapp"])

    return DesignBrief(
        app_name=manifest.name.replace("-", " ").title(),
        tagline=manifest.description or f"Mobile version of {manifest.name}",
        screens=screens,
        primary_color="#2563EB",
        navigation_type=NavigationType.TABS,
        key_features=["Responsive design", "Dark mode", "Offline support"],
    )
