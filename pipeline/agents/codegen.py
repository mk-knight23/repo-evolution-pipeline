"""
Code Generation Agent — generates complete mobile app source code.
Produces screens, navigation, config files, and project scaffolding.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional, cast

from pipeline.core.llm import invoke_with_retry  # type: ignore
from pipeline.core.models import (  # type: ignore
    RepoManifest,
    MobileArchitecture,
    MobileFramework,
    DeepAnalysis,
    ScreenSpec,
)
from pipeline.core.context import ProjectContextManager  # type: ignore
from pipeline.agents.ci_templates import get_ci_template  # type: ignore
from pipeline.templates.design_system.tokens import generate_theme_file  # type: ignore

logger = logging.getLogger("pipeline.codegen")


# ── Main Code Generation ─────────────────────────────────────────────────

async def generate_mobile_code(
    manifest: RepoManifest,
    architecture: MobileArchitecture,
    source_files: Optional[dict[str, str]] = None,
    deep_analysis: Optional[DeepAnalysis] = None,
) -> dict[str, str]:
    """
    Generate complete mobile app code based on architecture design.
    Returns dict mapping file paths to file contents.
    """
    files: dict[str, str] = {}
    fw = architecture.framework

    logger.info(f"Generating {fw.value} code for {manifest.name} "
               f"({len(architecture.screens)} screens)")

    # Initialize context manager for deep dependency analysis
    ctx_manager = ProjectContextManager(source_files or {})

    # 1. Project config files
    files.update(_generate_config_files(manifest, architecture))

    # 1.5 CI (required for quality gates; also used by GitLab push)
    files[".gitlab-ci.yml"] = get_ci_template(architecture.framework)

    # 2. Theme / Design system
    if fw in (MobileFramework.EXPO, MobileFramework.REACT_NATIVE):
        overrides = deep_analysis.extracted_theme if deep_analysis else None
        files["src/theme/index.ts"] = generate_theme_file(overrides=overrides)

    # 3. Navigation setup
    files.update(_generate_navigation(architecture))

    # 4. Screen files (LLM-powered when source available)
    for screen in architecture.screens:
        screen_files = await _generate_screen(
            screen=screen,
            architecture=architecture,
            manifest=manifest,
            source_files=source_files,
            deep_analysis=deep_analysis,
            ctx_manager=ctx_manager,
        )
        files.update(screen_files)

    # 5. Shared components
    files.update(_generate_shared_components(architecture))

    # 5.5 Polyfills for Web APIs
    files.update(_generate_polyfills(architecture, deep_analysis))

    # 6. Store / State management
    store_files = await _generate_store(architecture, manifest, deep_analysis, source_files, ctx_manager)
    files.update(store_files)

    # 7. API service layer
    files.update(_generate_api_service(manifest, architecture))

    # 7.5 Sanitization (Enterprise V4.0)
    if architecture.data_sanitization_enabled:
        files["src/utils/sanitization.ts"] = _generate_sanitization_util()

    # 8. App entry point
    files.update(_generate_app_entry(manifest, architecture))

    # 9. Type definitions
    files.update(_generate_types(manifest, architecture, deep_analysis))

    # 10. README
    files["README.md"] = _generate_readme(manifest, architecture)

    # 11. Architecture docs (required by quality gates; helps humans)
    files["ARCHITECTURE.md"] = _generate_architecture_doc(manifest, architecture)

    logger.info(f"Generated {len(files)} files, "
               f"{sum(len(c) for c in files.values())} chars total")

    return files


# ── Config File Generation ────────────────────────────────────────────────

def _generate_config_files(
    manifest: RepoManifest,
    arch: MobileArchitecture,
) -> dict[str, str]:
    """Generate project configuration files."""
    files = {}
    fw = arch.framework
    app_name = manifest.name.replace("-", "").replace("_", "").lower()

    if fw in (MobileFramework.EXPO, MobileFramework.REACT_NATIVE):
        # package.json
        pkg = {
            "name": manifest.name,
            "version": "1.0.0",
            "description": f"Mobile app evolved from {manifest.github_url}",
            "main": "index.js",
            "scripts": {
                "start": "expo start",
                "mobile:dev": "expo start --web",
                "mobile:dev:hardened": "mkdir -p .expo-cache .npm-cache && export HOME=$(pwd)/.expo-cache && npm start -- --web",
                "android": "expo start --android",
                "ios": "expo start --ios",
                "web": "expo start --web",
                "test": "jest --passWithNoTests",
                "lint": "eslint src/ --ext .ts,.tsx",
                "type-check": "tsc --noEmit",
            },
            "dependencies": {
                **arch.dependencies,
                "expo": "~55.0.5",
                "react": "^19.2.3",
                "react-dom": "^19.2.3",
                "react-native": "0.84.1",
                "react-native-reanimated": "~4.2.2",
                "react-native-worklets": "~0.7.2",
                "react-native-safe-area-context": "5.7.0",
                "react-native-web": "~0.21.2",
                "@expo/metro-runtime": "~55.0.6",
            },
            "devDependencies": {
                "typescript": "^5.7.3",
                "@types/react": "~19.0.0",
                "eslint": "^9.0.0",
                "eslint-config-expo": "^9.2.0",
                "jest": "^29.7.0",
                "prettier": "^3.0.0",
            },
        }
        files["package.json"] = json.dumps(pkg, indent=2)

        # tsconfig.json
        files["tsconfig.json"] = json.dumps({
            "compilerOptions": {
                "strict": True,
                "jsx": "react-native",
                "moduleResolution": "bundler",
                "esModuleInterop": True,
                "allowSyntheticDefaultImports": True,
                "paths": {"@/*": ["./src/*"]},
                "baseUrl": ".",
                "skipLibCheck": True,
                "target": "esnext",
            },
            "include": ["src/**/*.ts", "src/**/*.tsx", "app/**/*.ts", "app/**/*.tsx", "index.js", "App.tsx"],
            "exclude": ["node_modules", "dist", "build"],
        }, indent=2)

        if fw == MobileFramework.EXPO:
            files["app.json"] = json.dumps({
                "expo": {
                    "name": manifest.name.replace("-", " ").title(),
                    "slug": manifest.name,
                    "version": "1.0.0",
                    "orientation": "portrait",
                    "icon": "./assets/icon.png",
                    "scheme": app_name,
                    "userInterfaceStyle": "automatic",
                    "splash": {
                        "image": "./assets/splash.png",
                        "resizeMode": "contain",
                        "backgroundColor": "#ffffff",
                    },
                    "assetBundlePatterns": ["**/*"],
                    "ios": {"supportsTablet": True, "bundleIdentifier": f"com.evolved.{app_name}"},
                    "android": {
                        "adaptiveIcon": {"foregroundImage": "./assets/adaptive-icon.png", "backgroundColor": "#ffffff"},
                        "package": f"com.evolved.{app_name}",
                    },
                    "web": {"favicon": "./assets/favicon.png", "bundler": "metro"},
                    "plugins": ["expo-router", "expo-font"],
                },
            }, indent=2)

            # Assets (Minimal valid PNG placeholders to avoid "Jimp" errors)
            # 1x1 Transparent PNG base64
            dot_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            files["assets/icon.png"] = dot_png
            files["assets/splash.png"] = dot_png
            files["assets/adaptive-icon.png"] = dot_png
            files["assets/favicon.png"] = dot_png

    if arch.eas_enabled:
        files["eas.json"] = json.dumps({
            "cli": { "version": ">= 12.0.0" },
            "build": {
                "development": { "developmentClient": True, "distribution": "internal" },
                "preview": { "distribution": "internal" },
                "production": {}
            },
            "submit": { "production": {} }
        }, indent=2)

    files[".gitignore"] = """node_modules/
