"""
Mobile Architecture Agent — designs the mobile app architecture.
Maps web patterns to mobile equivalents, selects frameworks and navigation.
"""

from __future__ import annotations

import logging
from typing import Optional

from pipeline.core.models import (
    RepoManifest,
    DeepAnalysis,
    DesignBrief,
    MobileArchitecture,
    MobileFramework,
    NavigationType,
    ScreenSpec,
)

logger = logging.getLogger("pipeline.architect")


# ── Framework Selection ───────────────────────────────────────────────────

CATEGORY_FRAMEWORK_MAP = {
    "portfolio": MobileFramework.EXPO,
    # Web apps/dashboards often benefit from native modules + more complex navigation
    "webapp": MobileFramework.REACT_NATIVE,
    "dashboard": MobileFramework.REACT_NATIVE,
    "game": MobileFramework.EXPO,
    "tool": MobileFramework.EXPO,
    "ecommerce": MobileFramework.EXPO,
    "social": MobileFramework.EXPO,
    "blog": MobileFramework.EXPO,
    "docs": MobileFramework.EXPO,
    "api": MobileFramework.EXPO,
}

FRAMEWORK_STATE_MAP = {
    MobileFramework.EXPO: "zustand",
    MobileFramework.REACT_NATIVE: "zustand",
}

FRAMEWORK_NAVIGATION_MAP = {
    MobileFramework.EXPO: "expo-router",
    MobileFramework.REACT_NATIVE: "@react-navigation/native",
}


# ── Architecture Designer ─────────────────────────────────────────────────

def design_architecture(
    manifest: RepoManifest,
    deep_analysis: Optional[DeepAnalysis] = None,
    design_brief: Optional[DesignBrief] = None,
) -> MobileArchitecture:
    """
    Design the mobile architecture for a repo based on analysis results.
    Uses deep analysis when available, falls back to design brief or heuristics.
    """
    # 1. Select framework
    framework = _select_framework(manifest, deep_analysis)

    # 2. Determine navigation type
    nav_type = _select_navigation(manifest, design_brief, deep_analysis)

    # 3. Build screen list
    screens = _build_screens(manifest, deep_analysis, design_brief)

    # 4. Select state management
    state_mgmt = FRAMEWORK_STATE_MAP.get(framework, "zustand")

    # 5. Select navigation library
    nav_lib = FRAMEWORK_NAVIGATION_MAP.get(framework, "expo-router")

    # 6. Determine dependencies
    dependencies = _build_dependencies(framework, screens, nav_type)

    # 7. Build architecture
    arch = MobileArchitecture(
        framework=framework,
        navigation_type=nav_type,
        screens=screens,
        state_management=state_mgmt,
        navigation_library=nav_lib,
        dependencies=dependencies,
        design_tokens=True,
        accessibility_level="AA",
    )

    logger.info(
        f"Architecture designed for {manifest.name}: "
        f"{framework.value}, {nav_type.value}, "
        f"{len(screens)} screens, state={state_mgmt}"
    )

    return arch


def _select_framework(
    manifest: RepoManifest,
    deep_analysis: Optional[DeepAnalysis] = None,
) -> MobileFramework:
    """Select the best mobile framework based on analysis."""
    category = manifest.category.value

    # If deep analysis found a complex SPA, use React Native
    if deep_analysis:
        complexity = deep_analysis.complexity_score
        # Complex apps → React Native (bare workflow)
        if complexity and complexity >= 7:
            return MobileFramework.REACT_NATIVE

    # Default: use category mapping
    return CATEGORY_FRAMEWORK_MAP.get(category, MobileFramework.EXPO)


def _select_navigation(
    manifest: RepoManifest,
    design_brief: Optional[DesignBrief] = None,
    deep_analysis: Optional[DeepAnalysis] = None,
) -> NavigationType:
    """Select navigation pattern based on app structure."""
    if design_brief and design_brief.navigation_type:
        return design_brief.navigation_type

    # Heuristics based on screen count and category
    category = manifest.category.value

    if category in ("portfolio", "blog", "docs"):
        return NavigationType.TABS

    if category in ("ecommerce", "social"):
        return NavigationType.TABS

    if category == "dashboard":
        return NavigationType.DRAWER

    # If many routes found, drawer navigation
    if deep_analysis and len(deep_analysis.routes_found) > 8:
        return NavigationType.DRAWER

    return NavigationType.TABS


def _build_screens(
    manifest: RepoManifest,
    deep_analysis: Optional[DeepAnalysis] = None,
    design_brief: Optional[DesignBrief] = None,
) -> list[ScreenSpec]:
    """Build the screen list from analysis results."""
    if design_brief and design_brief.screens:
        return design_brief.screens

    if deep_analysis:
        return _screens_from_deep_analysis(deep_analysis, manifest)

    # Minimal fallback
    return [
        ScreenSpec(name="Home", purpose="Main landing screen", components=["Header", "Content"]),
        ScreenSpec(name="Detail", purpose="Detail view", components=["DetailView", "Actions"]),
        ScreenSpec(name="Settings", purpose="App settings", components=["SettingsForm"]),
    ]


