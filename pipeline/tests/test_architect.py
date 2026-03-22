"""Tests for pipeline.agents.architect — architecture design."""


from pipeline.agents.architect import (
    design_architecture,
    _select_framework,
    _select_navigation,
    _route_to_screen_name,
)
from pipeline.core.models import (
    RepoManifest,
    RepoCategory,
    MobileFramework,
    NavigationType,
)


class TestFrameworkSelection:
    def test_portfolio_gets_expo(self, sample_manifest):
        fw = _select_framework(sample_manifest)
        assert fw == MobileFramework.EXPO

    def test_webapp_gets_react_native(self, sample_manifest_webapp):
        fw = _select_framework(sample_manifest_webapp)
        assert fw == MobileFramework.REACT_NATIVE


class TestNavigationSelection:
    def test_portfolio_gets_tabs(self, sample_manifest):
        nav = _select_navigation(sample_manifest)
        assert nav == NavigationType.TABS

    def test_dashboard_gets_drawer(self):
        m = RepoManifest(
            name="test-dashboard",
            github_url="https://github.com/u/test",
            description="Dashboard",
            category=RepoCategory.DASHBOARD,
        )
        nav = _select_navigation(m)
        assert nav == NavigationType.DRAWER


class TestRouteToScreenName:
    def test_root_route(self):
        assert _route_to_screen_name("/") == "Home"

    def test_simple_route(self):
        assert _route_to_screen_name("/about") == "About"

    def test_nested_route(self):
        assert _route_to_screen_name("/blog/posts") == "BlogPosts"

    def test_dynamic_route_stripped(self):
        name = _route_to_screen_name("/projects/[id]")
        assert name == "Projects"

    def test_colon_param_segment_stripped(self):
        assert _route_to_screen_name("/posts/:slug") == "Posts"

    def test_404_route_maps_to_not_found(self):
        assert _route_to_screen_name("/404") == "NotFound"


class TestDesignArchitecture:
    def test_full_design(self, sample_manifest, sample_deep_analysis):
        arch = design_architecture(
            manifest=sample_manifest,
            deep_analysis=sample_deep_analysis,
        )
        assert arch.framework == MobileFramework.EXPO
        assert len(arch.screens) > 0
        assert arch.state_management == "zustand"
        assert arch.design_tokens is True

    def test_design_without_analysis(self, sample_manifest):
        arch = design_architecture(manifest=sample_manifest)
        assert arch.framework == MobileFramework.EXPO
        assert len(arch.screens) >= 3  # Minimum fallback screens