dist/
build/
.expo/
.expo-cache/
.npm-cache/
*.apk
*.aab
*.ipa
.env
.env.local
coverage/
*.log
.DS_Store
# EAS
bin-android/
bin-ios/
"""


    files["babel.config.js"] = """module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: ['react-native-reanimated/plugin'],
  };
};
"""

    # ESLint (ESLint v9 flat config). Use `.mjs` to avoid needing `"type": "module"`.
    files["eslint.config.mjs"] = """import { defineConfig } from 'eslint-config-expo/flat.js';

export default defineConfig({
  ignores: ['node_modules/**', 'dist/**', 'build/**', '.expo/**'],
  extends: ['expo'],
});
"""

    return files


# ── Navigation Generation ─────────────────────────────────────────────────

def _generate_navigation(arch: MobileArchitecture) -> dict[str, str]:
    """Generate navigation structure."""
    files = {}
    fw = arch.framework

    if fw == MobileFramework.EXPO:
        # Expo Router uses file-based routing
        files["app/_layout.tsx"] = _expo_root_layout(arch)
        files["app/(tabs)/_layout.tsx"] = _expo_tabs_layout(arch)

        for screen in arch.screens:
            route_name = screen.name.lower()
            if route_name == "home":
                files["app/(tabs)/index.tsx"] = _expo_screen_route(screen)
            else:
                files[f"app/(tabs)/{route_name}.tsx"] = _expo_screen_route(screen)

    elif fw == MobileFramework.REACT_NATIVE:
        files["src/navigation/AppNavigator.tsx"] = _rn_navigator(arch)

    return files


def _expo_root_layout(arch: MobileArchitecture) -> str:
    return """import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useTheme } from '@/theme';

