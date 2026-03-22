"""
Shared test fixtures and configuration.
"""

import pytest
import os

# Ensure test environment
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
os.environ.setdefault("GITHUB_TOKEN", "test-gh-token")
os.environ.setdefault("GITLAB_TOKEN", "test-gl-token")


@pytest.fixture
def sample_manifest():
    """Create a sample RepoManifest for testing."""
    from pipeline.core.models import RepoManifest, RepoCategory
    return RepoManifest(
        name="test-portfolio",
        github_url="https://github.com/user/test-portfolio",
        description="A test portfolio website",
        category=RepoCategory.PORTFOLIO,
        stars=42,
        language="TypeScript",
        topics=["portfolio", "react", "nextjs"],
    )


@pytest.fixture
def sample_manifest_webapp():
    from pipeline.core.models import RepoManifest, RepoCategory
    return RepoManifest(
        name="test-webapp",
        github_url="https://github.com/user/test-webapp",
        description="A complex web application",
        category=RepoCategory.WEBAPP,
        stars=150,
        language="TypeScript",
        topics=["webapp", "react", "dashboard"],
    )


@pytest.fixture
def sample_source_files():
    """Sample source files as would be extracted from a repo."""
    return {
        "package.json": '{"name": "test-app", "dependencies": {"next": "14.0.0", "react": "18.2.0"}}',
        "src/app/page.tsx": 'export default function Home() { return <div>Hello</div>; }',
        "src/app/about/page.tsx": 'export default function About() { return <div>About</div>; }',
        "src/app/projects/page.tsx": 'export default function Projects() { return <div>Projects</div>; }',
        "src/components/Header.tsx": 'export function Header() { return <header>Nav</header>; }',
        "src/components/Footer.tsx": 'export function Footer() { return <footer>Footer</footer>; }',
        "tsconfig.json": '{"compilerOptions": {"strict": true}}',
        "README.md": "# Test App\nA portfolio website.",
    }


@pytest.fixture
def sample_deep_analysis():
    from pipeline.core.models import DeepAnalysis
    return DeepAnalysis(
        detected_framework="Next.js",
        detected_patterns=["component-based", "file-based-routing", "SSR"],
        key_components=["Header", "Footer", "ProjectCard", "ContactForm"],
        routes_found=["/", "/about", "/projects", "/contact"],
        state_management="React Context",
        api_endpoints=["/api/contact"],
        styling_approach="Tailwind CSS",
        data_models=["Project", "ContactForm"],
        complexity_score=5,
        conversion_notes="Standard Next.js portfolio, straightforward conversion.",
    )


@pytest.fixture
def sample_architecture():
    from pipeline.core.models import (
        MobileArchitecture, MobileFramework, NavigationType, ScreenSpec,
    )
    return MobileArchitecture(
        framework=MobileFramework.EXPO,
        navigation_type=NavigationType.TABS,
        screens=[
            ScreenSpec(name="Home", purpose="Landing screen", components=["HeroSection", "FeaturedWork"]),
            ScreenSpec(name="Projects", purpose="Portfolio gallery", components=["ProjectGrid", "FilterBar"]),
            ScreenSpec(name="About", purpose="Bio section", components=["Avatar", "Bio", "Skills"]),
            ScreenSpec(name="Contact", purpose="Contact form", components=["ContactForm", "SocialLinks"]),
            ScreenSpec(name="Settings", purpose="App settings", components=["ThemeToggle", "AboutApp"]),
        ],
        state_management="zustand",
        navigation_library="expo-router",
        dependencies={"expo": "~52.0.0", "react": "18.3.1"},
        design_tokens=True,
        accessibility_level="AA",
    )


@pytest.fixture
def sample_generated_files(sample_architecture):
    """Minimal set of generated files for testing."""
    return {
        "package.json": '{"name": "test-app", "version": "1.0.0"}',
        "tsconfig.json": '{"compilerOptions": {"strict": true}}',
        "app.json": '{"expo": {"name": "Test App"}}',
        "README.md": "# Test App\n" + "Mobile app content.\n" * 60,
        "src/theme/index.ts": "export const colors = {};",
        "src/screens/HomeScreen.tsx": "export function HomeScreen() { return null; }",
        "src/screens/ProjectsScreen.tsx": "export function ProjectsScreen() { return null; }",
        "src/screens/AboutScreen.tsx": "export function AboutScreen() { return null; }",
        "src/screens/ContactScreen.tsx": "export function ContactScreen() { return null; }",
        "src/screens/SettingsScreen.tsx": "export function SettingsScreen() { return null; }",
        "app/_layout.tsx": "export default function Layout() {}",
        "app/(tabs)/_layout.tsx": "export default function TabLayout() {}",
        "app/(tabs)/index.tsx": "export default function Home() {}",
        "src/components/LoadingSpinner.tsx": "export function LoadingSpinner() {}",
        "src/components/ErrorBoundary.tsx": "export class ErrorBoundary {}",
        "src/store/index.ts": "export const useAppStore = () => {};",
        "src/services/api.ts": "export const api = {};",
        "src/types/index.ts": "export type RootStackParamList = {};",
        ".gitignore": "node_modules/",
        ".gitlab-ci.yml": "image: node:20\nstages: [test]\ntest:\n  script: npm test",
        "babel.config.js": "module.exports = {};",
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM invoke function."""
    async def _mock(*args, **kwargs):
        return {"mock": "response"}
    return _mock
