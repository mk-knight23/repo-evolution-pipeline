"""
Design System Tokens — shared visual language for ALL generated mobile apps.
Follows the Design Tokens Community Group specification.
Provides consistent colors, typography, spacing, and component styles.
"""

import json
from typing import Optional


# ── Color Tokens ───────────────────────────────────────────────────────────

COLORS = {
    "light": {
        "primary": "#2563EB",        # Blue 600
        "primary_light": "#3B82F6",  # Blue 500
        "primary_dark": "#1D4ED8",   # Blue 700
        "secondary": "#7C3AED",      # Violet 600
        "accent": "#06B6D4",         # Cyan 500
        "success": "#16A34A",        # Green 600
        "warning": "#D97706",        # Amber 600
        "error": "#DC2626",          # Red 600
        "info": "#2563EB",           # Blue 600

        "background": "#FFFFFF",
        "surface": "#F8FAFC",        # Slate 50
        "surface_elevated": "#FFFFFF",
        "card": "#FFFFFF",

        "text_primary": "#0F172A",   # Slate 900
        "text_secondary": "#475569", # Slate 600
        "text_tertiary": "#94A3B8",  # Slate 400
        "text_inverse": "#FFFFFF",
        "text_link": "#2563EB",

        "border": "#E2E8F0",         # Slate 200
        "border_focus": "#2563EB",
        "divider": "#F1F5F9",        # Slate 100

        "overlay": "rgba(0,0,0,0.5)",
        "shadow": "rgba(0,0,0,0.1)",
    },
    "dark": {
        "primary": "#3B82F6",
        "primary_light": "#60A5FA",
        "primary_dark": "#2563EB",
        "secondary": "#8B5CF6",
        "accent": "#22D3EE",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "error": "#EF4444",
        "info": "#3B82F6",

        "background": "#0F172A",     # Slate 900
        "surface": "#1E293B",        # Slate 800
        "surface_elevated": "#334155",# Slate 700
        "card": "#1E293B",

        "text_primary": "#F8FAFC",
        "text_secondary": "#CBD5E1",
        "text_tertiary": "#64748B",
        "text_inverse": "#0F172A",
        "text_link": "#60A5FA",

        "border": "#334155",
        "border_focus": "#3B82F6",
        "divider": "#1E293B",

        "overlay": "rgba(0,0,0,0.7)",
        "shadow": "rgba(0,0,0,0.3)",
    },
    "obsidian": {
        "primary": "#00FFCC",        # Neon Teal
        "primary_light": "#33FFD6",
        "primary_dark": "#00CCAA",
        "secondary": "#7C3AED",
        "accent": "#FF00FF",         # Neon Magenta
        "success": "#00FF66",
        "warning": "#FFCC00",
        "error": "#FF0033",
        "info": "#0099FF",

        "background": "#000000",
        "surface": "#0A0A0A",
        "surface_elevated": "#1A1A1A",
        "card": "#0A0A0A",

        "text_primary": "#FFFFFF",
        "text_secondary": "#A0A0A0",
        "text_tertiary": "#666666",
        "text_inverse": "#000000",
        "text_link": "#00FFCC",

        "border": "#1A1A1A",
        "border_focus": "#00FFCC",
        "divider": "#0F0F0F",

        "overlay": "rgba(0,0,0,0.9)",
        "shadow": "rgba(0,255,204,0.1)",
    },
}

# ── Premium UI Tokens (Glassmorphism & Gradients) ─────────────────────────

GLASSMOKE = {
    "light": {
        "thin": "rgba(255, 255, 255, 0.4)",
        "base": "rgba(255, 255, 255, 0.6)",
        "thick": "rgba(255, 255, 255, 0.8)",
        "border": "rgba(255, 255, 255, 0.5)",
    },
    "dark": {
        "thin": "rgba(15, 23, 42, 0.3)",
        "base": "rgba(15, 23, 42, 0.5)",
        "thick": "rgba(15, 23, 42, 0.7)",
        "border": "rgba(255, 255, 255, 0.1)",
    },
}

GRADIENTS = {
    "primary": ["#2563EB", "#7C3AED"],  # Blue to Violet
    "surface": ["#FFFFFF", "#F8FAFC"],
    "surface_dark": ["#0F172A", "#1E293B"],
    "accent": ["#06B6D4", "#3B82F6"],
    "glass": ["rgba(255, 255, 255, 0.1)", "rgba(255, 255, 255, 0.05)"],
}