export default function RootLayout() {
  const { colors, isDark } = useTheme();

  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.surface },
          headerTintColor: colors.textPrimary,
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      </Stack>
    </>
  );
}
"""


def _expo_tabs_layout(arch: MobileArchitecture) -> str:
    tabs = []
    icons = {"home": "home", "projects": "briefcase", "about": "user",
             "contact": "mail", "settings": "settings", "search": "search",
             "profile": "user", "detail": "file-text",
             "blog": "book", "dashboard": "bar-chart", "cart": "shopping-cart"}

    for screen in arch.screens:
        name = screen.name.lower()
        icon = icons.get(name, "circle")
        route = "index" if name == "home" else name
        tabs.append(f"""        <Tabs.Screen
          name="{route}"
          options={{{{
            title: '{screen.name}',
            tabBarIcon: ({{ color, size }}) => (
              <Icon name="{icon}" size={{size}} color={{color}} />
            ),
          }}}}
        />""")

    tabs_str = "\n".join(tabs)

    return f"""import {{ Tabs }} from 'expo-router';
import {{ Home, Briefcase, Settings, User, BarChart, Circle, Mail, Search, FileText, Book, ShoppingCart }} from 'lucide-react-native';
import {{ useTheme }} from '@/theme';

export default function TabLayout() {{
  const {{ colors }} = useTheme();

  // Helper to render icons dynamically
  const Icon = ({{ name, size, color }}: {{ name: string, size: number, color: string }}) => {{
    switch (name) {{
      case 'home': return <Home size={{size}} color={{color}} />;
      case 'briefcase': return <Briefcase size={{size}} color={{color}} />;
      case 'settings': return <Settings size={{size}} color={{color}} />;
      case 'user': return <User size={{size}} color={{color}} />;
      case 'bar-chart': return <BarChart size={{size}} color={{color}} />;
      case 'mail': return <Mail size={{size}} color={{color}} />;
      case 'search': return <Search size={{size}} color={{color}} />;
      case 'file-text': return <FileText size={{size}} color={{color}} />;
      case 'book': return <Book size={{size}} color={{color}} />;
      case 'shopping-cart': return <ShoppingCart size={{size}} color={{color}} />;
      default: return <Circle size={{size}} color={{color}} />;
    }}
  }};

  return (
    <Tabs
      screenOptions={{{{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textTertiary,
        tabBarStyle: {{ backgroundColor: colors.surface, borderTopColor: colors.border }},
        headerStyle: {{ backgroundColor: colors.surface }},
        headerTintColor: colors.textPrimary,
      }}}}
    >
{tabs_str}
    </Tabs>
  );
}}
"""


def _expo_screen_route(screen: ScreenSpec) -> str:
    return f"""import {{ View }} from 'react-native';
import {{ {screen.name}Screen }} from '@/screens/{screen.name}Screen';

export default function {screen.name}Route() {{
  return <{screen.name}Screen />;
}}
"""


def _rn_navigator(arch: MobileArchitecture) -> str:
    imports = [f"import {{ {s.name}Screen }} from '@/screens/{s.name}Screen';" for s in arch.screens]
    screens = [f"        <Tab.Screen name=\"{s.name}\" component={{{s.name}Screen}} />" for s in arch.screens]

    return f"""import React from 'react';
import {{ NavigationContainer }} from '@react-navigation/native';
import {{ createBottomTabNavigator }} from '@react-navigation/bottom-tabs';
import {{ useTheme }} from '@/theme';
{chr(10).join(imports)}

const Tab = createBottomTabNavigator();