def _screens_from_deep_analysis(
    analysis: DeepAnalysis,
    manifest: RepoManifest,
) -> list[ScreenSpec]:
    """Convert deep analysis routes/components into screens."""
    screens = []

    # Convert routes to screens
    for route in analysis.routes_found[:10]:
        name = _route_to_screen_name(route)
        screens.append(ScreenSpec(
            name=name,
            purpose=f"Mobile equivalent of {route}",
            components=_infer_components(name, analysis),
        ))

    # Ensure minimum screens
    if not screens:
        screens = [
            ScreenSpec(name="Home", purpose="Main screen", components=["Header", "Content"]),
        ]

    # Always add a Settings screen if not present
    if not any(s.name.lower() == "settings" for s in screens):
        screens.append(ScreenSpec(
            name="Settings",
            purpose="App settings and preferences",
            components=["SettingsGroup", "ThemeToggle", "AboutSection"],
        ))

    return screens


def _route_to_screen_name(route: str) -> str:
    """Convert a URL route to a screen name."""
    if route == "/" or route == "":
        return "Home"

    cleaned = route.strip().lower()
    if cleaned in ("/404", "404"):
        return "NotFound"

    # Clean up the route
    parts = []
    for p in route.strip("/").split("/"):
        if not p:
            continue
        # Drop dynamic segments (Next.js `[id]`, Express-style `:id`, splats, etc.)
        if p.startswith("[") or p.startswith(":") or p in ("*", "**"):
            continue
        # Remove non-alphanumeric characters for identifier safety
        safe = "".join(ch for ch in p if ch.isalnum())
        if safe:
            parts.append(safe)

    if not parts:
        return "Home"

    # PascalCase the parts
    name = "".join(p.capitalize() for p in parts)
    # Ensure identifier starts with a letter
    if not name or not name[0].isalpha():
        return "Home"
    return name


def _infer_components(screen_name: str, analysis: DeepAnalysis) -> list[str]:
    """Infer likely components for a screen based on its name."""
    name_lower = screen_name.lower()

    component_map = {
        "home": ["HeroSection", "FeaturedContent", "QuickActions"],
        "about": ["Avatar", "Bio", "Timeline", "Skills"],
        "contact": ["ContactForm", "SocialLinks"],
        "projects": ["ProjectGrid", "FilterBar", "SearchInput"],
        "blog": ["ArticleList", "CategoryFilter", "SearchBar"],
        "settings": ["SettingsGroup", "ThemeToggle", "ProfileEditor"],
        "profile": ["Avatar", "ProfileInfo", "ActivityFeed"],
        "dashboard": ["StatsCards", "ChartView", "RecentActivity"],
        "detail": ["DetailHeader", "ContentBody", "ActionButtons"],
        "login": ["LoginForm", "SocialLogin", "ForgotPassword"],
        "register": ["RegisterForm", "TermsCheckbox"],
        "search": ["SearchBar", "FilterChips", "ResultsList"],
        "cart": ["CartItems", "PriceSummary", "CheckoutButton"],
    }

    for key, components in component_map.items():
        if key in name_lower:
            return components

    # Default components
    return ["Header", "ContentSection", "ActionBar"]


def _build_dependencies(
    framework: MobileFramework,
    screens: list[ScreenSpec],
    nav_type: NavigationType,
) -> dict[str, str]:
    """Build the dependency map for the architecture."""
    deps = {}

    if framework == MobileFramework.EXPO:
        deps.update({
            "expo": "~52.0.0",
            "expo-router": "~4.0.0",
            "expo-status-bar": "~2.0.0",
            "expo-splash-screen": "~0.29.0",
            "expo-font": "~13.0.0",
            "react": "18.3.1",
            "react-native": "0.76.6",
            "zustand": "^4.5.0",
            "lucide-react-native": "^0.460.0",
            "lucide": "^0.460.0",
            "react-native-svg": "15.8.0",
            "react-native-web": "~0.19.13",
            "react-dom": "18.3.1",
            "@expo/metro-runtime": "~4.0.0",
            "react-native-safe-area-context": "4.12.0",
            "react-native-screens": "~4.4.0",
            "react-native-reanimated": "~3.16.0",
            "react-native-gesture-handler": "~2.20.0",
        })

    # React Native bare dependencies
    elif framework == MobileFramework.REACT_NATIVE:
        deps.update({
            "react": "18.3.1",
            "react-native": "0.76.6",
            "@react-navigation/native": "^7.0.0",
            "@react-navigation/native-stack": "^7.0.0",
            "react-native-screens": "~4.4.0",
            "react-native-safe-area-context": "4.14.1",
            "react-native-reanimated": "~3.16.0",
            "react-native-gesture-handler": "~2.20.0",
            "zustand": "^4.5.0",
            "react-native-vector-icons": "^10.0.0",
        })
        if nav_type == NavigationType.TABS:
            deps["@react-navigation/bottom-tabs"] = "^7.0.0"
        elif nav_type == NavigationType.DRAWER:
            deps["@react-navigation/drawer"] = "^7.0.0"

    return deps