# ── Typography Tokens ──────────────────────────────────────────────────────

TYPOGRAPHY = {
    "font_family": {
        "sans": "System",          # Platform default sans-serif
        "mono": "SpaceMono",       # For code blocks
    },
    "font_size": {
        "xs": 11,
        "sm": 13,
        "base": 15,
        "md": 17,
        "lg": 20,
        "xl": 24,
        "2xl": 30,
        "3xl": 36,
        "4xl": 48,
    },
    "font_weight": {
        "regular": "400",
        "medium": "500",
        "semibold": "600",
        "bold": "700",
        "extrabold": "800",
    },
    "line_height": {
        "tight": 1.2,
        "normal": 1.5,
        "relaxed": 1.75,
    },
    "letter_spacing": {
        "tight": -0.5,
        "normal": 0,
        "wide": 0.5,
        "wider": 1.0,
    },
}


# ── Spacing Tokens ─────────────────────────────────────────────────────────

SPACING = {
    "0": 0,
    "xs": 4,
    "sm": 8,
    "md": 12,
    "base": 16,
    "lg": 20,
    "xl": 24,
    "2xl": 32,
    "3xl": 40,
    "4xl": 48,
    "5xl": 64,
}


# ── Border Tokens ──────────────────────────────────────────────────────────

BORDERS = {
    "radius": {
        "none": 0,
        "sm": 4,
        "md": 8,
        "lg": 12,
        "xl": 16,
        "2xl": 24,
        "full": 9999,
    },
    "width": {
        "thin": 0.5,
        "base": 1,
        "medium": 1.5,
        "thick": 2,
    },
}


# ── Shadow / Elevation Tokens ─────────────────────────────────────────────

SHADOWS = {
    "none": {"shadowColor": "transparent", "shadowOffset": {"width": 0, "height": 0}, "shadowOpacity": 0, "shadowRadius": 0, "elevation": 0},
    "sm": {"shadowColor": "#000", "shadowOffset": {"width": 0, "height": 1}, "shadowOpacity": 0.05, "shadowRadius": 2, "elevation": 1},
    "md": {"shadowColor": "#000", "shadowOffset": {"width": 0, "height": 2}, "shadowOpacity": 0.1, "shadowRadius": 4, "elevation": 3},
    "lg": {"shadowColor": "#000", "shadowOffset": {"width": 0, "height": 4}, "shadowOpacity": 0.15, "shadowRadius": 8, "elevation": 5},
    "xl": {"shadowColor": "#000", "shadowOffset": {"width": 0, "height": 8}, "shadowOpacity": 0.2, "shadowRadius": 16, "elevation": 8},
}


# ── Animation / Motion Tokens ─────────────────────────────────────────────

MOTION = {
    "duration": {
        "instant": 100,
        "fast": 200,
        "normal": 300,
        "slow": 500,
        "glacial": 800,
    },
    "easing": {
        "ease_in": "cubic-bezier(0.4, 0, 1, 1)",
        "ease_out": "cubic-bezier(0, 0, 0.2, 1)",
        "ease_in_out": "cubic-bezier(0.4, 0, 0.2, 1)",
        "spring": "cubic-bezier(0.34, 1.56, 0.64, 1)",
    },
}


# ── Icon Sizes ─────────────────────────────────────────────────────────────

ICON_SIZES = {
    "xs": 16,
    "sm": 20,
    "md": 24,
    "lg": 28,
    "xl": 32,
    "2xl": 40,
}


# ── Code Generator ─────────────────────────────────────────────────────────