export default function AppNavigator() {{
  const {{ colors }} = useTheme();

  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={{{{
          tabBarActiveTintColor: colors.primary,
          tabBarStyle: {{ backgroundColor: colors.surface }},
        }}}}
      >
{chr(10).join(screens)}
      </Tab.Navigator>
    </NavigationContainer>
  );
}}
"""


# ── Screen Generation ─────────────────────────────────────────────────────

async def _generate_screen(
    screen: ScreenSpec,
    architecture: MobileArchitecture,
    manifest: RepoManifest,
    source_files: Optional[dict[str, str]] = None,
    deep_analysis: Optional[DeepAnalysis] = None,
    ctx_manager: Optional[ProjectContextManager] = None,
) -> dict[str, str]:
    """Generate a single screen with LLM assistance when source is available."""
    files = {}
    fw = architecture.framework

    if fw in (MobileFramework.EXPO, MobileFramework.REACT_NATIVE):
        # Always use LLM for screen generation to ensure premium, non-templated UI
        # Pass 1: Generation (from source if available, otherwise from spec)
        if source_files and deep_analysis:
            content = await _llm_generate_screen(
                screen, 
                architecture, 
                source_files, 
                manifest,
                ctx_manager=ctx_manager
            )
        else:
            logger.info(f"Generating {screen.name} from spec (no source available)...")
            content = await _llm_generate_screen_from_spec(screen, architecture, manifest)
        
        # Pass 2: Premium Refinement (V3.0)
        if content:
            logger.info(f"Refining {screen.name} for elite mobile UI/UX...")
            content = await _refine_screen(content, screen, architecture, deep_analysis)
        
        if content:
            files[f"src/screens/{screen.name}Screen.tsx"] = content
            return files

        # Final absolute fallback if LLM completely fails (unlikely with our chain)
        files[f"src/screens/{screen.name}Screen.tsx"] = _template_screen_tsx(screen, architecture)

    return files


async def _llm_generate_screen(
    screen: ScreenSpec,
    arch: MobileArchitecture,
    source_files: dict[str, str],
    manifest: RepoManifest,
    ctx_manager: Optional[ProjectContextManager] = None,
) -> Optional[str]:
    """Use LLM to generate a screen component from source code."""
    relevant_sources: dict[str, str] = {}
    orig_file = getattr(screen, "original_file", "")
    
    # 1. Primary Context: Deep dependency tracing
    if ctx_manager and orig_file:
        relevant_sources = ctx_manager.get_relevant_context(orig_file, max_depth=1)
    
    # 2. RAG Context: Semantic Search (Phase D Upgrade)
    if ctx_manager:
        query = f"{screen.name} {screen.purpose} {' '.join(screen.components)}"
        rag_results = ctx_manager.search_context(query, top_k=3)
        for path, content in rag_results.items():
            if not relevant_sources.get(path):  # type: ignore
                relevant_sources.update({path: content})  # type: ignore

    # 3. Fallback: Simple name-based matching
    if not relevant_sources:
        relevant_sources = _find_relevant_sources(screen, source_files)
    
    if not relevant_sources:
        return None

    # Sort sources to put the primary file first
    sorted_sources = list(relevant_sources.items())
    if orig_file in relevant_sources:
        sorted_sources.sort(key=lambda x: x[0] != orig_file)

    source_context = "\n".join(
        f"### {path}\n```\n{cast(str, content)[:4000]}\n```"  # type: ignore
        for path, content in sorted_sources[:5]  # type: ignore
    )

    prompt = f"""You are a World-Class Mobile Developer. 
Convert this web component/page to a React Native screen using EXTREME AUTHORITY.

## Target Screen: {screen.name}
Purpose: {screen.purpose}
Components needed: {', '.join(screen.components)}

## Original Web Source (Reference Only)
{source_context}

## Authority Guidelines
- DO NOT just port the code. REINVENT it for an elite touch-driven experience.
- Use high-fidelity layouts, smooth animations (Ready for Reanimated), and modern typography.
- Use StyleSheet.create() for styles.
- Make it accessible and production-ready.
- Export as named export: export function {screen.name}Screen()

Generate ONLY the TypeScript/React Native code. No explanations."""

    result = await invoke_with_retry(
        prompt=prompt,
        stage="screen_generation",
        heavy=True,
        parse_json=False,
    )

    if result and "export" in result:
        # Clean up — remove markdown fences if present
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return result

    return None


async def _llm_generate_screen_from_spec(
    screen: ScreenSpec,
    arch: MobileArchitecture,
    manifest: RepoManifest,
) -> Optional[str]:
    """Generate a screen entirely from the architecture spec (no source context)."""
    prompt = f"""You are a Silicon Valley Mobile Design Lead. 
Create an ELITE mobile screen from the following specification.

## Screen Metadata
- Name: {screen.name}
- Purpose: {screen.purpose}
- Core Components: {', '.join(screen.components)}

## App Context
- App Name: {manifest.name}
- Category: {manifest.category.value}

## Design Authority
- Do not use templates. Brainstorm a unique, high-conversion mobile UI.
- Use Lucide icons (lucide-react-native).
- Implement specialized 'Elite' mobile patterns (Action Sheets, Floating Action Buttons, Glass cards).
- Export as named export: export function {screen.name}Screen()

