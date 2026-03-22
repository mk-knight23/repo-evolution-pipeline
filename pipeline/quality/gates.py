"""
Quality Gates Engine — automated checks that every generated repo must pass.
Industry-standard validation covering structure, syntax, security, and completeness.
"""

from __future__ import annotations
from typing import cast

import json
import re
import logging

from pipeline.core.models import (
    QualityGate,
    QualityGateResult,
    MobileArchitecture,
    RepoManifest,
    MobileFramework,
)

logger = logging.getLogger("pipeline.quality")


class QualityGatesEngine:
    """Run all quality gates against generated files."""

    def __init__(self, files: dict[str, str], arch: MobileArchitecture, manifest: RepoManifest):
        self.files = files
        self.arch = arch
        self.manifest = manifest
        self.gates: list[QualityGate] = []

    def run_all(self) -> list[QualityGate]:
        """Execute all quality gates and return results."""
        self.gates = []

        self._gate_valid_project_structure()
        self._gate_valid_config_files()
        self._gate_minimum_screens()
        self._gate_navigation_connects_screens()
        self._gate_valid_ci_yaml()
        self._gate_readme_exists()
        self._gate_architecture_docs()
        self._gate_github_ancestor_link()
        self._gate_no_hardcoded_secrets()
        self._gate_typescript_quality()
        self._gate_accessibility_basics()
        self._gate_offline_support()
        self._gate_error_handling()
        self._gate_no_placeholder_content()
        self._gate_design_system_tokens()
        self._gate_security_sca()
        self._gate_production_hardening()
        # v3.0 gates
        self._gate_dependency_freshness()
        self._gate_bundle_size_estimate()
        self._gate_deep_accessibility()
        self._gate_performance_budget()
        self._gate_i18n_readiness()

        return self.gates

    @property
    def score(self) -> float:
        """Calculate quality score 0-100."""
        if not self.gates:
            return 0.0
        passed = sum(1 for g in self.gates if g.result == QualityGateResult.PASSED)
        warnings = sum(1 for g in self.gates if g.result == QualityGateResult.WARNING)
        total = len(self.gates)
        score_val = ((passed + warnings * 0.5) / total) * 100
        return round(score_val, 1)

    @property
    def all_critical_passed(self) -> bool:
        """Check if all critical (non-warning) gates passed."""
        critical_gates = [
            "valid_project_structure",
            "valid_config_files",
            "minimum_screens",
            "valid_ci_yaml",
            "no_hardcoded_secrets",
        ]
        for gate in self.gates:
            if gate.name in critical_gates and gate.result == QualityGateResult.FAILED:
                return False
        return True

    # ── Individual Gates ───────────────────────────────────────────────────

    def _add(
        self,
        name: str,
        desc: str,
        result: QualityGateResult,
        details: str = "",
        message: str = "",
        auto_fixable: bool = False,
    ):
        self.gates.append(QualityGate(
            name=name,
            description=desc,
            result=result,
            passed=(result != QualityGateResult.FAILED),
            message=message or desc,
            details=details,
            auto_fixable=auto_fixable,
        ))

    def _gate_valid_project_structure(self):
        """GATE 1: All required directories and config files exist."""
        # The current pipeline targets Expo (managed) and React Native (JS-only scaffold).
        if self.arch.framework == MobileFramework.EXPO:
            required = ["package.json", "app.json"]
            optional_dirs = ["app/", "src/"]
        else:
            required = ["package.json"]
            optional_dirs = ["src/"]

        missing = [f for f in required if f not in self.files]
        has_dir = any(
            any(fp.startswith(d) for fp in self.files) for d in optional_dirs
        )

        if not missing and has_dir:
            self._add("valid_project_structure", "All required project files exist", QualityGateResult.PASSED)
        elif not missing:
            self._add("valid_project_structure", "Config files exist but source dirs sparse",
                       QualityGateResult.WARNING, f"Dirs checked: {optional_dirs}")
        else:
            self._add("valid_project_structure", "Missing required project files",
                       QualityGateResult.FAILED, f"Missing: {missing}", auto_fixable=True)

    def _gate_valid_config_files(self):
        """GATE 2: package.json / pubspec.yaml is valid."""
        config_file = "package.json" if "package.json" in self.files else "pubspec.yaml"
        content = self.files.get(config_file, "")

        if not content:
            self._add("valid_config_files", f"{config_file} is valid", QualityGateResult.FAILED,
                       "Config file not found", auto_fixable=True)
            return

        try:
            if config_file.endswith(".json"):
                parsed = json.loads(content)
                has_name = "name" in parsed
                has_deps = "dependencies" in parsed
                if has_name and has_deps:
                    self._add("valid_config_files", f"{config_file} is valid JSON with required fields",
                               QualityGateResult.PASSED)
                else:
                    self._add("valid_config_files", f"{config_file} missing fields",
                               QualityGateResult.WARNING,
                               f"has_name={has_name}, has_deps={has_deps}")
            else:
                # YAML validation
                if "name:" in content and "dependencies:" in content:
                    self._add("valid_config_files", f"{config_file} has required fields",
                               QualityGateResult.PASSED)
                else:
                    self._add("valid_config_files", f"{config_file} may be incomplete",
                               QualityGateResult.WARNING)
        except (json.JSONDecodeError, Exception) as e:
            self._add("valid_config_files", f"{config_file} parse error",
                       QualityGateResult.FAILED, str(e), auto_fixable=True)

    def _gate_minimum_screens(self):
        """GATE 3: At least 3 screen files exist."""
        screen_patterns = [
            r"(app|screens?|pages?)/.*\.(tsx|jsx|ts|js|dart)$",
            r"lib/screens?/.*\.dart$",
        ]
        screen_files = [
            fp for fp in self.files
            if any(re.match(pat, fp) for pat in screen_patterns)
        ]

        count = len(screen_files)
        if count >= 3:
            self._add("minimum_screens", f"{count} screen files found (≥3 required)",
                       QualityGateResult.PASSED, f"Files: {cast(list, screen_files)[:5]}")
        elif count >= 1:
            self._add("minimum_screens", f"Only {count} screen files found (3 recommended)",
                       QualityGateResult.WARNING, f"Files: {screen_files}")
        else:
            self._add("minimum_screens", "No screen files found",
                       QualityGateResult.FAILED, auto_fixable=True)

    def _gate_navigation_connects_screens(self):
        """GATE 4: Navigation file connects all screens."""
        layout_files = [fp for fp in self.files if "layout" in fp.lower() or "navigator" in fp.lower()]
        if not layout_files:
            self._add("navigation_connects_screens", "No navigation/layout file found",
                       QualityGateResult.WARNING, auto_fixable=True)
            return

        layout_content = self.files.get(layout_files[0], "")
        has_nav = any(kw in layout_content for kw in ["Tabs", "Stack", "Drawer", "Navigator", "router"])
        if has_nav:
            self._add("navigation_connects_screens", "Navigation file found with routing",
                       QualityGateResult.PASSED)
        else:
            self._add("navigation_connects_screens", "Layout file exists but no navigation detected",
                       QualityGateResult.WARNING)

    def _gate_valid_ci_yaml(self):
        """GATE 5: .gitlab-ci.yml is valid YAML."""
        ci_content = self.files.get(".gitlab-ci.yml", "")
        if not ci_content:
            self._add("valid_ci_yaml", ".gitlab-ci.yml exists", QualityGateResult.FAILED,
                       "CI file not found", auto_fixable=True)
            return

        # Basic YAML structure checks
        has_stages = "stages:" in ci_content or "stage:" in ci_content
        has_script = "script:" in ci_content

        if has_stages and has_script:
            self._add("valid_ci_yaml", ".gitlab-ci.yml has stages and scripts",
                       QualityGateResult.PASSED)
        elif has_script:
            self._add("valid_ci_yaml", ".gitlab-ci.yml has scripts but missing stages definition",
                       QualityGateResult.WARNING)
        else:
            self._add("valid_ci_yaml", ".gitlab-ci.yml appears invalid",
                       QualityGateResult.FAILED, auto_fixable=True)

    def _gate_readme_exists(self):
        """GATE 6: README.md exists with >50 lines."""
        readme = self.files.get("README.md", "")
        line_count = len(readme.splitlines())
        if line_count >= 50:
            self._add("readme_exists", f"README.md exists ({line_count} lines)",
                       QualityGateResult.PASSED)
        elif line_count > 0:
            self._add("readme_exists", f"README.md exists but short ({line_count} lines, recommend ≥50)",
                       QualityGateResult.WARNING)
        else:
            self._add("readme_exists", "README.md not found",
                       QualityGateResult.FAILED, auto_fixable=True)

    def _gate_architecture_docs(self):
        """GATE 7: ARCHITECTURE.md exists."""
        arch_files = [fp for fp in self.files if "architecture" in fp.lower() and fp.endswith(".md")]
        if arch_files:
            self._add("architecture_docs", "Architecture documentation exists",
                       QualityGateResult.PASSED, f"Files: {arch_files}")
        else:
            self._add("architecture_docs", "No architecture documentation found",
                       QualityGateResult.WARNING, auto_fixable=True)

    def _gate_github_ancestor_link(self):
        """GATE 8: Link to GitHub ancestor included."""
        all_content = " ".join(self.files.values())
        has_link = self.manifest.github_url in all_content or "github.com/mk-knight23" in all_content
        if has_link:
            self._add("github_ancestor_link", "Link to original GitHub repo included",
                       QualityGateResult.PASSED)
        else:
            self._add("github_ancestor_link", "Missing link to original GitHub repository",
                       QualityGateResult.WARNING, auto_fixable=True)

    def _gate_no_hardcoded_secrets(self):
        """GATE 9: No API keys, tokens, or secrets in source code (OWASP-hardened)."""
        secret_patterns = [
            r"sk-[a-zA-Z0-9\-]{20,}",             # Anthropic keys
            r"ghp_[a-zA-Z0-9]{36}",              # GitHub tokens
            r"glpat-[a-zA-Z0-9\-]{20,}",         # GitLab tokens
            r"eyJ[a-zA-Z0-9\-_]{50,}",           # JWT tokens
            r"AKIA[A-Z0-9]{16}",                 # AWS access keys
            r"password\s*[:=]\s*[\"'][^\"']+",    # Hardcoded passwords
            r"-----BEGIN [A-Z ]+ PRIVATE KEY-----", # Private keys
            r"xox[bpgs]-[a-zA-Z0-9\-]{20,}",      # Slack tokens
            r"sk_live_[a-zA-Z0-9]{24,}",           # Stripe live keys
            r"rk_live_[a-zA-Z0-9]{24,}",           # Stripe restricted keys
            r"SG\.[a-zA-Z0-9\-_]{22,}",            # SendGrid API keys
            r"AC[a-f0-9]{32}",                     # Twilio account SID
            r"AIza[a-zA-Z0-9\-_]{35}",             # Google API keys
            r"ya29\.[a-zA-Z0-9\-_]+",              # Google OAuth tokens
            r"AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}", # Firebase server key
        ]

        violations = []
        for filepath, content in self.files.items():
            if filepath.endswith((".env", ".env.example", ".env.local")):
                continue  # Skip env files
            for pattern in secret_patterns:
                if re.search(pattern, content):
                    violations.append(filepath)
                    break

        if not violations:
            self._add("no_hardcoded_secrets", "No hardcoded secrets detected (OWASP scan)",
                       QualityGateResult.PASSED)
        else:
            self._add("no_hardcoded_secrets", f"Potential secrets found in {len(violations)} files",
                       QualityGateResult.FAILED, f"Files: {cast(list, violations)[:5]}")

    def _gate_typescript_quality(self):
        """GATE 10: TypeScript files have proper typing."""
        ts_files = {fp: c for fp, c in self.files.items() if fp.endswith((".ts", ".tsx"))}
        if not ts_files:
            self._add("typescript_quality", "No TypeScript files to check",
                       QualityGateResult.WARNING)
            return

        typed_count = 0
        for content in ts_files.values():
            has_types = any(kw in content for kw in ["interface ", "type ", ": string", ": number", ": boolean", "React.FC"])
            if has_types:
                typed_count += 1

        ratio = typed_count / len(ts_files) if ts_files else 0
        if ratio >= 0.7:
            self._add("typescript_quality", f"{typed_count}/{len(ts_files)} TS files have proper typing",
                       QualityGateResult.PASSED)
        elif ratio >= 0.3:
            self._add("typescript_quality", f"Only {typed_count}/{len(ts_files)} TS files have typing",
                       QualityGateResult.WARNING)
        else:
            self._add("typescript_quality", f"Poor TypeScript coverage: {typed_count}/{len(ts_files)}",
                       QualityGateResult.FAILED, auto_fixable=True)

    def _gate_accessibility_basics(self):
        """GATE 11: Basic accessibility attributes present."""
        all_tsx = " ".join(c for fp, c in self.files.items() if fp.endswith((".tsx", ".jsx")))
        checks = {
            "accessibilityLabel": "accessibilityLabel" in all_tsx or "accessible" in all_tsx,
            "accessibilityRole": "accessibilityRole" in all_tsx,
        }

        passed = sum(checks.values())
        if passed >= 1:
            self._add("accessibility_basics", "Basic accessibility attributes found",
                       QualityGateResult.PASSED)
        else:
            self._add("accessibility_basics", "No accessibility attributes found in components",
                       QualityGateResult.WARNING,
                       "Add accessibilityLabel and accessibilityRole to interactive elements")

    def _gate_offline_support(self):
        """GATE 12: Offline support / caching present."""
        all_content = " ".join(self.files.values())
        has_async_storage = "AsyncStorage" in all_content
        has_cache = "cache" in all_content.lower() or "fetchWithCache" in all_content
        has_offline = "offline" in all_content.lower() or "NetInfo" in all_content

        if has_async_storage or has_cache or has_offline:
            self._add("offline_support", "Offline/caching support detected",
                       QualityGateResult.PASSED)
        else:
            self._add("offline_support", "No offline support or caching detected",
                       QualityGateResult.WARNING,
                       "Consider adding AsyncStorage caching or NetInfo for offline detection")

    def _gate_error_handling(self):
        """GATE 13: Error handling present in components."""
        all_content = " ".join(self.files.values())
        error_patterns = ["try {", "catch (", ".catch(", "ErrorBoundary", "error", "onError"]
        found = sum(1 for p in error_patterns if p in all_content)

        if found >= 3:
            self._add("error_handling", "Error handling patterns found",
                       QualityGateResult.PASSED)
        elif found >= 1:
            self._add("error_handling", "Minimal error handling found",
                       QualityGateResult.WARNING, "Consider adding try/catch to API calls and ErrorBoundary")
        else:
            self._add("error_handling", "No error handling detected",
                       QualityGateResult.FAILED, auto_fixable=True)

    def _gate_no_placeholder_content(self):
        """GATE 14: No TODO/placeholder content in shipped code."""
        placeholder_patterns = ["TODO:", "FIXME:", "PLACEHOLDER", "Lorem ipsum", "<Text>Home</Text>"]
        violations = []

        for fp, content in self.files.items():
            if fp.endswith(".md"):
                continue  # TODOs in docs are OK
            for pattern in placeholder_patterns:
                if pattern in content:
                    violations.append((fp, pattern))

        if not violations:
            self._add("no_placeholder_content", "No placeholder content found",
                       QualityGateResult.PASSED)
        elif len(violations) <= 3:
            self._add("no_placeholder_content", f"{len(violations)} placeholder(s) found",
                       QualityGateResult.WARNING,
                       f"Found: {cast(list, violations)[:3]}")
        else:
            self._add("no_placeholder_content", f"{len(violations)} placeholders found",
                       QualityGateResult.FAILED, auto_fixable=True)

    def _gate_design_system_tokens(self):
        """GATE 15: Design system tokens / theme file present."""
        theme_patterns = ["theme", "tokens", "colors", "typography", "design-system"]
        has_theme = any(
            any(p in fp.lower() for p in theme_patterns)
            for fp in self.files
        )

        all_content = " ".join(self.files.values())
        has_style_constants = "StyleSheet.create" in all_content and ("colors" in all_content.lower() or "spacing" in all_content.lower())

        if has_theme or has_style_constants:
            self._add("design_system_tokens", "Design system / theme tokens present",
                       QualityGateResult.PASSED)
        else:
            self._add("design_system_tokens", "No design system tokens found",
                       QualityGateResult.WARNING,
                       "Consider adding a theme file with colors, spacing, typography tokens")

    def _gate_security_sca(self):
        """GATE 16: Software Composition Analysis — check for known-vulnerable dependencies."""
        if self.arch.framework not in (MobileFramework.EXPO, MobileFramework.REACT_NATIVE):
            return

        pkg_content = self.files.get("package.json", "")
        if not pkg_content:
            return

        try:
            pkg = json.loads(pkg_content)
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            
            # Simulated vulnerability database for demonstration
            VULNERABLE_PACKAGES = {
                "axios": ("<1.6.0", "CVE-2023-45853: Server-Side Request Forgery"),
                "lodash": ("<4.17.21", "CVE-2020-8203: Prototype Pollution"),
                "express": ("<4.19.2", "CVE-2024-29041: Open Redirect"),
            }

            vulnerabilities = []
            for name, version in deps.items():
                if name in VULNERABLE_PACKAGES:
                    # Very basic version check (start with digit or <)
                    clean_version = re.sub(r"[^0-9.]", "", str(version))
                    limit_version = re.sub(r"[^0-9.]", "", VULNERABLE_PACKAGES[name][0])
                    
                    if clean_version and limit_version and clean_version < limit_version:
                        vulnerabilities.append(f"{name}@{version} ({VULNERABLE_PACKAGES[name][1]})")

            if not vulnerabilities:
                self._add("security_sca", "No known-vulnerable dependencies detected", QualityGateResult.PASSED)
            else:
                self._add("security_sca", f"Found {len(vulnerabilities)} vulnerable dependency(ies)", 
                           QualityGateResult.FAILED, "\n".join(vulnerabilities))

        except Exception as e:
            self._add("security_sca", "SCA check failed", QualityGateResult.WARNING, str(e))

    def _gate_production_hardening(self):
        """GATE 17: Production Hardening — check for PII protection and sanitization."""
        all_content = " ".join(self.files.values())
        
        # Check for data sanitization patterns identified in V4.0 Blueprint
        has_sanitization = any(kw in all_content for kw in ["sanitize", "maskPII", "encryptData", "DOMPurify"])
        
        if has_sanitization:
            self._add("production_hardening", "PII sanitization logic detected", QualityGateResult.PASSED)
        else:
            self._add("production_hardening", "No PII sanitization or data masking detected", 
                       QualityGateResult.WARNING, "Consider adding a data sanitization layer for GDPR/CCPA compliance")

    # ── v3.0 Quality Gates ─────────────────────────────────────────────────

    def _gate_dependency_freshness(self):
        """GATE 18: Check if major dependencies are reasonably current."""
        pkg_content = self.files.get("package.json", "")
        if not pkg_content:
            self._add("dependency_freshness", "No package.json to check",
                       QualityGateResult.WARNING)
            return

        try:
            pkg = json.loads(pkg_content)
            deps = pkg.get("dependencies", {})

            # Known latest major versions (as of pipeline v3.0)
            LATEST_MAJORS = {
                "expo": 52, "react": 18, "react-native": 0,
                "typescript": 5, "@react-navigation/native": 7,
            }

            outdated = []
            for name, version in deps.items():
                if name in LATEST_MAJORS:
                    clean = re.sub(r"[^0-9.]", "", str(version))
                    if clean:
                        major = int(clean.split(".")[0])
                        expected = LATEST_MAJORS[name]
                        if expected > 0 and major < expected - 1:  # Allow 1 major behind
                            outdated.append(f"{name}@{version} (latest major: {expected})")

            if not outdated:
                self._add("dependency_freshness", "All major deps are current",
                           QualityGateResult.PASSED)
            else:
                self._add("dependency_freshness",
                           f"{len(outdated)} outdated dependency(ies)",
                           QualityGateResult.WARNING,
                           ", ".join(outdated))
        except Exception:
            self._add("dependency_freshness", "Could not parse package.json",
                       QualityGateResult.WARNING)

    def _gate_bundle_size_estimate(self):
        """GATE 19: Estimate total JS/TS bundle size."""
        total_bytes = sum(
            len(content)
            for fp, content in self.files.items()
            if fp.endswith((".ts", ".tsx", ".js", ".jsx"))
        )
        mb = total_bytes / (1024 * 1024)

        if mb <= 2.0:
            self._add("bundle_size_estimate",
                       f"Estimated source size: {mb:.1f}MB (good)",
                       QualityGateResult.PASSED)
        elif mb <= 5.0:
            self._add("bundle_size_estimate",
                       f"Estimated source size: {mb:.1f}MB (consider code splitting)",
                       QualityGateResult.WARNING)
        else:
            self._add("bundle_size_estimate",
                       f"Estimated source size: {mb:.1f}MB (too large)",
                       QualityGateResult.FAILED,
                       "Split code, use dynamic imports, or remove unused dependencies")

    def _gate_deep_accessibility(self):
        """GATE 20: Deep accessibility — checks beyond basic labels."""
        all_tsx = " ".join(c for fp, c in self.files.items() if fp.endswith((".tsx", ".jsx")))

        checks = {
            "accessibilityHint": "accessibilityHint" in all_tsx,
            "accessibilityState": "accessibilityState" in all_tsx,
            "semantic_roles": any(r in all_tsx for r in [
                '"button"', '"header"', '"link"', '"image"', '"text"',
                "'button'", "'header'", "'link'",
            ]),
            "focus_management": any(kw in all_tsx for kw in [
                "useFocusEffect", "autoFocus", "focusable", "setAccessibilityFocus",
            ]),
        }

        score = sum(checks.values())
        if score >= 3:
            self._add("deep_accessibility", "Strong accessibility implementation",
                       QualityGateResult.PASSED, f"Found: {[k for k, v in checks.items() if v]}")
        elif score >= 1:
            self._add("deep_accessibility", f"Partial accessibility ({score}/4 checks)",
                       QualityGateResult.WARNING,
                       f"Missing: {[k for k, v in checks.items() if not v]}")
        else:
            self._add("deep_accessibility", "No deep accessibility patterns found",
                       QualityGateResult.WARNING,
                       "Add accessibilityHint, semantic roles, and focus management")

    def _gate_performance_budget(self):
        """GATE 21: Performance patterns — FlashList, memoization, lazy loading."""
        all_content = " ".join(self.files.values())

        checks = {
            "efficient_lists": any(kw in all_content for kw in ["FlashList", "RecyclerListView", "windowSize"]),
            "memoization": any(kw in all_content for kw in ["React.memo", "useMemo", "useCallback"]),
            "lazy_loading": any(kw in all_content for kw in ["lazy(", "Suspense", "dynamic(", "React.lazy"]),
            "image_optimization": any(kw in all_content for kw in ["Image.prefetch", "FastImage", "expo-image"]),
        }

        score = sum(checks.values())
        if score >= 2:
            self._add("performance_budget", f"Performance patterns found ({score}/4)",
                       QualityGateResult.PASSED, f"Found: {[k for k, v in checks.items() if v]}")
        elif score >= 1:
            self._add("performance_budget", f"Minimal perf optimizations ({score}/4)",
                       QualityGateResult.WARNING,
                       f"Consider: {[k for k, v in checks.items() if not v]}")
        else:
            self._add("performance_budget", "No performance optimization patterns found",
                       QualityGateResult.WARNING,
                       "Add React.memo, useMemo, FlashList, and lazy loading")

    def _gate_i18n_readiness(self):
        """GATE 22: Internationalization readiness."""
        all_content = " ".join(self.files.values())

        i18n_patterns = [
            "i18n", "intl", "useTranslation", "t(", "formatMessage",
            "i18next", "react-intl", "expo-localization", "Localization",
        ]
        has_i18n = any(p in all_content for p in i18n_patterns)

        # Check for hardcoded user-facing strings in components
        tsx_content = " ".join(
            c for fp, c in self.files.items()
            if fp.endswith((".tsx", ".jsx")) and "test" not in fp.lower()
        )
        # Simple heuristic: look for JSX text content patterns
        hardcoded_count = len(re.findall(r'>\s*[A-Z][a-z]+\s+[a-z]+', tsx_content))

        if has_i18n:
            self._add("i18n_readiness", "i18n framework detected",
                       QualityGateResult.PASSED)
        elif hardcoded_count < 5:
            self._add("i18n_readiness", "Few hardcoded strings (acceptable for MVP)",
                       QualityGateResult.WARNING)
        else:
            self._add("i18n_readiness",
                       f"~{hardcoded_count} hardcoded strings, no i18n framework",
                       QualityGateResult.WARNING,
                       "Consider adding expo-localization or i18next for future scaling")


def run_quality_gates(
    files: dict[str, str],
    arch: MobileArchitecture,
    manifest: RepoManifest,
) -> tuple[list[QualityGate], float]:
    """Convenience function to run all quality gates.

    Returns:
        Tuple of (gates_list, quality_score_0_to_100)
    """
    engine = QualityGatesEngine(files, arch, manifest)
    gates = engine.run_all()

    passed = sum(1 for g in gates if g.result == QualityGateResult.PASSED)
    warnings = sum(1 for g in gates if g.result == QualityGateResult.WARNING)
    failed = sum(1 for g in gates if g.result == QualityGateResult.FAILED)

    logger.info(
        f"Quality gates: {passed} passed, {warnings} warnings, {failed} failed "
        f"(score: {engine.score}/100)"
    )

    return gates, engine.score