def generate_theme_file(overrides: Optional[dict[str, str]] = None) -> str:
    """Generate a complete React Native theme TypeScript file with optional color overrides."""
    overrides = overrides or {}
    
    # Extract overrides with fallback to design system constants
    p_light = overrides.get("primary_color", COLORS["light"]["primary"])
    s_light = overrides.get("secondary_color", COLORS["light"]["secondary"])
    b_light = overrides.get("background_color", COLORS["light"]["background"])
    
    p_dark = overrides.get("primary_color_dark", p_light) # Default to light if no specific dark
    s_dark = overrides.get("secondary_color_dark", s_light)
    b_dark = overrides.get("background_color_dark", COLORS["dark"]["background"])

    is_obsidian = overrides.get("style_vibe") == "obsidian"
    active_dark = COLORS["obsidian"] if is_obsidian else COLORS["dark"]

    return f'''/**
 * Design System Tokens — Auto-generated by Repo Evolution Pipeline v2.1
 * Follows Design Tokens Community Group specification.
 *
 * Usage:
 *   import {{ colors, spacing, typography, shadows }} from '@/theme';
 *   <View style={{{{ backgroundColor: colors.background, padding: spacing.base }}}} />
 */

import {{ useColorScheme }} from 'react-native';

// ── Color Palette ─────────────────────────────────────────────────────────

const lightColors = {{
  primary: '{p_light}',
  primaryLight: '{p_light}', // Simplified for overrides
  primaryDark: '{p_light}',
  secondary: '{s_light}',
  accent: '{COLORS["light"]["accent"]}',
  success: '{COLORS["light"]["success"]}',
  warning: '{COLORS["light"]["warning"]}',
  error: '{COLORS["light"]["error"]}',
  info: '{COLORS["light"]["info"]}',

  background: '{b_light}',
  surface: '{COLORS["light"]["surface"]}',
  surfaceElevated: '{COLORS["light"]["surface_elevated"]}',
  card: '{COLORS["light"]["card"]}',

  textPrimary: '{COLORS["light"]["text_primary"]}',
  textSecondary: '{COLORS["light"]["text_secondary"]}',
  textTertiary: '{COLORS["light"]["text_tertiary"]}',
  textInverse: '{COLORS["light"]["text_inverse"]}',
  textLink: '{p_light}',

  border: '{COLORS["light"]["border"]}',
  borderFocus: '{p_light}',
  divider: '{COLORS["light"]["divider"]}',

  overlay: '{COLORS["light"]["overlay"]}',
  shadow: '{COLORS["light"]["shadow"]}',
  white: '#FFFFFF',
  black: '#000000',
}} as const;

const darkColors = {{
  primary: '{p_dark}',
  primaryLight: '{p_dark}',
  primaryDark: '{p_dark}',
  secondary: '{s_dark}',
  accent: '{COLORS["dark"]["accent"]}',
  success: '{COLORS["dark"]["success"]}',
  warning: '{COLORS["dark"]["warning"]}',
  error: '{COLORS["dark"]["error"]}',
  info: '{COLORS["dark"]["info"]}',

  background: '{b_dark}',
  surface: '{COLORS["dark"]["surface"]}',
  surfaceElevated: '{COLORS["dark"]["surface_elevated"]}',
  card: '{COLORS["dark"]["card"]}',

  textPrimary: '{COLORS["dark"]["text_primary"]}',
  textSecondary: '{COLORS["dark"]["text_secondary"]}',
  textTertiary: '{COLORS["dark"]["text_tertiary"]}',
  textInverse: '{COLORS["dark"]["text_inverse"]}',
  textLink: '{p_dark}',

  border: '{active_dark["border"]}',
  borderFocus: '{p_dark}',
  divider: '{active_dark["divider"]}',

  overlay: '{active_dark["overlay"]}',
  shadow: '{active_dark["shadow"]}',
  white: '#FFFFFF',
  black: '#000000',
}} as const;

export const glass = {{
  light: {{
    thin: '{GLASSMOKE["light"]["thin"]}',
    base: '{GLASSMOKE["light"]["base"]}',
    thick: '{GLASSMOKE["light"]["thick"]}',
    border: '{GLASSMOKE["light"]["border"]}',
  }},
  dark: {{
    thin: '{GLASSMOKE["dark"]["thin"]}',
    base: '{GLASSMOKE["dark"]["base"]}',
    thick: '{GLASSMOKE["dark"]["thick"]}',
    border: '{GLASSMOKE["dark"]["border"]}',
  }},
  obsidian: {{
    thin: 'rgba(0, 0, 0, 0.4)',
    base: 'rgba(0, 0, 0, 0.6)',
    thick: 'rgba(0, 0, 0, 0.8)',
    border: 'rgba(0, 255, 204, 0.2)',
  }},
}} as const;

export const gradients = {{
  primary: {json.dumps(GRADIENTS["primary"])},
  accent: {json.dumps(GRADIENTS["accent"])},
  glass: {json.dumps(GRADIENTS["glass"])},
}} as const;

export type ColorTokens = typeof lightColors;

// ── Typography ────────────────────────────────────────────────────────────

export const typography = {{
  fontSize: {{
    xs: {TYPOGRAPHY["font_size"]["xs"]},
    sm: {TYPOGRAPHY["font_size"]["sm"]},
    base: {TYPOGRAPHY["font_size"]["base"]},
    md: {TYPOGRAPHY["font_size"]["md"]},
    lg: {TYPOGRAPHY["font_size"]["lg"]},
    xl: {TYPOGRAPHY["font_size"]["xl"]},
    '2xl': {TYPOGRAPHY["font_size"]["2xl"]},
    '3xl': {TYPOGRAPHY["font_size"]["3xl"]},
    '4xl': {TYPOGRAPHY["font_size"]["4xl"]},
  }},
  fontWeight: {{
    regular: '{TYPOGRAPHY["font_weight"]["regular"]}' as const,
    medium: '{TYPOGRAPHY["font_weight"]["medium"]}' as const,
    semibold: '{TYPOGRAPHY["font_weight"]["semibold"]}' as const,
    bold: '{TYPOGRAPHY["font_weight"]["bold"]}' as const,
    extrabold: '{TYPOGRAPHY["font_weight"]["extrabold"]}' as const,
  }},
  lineHeight: {{
    tight: {TYPOGRAPHY["line_height"]["tight"]},
    normal: {TYPOGRAPHY["line_height"]["normal"]},
    relaxed: {TYPOGRAPHY["line_height"]["relaxed"]},
  }},
  // Presets
  h1: {{
    fontSize: 32,
    fontWeight: '700' as const,
    lineHeight: 40,
  }},
  h2: {{
    fontSize: 24,
    fontWeight: '700' as const,
    lineHeight: 32,
  }},
  subtitle: {{
    fontSize: 18,
    fontWeight: '600' as const,
    lineHeight: 24,
  }},
  body: {{
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 24,
  }},
  caption: {{
    fontSize: 12,
    fontWeight: '400' as const,
    lineHeight: 16,
  }},
  button: {{
    fontSize: 16,
    fontWeight: '600' as const,
    lineHeight: 20,
  }},
}} as const;


// ── Spacing ───────────────────────────────────────────────────────────────

export const spacing = {{
  0: 0,
  xs: {SPACING["xs"]},
  sm: {SPACING["sm"]},
  md: {SPACING["md"]},
  base: {SPACING["base"]},
  lg: {SPACING["lg"]},
  xl: {SPACING["xl"]},
  '2xl': {SPACING["2xl"]},
  '3xl': {SPACING["3xl"]},
  '4xl': {SPACING["4xl"]},
  '5xl': {SPACING["5xl"]},
}} as const;

// ── Borders ───────────────────────────────────────────────────────────────

export const borderRadius = {{
  none: {BORDERS["radius"]["none"]},
  sm: {BORDERS["radius"]["sm"]},
  md: {BORDERS["radius"]["md"]},
  lg: {BORDERS["radius"]["lg"]},
  xl: {BORDERS["radius"]["xl"]},
  '2xl': {BORDERS["radius"]["2xl"]},
  full: {BORDERS["radius"]["full"]},
}} as const;

// ── Shadows ───────────────────────────────────────────────────────────────

export const shadows = {{
  none: {{ shadowColor: 'transparent', shadowOffset: {{ width: 0, height: 0 }}, shadowOpacity: 0, shadowRadius: 0, elevation: 0 }},
  sm: {{ shadowColor: '#000', shadowOffset: {{ width: 0, height: 1 }}, shadowOpacity: 0.05, shadowRadius: 2, elevation: 1 }},
  md: {{ shadowColor: '#000', shadowOffset: {{ width: 0, height: 2 }}, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 }},
  lg: {{ shadowColor: '#000', shadowOffset: {{ width: 0, height: 4 }}, shadowOpacity: 0.15, shadowRadius: 8, elevation: 5 }},
  xl: {{ shadowColor: '#000', shadowOffset: {{ width: 0, height: 8 }}, shadowOpacity: 0.2, shadowRadius: 16, elevation: 8 }},
}} as const;

// ── Theme Hook ────────────────────────────────────────────────────────────

export function useTheme() {{
  const scheme = useColorScheme();
  const isObsidian = { 'true' if is_obsidian else 'false' };
  const colors = scheme === 'dark' ? darkColors : lightColors;
  const glassTheme = scheme === 'dark' ? (isObsidian ? glass.obsidian : glass.dark) : glass.light;
  
  return {{ 
    colors, 
    typography, 
    spacing, 
    borderRadius, 
    shadows, 
    glass: glassTheme,
    gradients,
    isDark: scheme === 'dark',
    isObsidian
  }};
}}


export {{ lightColors, darkColors }};
export default {{ lightColors, darkColors, typography, spacing, borderRadius, shadows }};
'''