Generate ONLY the TypeScript/React Native code. No explanations."""

    result = await invoke_with_retry(
        prompt=prompt,
        stage="screen_spec_generation",
        heavy=True,
        parse_json=False,
        include_practices=["expo", "premium_ui", "authority"]
    )
    
    if result and "export" in result:
        # Clean up — remove markdown fences if present
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return result

    return None


async def _refine_screen(
    initial_code: str,
    screen: ScreenSpec,
    arch: MobileArchitecture,
    deep_analysis: DeepAnalysis,
) -> str:
    """Implement a second LLM pass to 'Premium-ize' the generated code."""
    style_info = deep_analysis.extracted_theme
    has_glass = style_info.get("glassmorphism", False)
    
    prompt = f"""Refine this React Native screen to be absolute ELITE and PREMIUM.
    
    ## Initial Code
    ```tsx
    {initial_code}
    ```
    
    ## Styling Metadata
    - Style Vibe: {style_info.get('style_vibe', 'premium-modern')}
    - Glassmorphism Requested: {has_glass}
    - Gradients: {style_info.get('gradients', [])}
    
    ## Authority Refinement
    1. Apply Premium UI: Use BlurView (expo-blur) and Glassmorphism techniques.
    2. Add Fluid Animations: Use react-native-reanimated for layout transitions and interaction feedback.
    3. Haptic Feedback: Add expo-haptics for button presses.
    4. Advanced Clean Code: Ensure generic types are used where appropriate.
    
    Generate ONLY the improved TypeScript/React Native code. No markdown fences."""

    practices = ["expo", "performance"]
    if has_glass or "vibrant" in style_info.get("style_vibe", ""):
        practices.append("premium_ui")

    result = await invoke_with_retry(
        prompt=prompt,
        stage="screen_refinement",
        heavy=True,
        parse_json=False,
        include_practices=practices
    )

    if result and "export" in result:
        # Clean up — remove markdown fences if present
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return result

    return initial_code


def _find_relevant_sources(screen: ScreenSpec, source_files: dict[str, str]) -> dict[str, str]:
    """Find source files relevant to a specific screen."""
    relevant = {}
    name_lower = screen.name.lower()

    for path, content in source_files.items():
        path_lower = path.lower()
        # Match by screen name in path
        if name_lower in path_lower:
            relevant[path] = content
        # Match by component names
        elif any(comp.lower() in path_lower for comp in screen.components):
            relevant[path] = content
        # Match by original_file if listed
        elif getattr(screen, "original_file", "") and getattr(screen, "original_file", "") in path:
            relevant[path] = content

    return dict(cast(list, list(relevant.items()))[:8])  # type: ignore


def _template_screen_tsx(screen: ScreenSpec, arch: MobileArchitecture) -> str:
    """Generate a template-based React Native screen with responsive design."""
    components_jsx = "\n".join(
        f"        <View style={{[styles.section, {{ backgroundColor: colors.card, ...shadows.sm }}]}}>\n"
        f"          <Text style={{[styles.sectionTitle, {{ color: colors.textPrimary }}]}}>{comp}</Text>\n"
        f"          <Text style={{[styles.placeholder, {{ color: colors.textSecondary }}]}}>{{/* Implement {comp} */}}</Text>\n"
        f"        </View>"
        for comp in screen.components
    )

    return f"""import React from 'react';
import {{ View, Text, ScrollView, StyleSheet, RefreshControl, useWindowDimensions }} from 'react-native';
import {{ useTheme }} from '@/theme';

export function {screen.name}Screen() {{
  const {{ colors, typography, spacing, shadows }} = useTheme();
  const {{ width }} = useWindowDimensions();
  const isTablet = width >= 768;
  
  const [refreshing, setRefreshing] = React.useState(false);

  const onRefresh = React.useCallback(() => {{
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 1500);
  }}, []);

  return (
    <ScrollView
      style={{[styles.container, {{ backgroundColor: colors.background }}]}}
      contentContainerStyle={{[styles.content, isTablet && styles.contentTablet]}}
      refreshControl={{
        <RefreshControl refreshing={{refreshing}} onRefresh={{onRefresh}} tintColor={{colors.primary}} />
      }}
      accessibilityLabel="{screen.name} screen"
    >
      <View style={{styles.header}}>
        <Text
          style={{[styles.title, {{ color: colors.textPrimary }}]}}
          accessibilityRole="header"
        >
          {screen.name}
        </Text>
        <Text style={{[styles.subtitle, {{ color: colors.textSecondary }}]}}>
          {screen.purpose}
        </Text>
      </View>

      <View style={{isTablet && styles.gridContainer}}>
{components_jsx}
      </View>
    </ScrollView>
  );
}}

const styles = StyleSheet.create({{
  container: {{ flex: 1 }},
  content: {{ padding: 16 }},
  contentTablet: {{ paddingHorizontal: 40, alignSelf: 'center', width: '100%', maxWidth: 1024 }},
  header: {{ marginBottom: 24 }},
  title: {{ ...typography.h1, marginBottom: 4 }},
  subtitle: {{ ...typography.body }},
  gridContainer: {{ flexDirection: 'row', flexWrap: 'wrap', gap: 16, justifyContent: 'space-between' }},
  section: {{ marginBottom: 20, padding: 16, borderRadius: 12, minWidth: 280, flex: 1 }},
  sectionTitle: {{ ...typography.subtitle, marginBottom: 8 }},
  placeholder: {{ ...typography.caption }},
}});
"""





# ── Shared Components ─────────────────────────────────────────────────────

def _generate_shared_components(arch: MobileArchitecture) -> dict[str, str]:
    """Generate reusable shared components."""
    files = {}

    if arch.framework in (MobileFramework.EXPO, MobileFramework.REACT_NATIVE):
        files["src/components/LoadingSpinner.tsx"] = """import React from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { useTheme } from '@/theme';

interface Props {
  size?: 'small' | 'large';
}

export function LoadingSpinner({ size = 'large' }: Props) {
  const { colors } = useTheme();
  return (
    <View style={styles.container} accessibilityLabel="Loading">
      <ActivityIndicator size={size} color={colors.primary} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
});
"""

        files["src/components/ErrorBoundary.tsx"] = """import React, { Component, ErrorInfo, ReactNode } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

interface Props { children: ReactNode; }
interface State { hasError: boolean; error?: Error; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.container} accessibilityRole="alert">
          <Text style={styles.title}>Something went wrong</Text>
          <Text style={styles.message}>{this.state.error?.message}</Text>
          <TouchableOpacity
            style={styles.button}
            onPress={() => this.setState({ hasError: false })}
            accessibilityLabel="Try again"
          >
            <Text style={styles.buttonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      );
    }
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { fontSize: 20, fontWeight: '700', marginBottom: 8, color: '#DC2626' },
  message: { fontSize: 14, color: '#64748B', marginBottom: 20, textAlign: 'center' },
  button: { backgroundColor: '#2563EB', paddingHorizontal: 24, paddingVertical: 12, borderRadius: 8 },
  buttonText: { color: '#fff', fontWeight: '600' },
});
"""

        files["src/components/Card.tsx"] = """import React, { ReactNode } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { useTheme } from '@/theme';

interface Props {
  children: ReactNode;
  style?: ViewStyle;
}

export function Card({ children, style }: Props) {
  const { colors, shadows } = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: colors.card, ...shadows.md }, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 12, padding: 16, marginBottom: 12 },
});
"""

    return files


def _generate_polyfills(arch: MobileArchitecture, deep_analysis: Optional[DeepAnalysis]) -> dict[str, str]:
    """Generate polyfills for web APIs like localStorage."""
    files = {}
    if arch.framework in (MobileFramework.EXPO, MobileFramework.REACT_NATIVE):
        files["src/utils/storageShim.ts"] = """import AsyncStorage from '@react-native-async-storage/async-storage';

// In-memory fallback to avoid async/await issues in existing synchronous code
const memoryCache: Record<string, string> = {};

// Load existing data on startup
AsyncStorage.getAllKeys().then(keys => {
  AsyncStorage.multiGet(keys).then(results => {
    results.forEach(([key, val]) => {
      if (val !== null) memoryCache[key] = val;
    });
  });
});

export const localStorageShim = {
  getItem: (key: string): string | null => memoryCache[key] || null,
  setItem: (key: string, value: string) => {
    memoryCache[key] = value;
    AsyncStorage.setItem(key, value).catch(console.error);
  },
  removeItem: (key: string) => {
    delete memoryCache[key];
    AsyncStorage.removeItem(key).catch(console.error);
  },
  clear: () => {
    for (const key in memoryCache) delete memoryCache[key];
    AsyncStorage.clear().catch(console.error);
  }
};
"""
    return files

# ── Store Generation ──────────────────────────────────────────────────────

async def _generate_store(
    arch: MobileArchitecture, 
    manifest: RepoManifest,
    deep_analysis: Optional[DeepAnalysis] = None,
    source_files: Optional[dict[str, str]] = None,
    ctx_manager: Optional[ProjectContextManager] = None
) -> dict[str, str]:
    """Generate state management store. Attempts LLM translation if complex web state found."""
    files = {}

    if arch.framework in (MobileFramework.EXPO, MobileFramework.REACT_NATIVE):
        # Determine if we should attempt LLM state translation
        state_approach = getattr(deep_analysis, "state_management", "").lower()
        
        should_use_llm = False
        context_str = ""
        
        if source_files and ("redux" in state_approach or "vuex" in state_approach or "context" in state_approach):
            should_use_llm = True
            # Find relevant state files
            state_files = {k: cast(str, v)[:5000] for k, v in source_files.items() if "store" in k.lower() or "slice" in k.lower() or "context" in k.lower() or "reducer" in k.lower()}  # type: ignore
            if state_files:
                context_str = "\n".join(f"### {p}\n```ts\n{c}\n```" for p, c in cast(list, list(state_files.items()))[:3])  # type: ignore
            else:
                should_use_llm = False

        if should_use_llm and context_str:
            logger.info("Translating web state to Zustand store via LLM...")
            prompt = f"""You are a World-Class Mobile Developer.
Translate the following web state management logic into a React Native Zustand store.

## Web State Context
{context_str}

## Requirements
- Create a comprehensive Zustand store (`useAppStore`).
- Implement the core business logic found in the reducers/actions.
- Combine multiple slices into one main store if appropriate, or create standard slices.
- Use TypeScript interfaces.
- Export as `export const useAppStore = create...`

Generate ONLY the TypeScript code for `src/store/index.ts`. No explanations. No markdown fences."""
            
            result = await invoke_with_retry(
                prompt=prompt,
                stage="store_generation",
                heavy=True,
                parse_json=False,
            )
            
            if result and "export const" in result:
                if result.startswith("```"):
                    lines = result.split("\n")
                    result = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                files["src/store/index.ts"] = result
                
                # Add AsyncStorage dependency
                if arch.dependencies is not None:
                    arch.dependencies["@react-native-async-storage/async-storage"] = "~1.23.1"
                
                return files

        # Fallback to generic store
        files["src/store/index.ts"] = f"""import {{ create }} from 'zustand';

interface UserProfile {{
  name: string;
  email: string;
  avatar: string;
}}

interface UserSettings {{
  theme: 'light' | 'dark';
  notifications: boolean;
}}

interface AppState {{
  // Data
  profile: UserProfile;
  settings: UserSettings;
  updateProfile: (data: Partial<UserProfile>) => void;
  updateSettings: (data: Partial<UserSettings>) => void;

  // Theme
  isDarkMode: boolean;
  toggleDarkMode: () => void;

  // Loading states
  isLoading: boolean;
  setLoading: (loading: boolean) => void;

  // Error handling
  error: string | null;
  setError: (error: string | null) => void;
  clearError: () => void;
}}

export const useAppStore = create<AppState>((set) => ({{
  // Defaults
  profile: {{
    name: '{manifest.name.replace('-', ' ').title()}',
    email: 'user@example.com',
    avatar: 'https://images.unsplash.com/photo-1633332755192-727a05c4013d?w=400',
  }},
  settings: {{
    theme: 'light',
    notifications: true,
  }},

  isDarkMode: false,
  toggleDarkMode: () => set((state) => ({{ 
    isDarkMode: !state.isDarkMode,
    settings: {{ ...state.settings, theme: !state.isDarkMode ? 'dark' : 'light' }}
  }})),

  updateProfile: (data) => set((state) => ({{ 
    profile: {{ ...state.profile, ...data }} 
  }})),
  
  updateSettings: (data) => set((state) => ({{ 
    settings: {{ ...state.settings, ...data }},
    isDarkMode: data.theme ? data.theme === 'dark' : state.isDarkMode
  }})),

  isLoading: false,
  setLoading: (loading) => set({{ isLoading: loading }}),

  error: null,
  setError: (error) => set({{ error }}),
  clearError: () => set({{ error: null }}),
}}));
"""
    return files


def _generate_api_service(manifest: RepoManifest, arch: MobileArchitecture) -> dict[str, str]:
    """Generate API service layer with optional Enterprise sanitization."""
    files = {}
    base_url = "https://api.example.com"
    if manifest.api_endpoints:
        # Simple extraction of base URL from first endpoint
        import re
        match = re.search(r"https?://[^/]+", manifest.api_endpoints[0])
        if match:
            base_url = match.group(0)

    sanitization_import = "import { sanitizeData } from '@/utils/sanitization';" if arch.data_sanitization_enabled else ""
    sanitization_call = "data = sanitizeData(data);" if arch.data_sanitization_enabled else ""

    files["src/api/client.ts"] = f"""import axios from 'axios';
{sanitization_import}

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || '{base_url}';

export const apiClient = axios.create({{
  baseURL: API_BASE_URL,
  headers: {{
    'Content-Type': 'application/json',
  }},
}});

apiClient.interceptors.request.use((config) => {{
  // Auth token can be attached here (e.g., from Zustand store) if needed.
  return config;
}});

apiClient.interceptors.response.use(
  (response) => {{
    let data = response.data;
    {sanitization_call}
    return {{ ...response, data }};
  }},
  (error) => {{
    return Promise.reject(error);
  }}
);
"""
    return files


def _generate_architecture_doc(manifest: RepoManifest, arch: MobileArchitecture) -> str:
    screens = "\n".join(
        [f"- `{s.name}`: {s.purpose or '—'}" for s in arch.screens]
    ) or "- (none)"

    deps = "\n".join([f"- `{k}`: `{v}`" for k, v in sorted((arch.dependencies or {}).items())]) or "- (none)"

    return f"""# {manifest.name} — Mobile Architecture

This repository is an auto-generated mobile app evolved from:
- Source: {manifest.github_url}

## Stack
- Framework: `{arch.framework.value}`
- Navigation: `{arch.navigation_library}` (`{arch.navigation_type.value}`)
- State: `{arch.state_management}`
- Accessibility target: `{arch.accessibility_level}` (WCAG)

## Screens
{screens}

## Core Dependencies
{deps}

## Notes
- Generated by Repo Evolution Pipeline.
- Design tokens live in `src/theme/index.ts`.
"""


def _generate_sanitization_util() -> str:
    """Enterprise V4.0: GDPR/CCPA Data Sanitization Utility."""
    return """/**
 * Enterprise Data Sanitization & PII Masking
 * Automatically injected for compliance (GDPR/CCPA/SOC2)
 */

export function sanitizeData(data: any): any {
  if (!data) return data;

  if (Array.isArray(data)) {
    return data.map(item => sanitizeData(item));
  }

  if (typeof data === 'object') {
    const sanitized: any = {};
    for (const [key, value] of Object.entries(data)) {
      // PII Masking Keys
      const maskKeys = ['password', 'secret', 'token', 'credit_card', 'ssn', 'social_security'];
      const censorKeys = ['email', 'phone', 'address'];

      if (maskKeys.some(k => key.toLowerCase().includes(k))) {
        sanitized[key] = '********';
      } else if (censorKeys.some(k => key.toLowerCase().includes(k))) {
        sanitized[key] = censorString(String(value), key.toLowerCase());
      } else if (typeof value === 'object') {
        sanitized[key] = sanitizeData(value);
      } else {
        sanitized[key] = value;
      }
    }
    return sanitized;
  }

  return data;
}

function censorString(val: string, type: string): string {
  if (type.includes('email')) {
    const [part1, part2] = val.split('@');
    if (!part2) return val;
    return `${part1[0]}***@${part2}`;
  }
  if (type.includes('phone')) {
    return val.replace(/\\d(?=\\d{4})/g, '*');
  }
  return '***HIDDEN***';
}
"""

# ── App Entry ─────────────────────────────────────────────────────────────

def _generate_app_entry(manifest: RepoManifest, arch: MobileArchitecture) -> dict[str, str]:
    files = {}

    if arch.framework in (MobileFramework.EXPO, MobileFramework.REACT_NATIVE):
        # index.js (Mandatory for newer SDKs when not using AppEntry)
        files["index.js"] = """import { registerRootComponent } from 'expo';
import App from './App';

registerRootComponent(App);
"""

        # App.tsx
        files["App.tsx"] = """import React from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { useTheme } from '@/theme';

// Import root navigation or generated screen
// In a real flow, the architect decides if we use expo-router or custom navigation
export default function App() {
  const { colors } = useTheme();
  
  return (
    <SafeAreaProvider style={{ flex: 1, backgroundColor: colors.background }}>
      <ErrorBoundary>
        {/* The generated code will populate this with the Entry screen */}
      </ErrorBoundary>
    </SafeAreaProvider>
  );
}
"""
    return files


# ── Types ─────────────────────────────────────────────────────────────────

def _generate_types(
    manifest: RepoManifest,
    arch: MobileArchitecture,
    deep_analysis: Optional[DeepAnalysis] = None,
) -> dict[str, str]:
    return {
        "src/types/index.ts": f"""/**
 * Shared type definitions for {manifest.name}
 * Auto-generated by Repo Evolution Pipeline v2.0
 */

// Navigation
export type RootStackParamList = {{
{chr(10).join(f"  {s.name}: undefined;" for s in arch.screens)}
}};

// Common
export interface ApiResponse<T> {{
  data: T;
  error?: string;
  meta?: Record<string, unknown>;
}}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {{
  page: number;
  totalPages: number;
  totalItems: number;
}}
""",
    }


# ── README ────────────────────────────────────────────────────────────────

def _generate_readme(manifest: RepoManifest, arch: MobileArchitecture) -> str:
    screens_list = "\n".join(f"- **{s.name}**: {s.purpose}" for s in arch.screens)

    return f"""# {manifest.name.replace('-', ' ').title()} - Mobile App

> Mobile app evolved from [{manifest.name}]({manifest.github_url})

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | {arch.framework.value} |
| Navigation | {arch.navigation_library} |
| State | {arch.state_management} |
| Styling | Design Tokens + StyleSheet |

## Screens

{screens_list}

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm start

# Run on iOS
npm run ios

# Run on Android
npm run android
```

## Project Structure

```
src/
  screens/       # Screen components
  components/    # Shared UI components
  theme/         # Design tokens & theme
  store/         # State management
  services/      # API & external services
  types/         # TypeScript definitions
```

## Quality

- TypeScript strict mode
- ESLint + Prettier
- WCAG {arch.accessibility_level} accessibility
- Error boundaries
- Pull-to-refresh

---

*Generated by [Repo Evolution Pipeline v2.0](https://gitlab.com) — transforming web to mobile*
"""
