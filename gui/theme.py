"""
ROLEX AI — Premium Visual Identity / Theme
LOCKED DESIGN DIRECTION: original Rolex dark futuristic theme.
Deep obsidian + Rolex gold + electric cyan, with neon glow accents.

This module is pure data + KV styling. It never imports Kivy at module load,
so it is safe to import on any platform.
"""

# ---------------------------------------------------------------------------
# Palette — deep obsidian + gold/cyan neon accents
# ---------------------------------------------------------------------------
COLORS = {
    # Backgrounds (layered depth)
    "bg":            (0.031, 0.039, 0.055, 1),   # #080A0E deepest
    "bg_alt":        (0.047, 0.059, 0.082, 1),   # #0C0F15
    "panel":         (0.070, 0.086, 0.118, 1),   # #12161E
    "panel_light":   (0.102, 0.125, 0.169, 1),   # #1A202B
    "card":          (0.086, 0.106, 0.145, 1),   # #161B25
    "card_hi":       (0.118, 0.145, 0.196, 1),   # #1E2532
    "stroke":        (0.180, 0.212, 0.278, 1),   # #2E3647 subtle border

    # Accents
    "gold":          (0.831, 0.686, 0.216, 1),   # #D4AF37 Rolex gold
    "gold_hi":       (0.949, 0.831, 0.400, 1),   # #F2D466 bright gold
    "gold_dim":      (0.560, 0.455, 0.140, 1),
    "cyan":          (0.000, 0.898, 0.898, 1),   # #00E5E5 accent
    "cyan_hi":       (0.400, 1.000, 1.000, 1),   # #66FFFF
    "cyan_dim":      (0.000, 0.420, 0.450, 1),
    "violet":        (0.545, 0.361, 0.965, 1),   # #8B5CF6
    "magenta":       (0.925, 0.282, 0.600, 1),   # #EC4899

    # Text
    "text":          (0.925, 0.941, 0.965, 1),   # #ECF0F6
    "text_dim":      (0.560, 0.620, 0.700, 1),   # #8F9EB3
    "text_faint":    (0.360, 0.410, 0.480, 1),

    # Semantic
    "success":       (0.290, 0.870, 0.502, 1),   # #4ADE80
    "warning":       (0.980, 0.749, 0.290, 1),   # #FABF4A
    "error":         (0.937, 0.325, 0.314, 1),   # #EF5350

    # Bubbles
    "user_bubble":   (0.129, 0.180, 0.259, 1),
    "ai_bubble":     (0.086, 0.106, 0.145, 1),

    # Misc
    "overlay":       (0.0, 0.0, 0.0, 0.55),
    "white":         (1, 1, 1, 1),
    "black":         (0, 0, 0, 1),

    # --- Autobots theme accents -------------------------------------------
    "autobot_blue":  (0.129, 0.400, 0.850, 1),   # #2166D9 Optimus blue
    "autobot_red":   (0.850, 0.180, 0.180, 1),   # #D92E2E Autobot red
    "energy":        (0.400, 0.900, 1.000, 1),   # #66E6FF energon glow
    "energon":       (0.600, 0.300, 0.950, 1),   # #994CFF energon violet
    "steel":         (0.560, 0.620, 0.700, 1),   # #8F9EB3 metallic
    "hud":           (0.000, 0.898, 0.898, 0.85),
}

FONT = "Roboto"

# Gradient stops used by the animated background (top -> bottom)
BG_GRADIENT_TOP = (0.055, 0.070, 0.110, 1)     # #0E121C
BG_GRADIENT_BOT = (0.020, 0.026, 0.039, 1)     # #05070A

# Accent gradient (gold -> cyan) for hero elements
ACCENT_GRADIENT = [
    (0.831, 0.686, 0.216, 1),   # gold
    (0.000, 0.898, 0.898, 1),   # cyan
]

# Autobots energon gradient (blue -> cyan -> violet) for hero/HUD elements
ENERGON_GRADIENT = [
    (0.129, 0.400, 0.850, 1),   # autobot blue
    (0.400, 0.900, 1.000, 1),   # energy cyan
    (0.600, 0.300, 0.950, 1),   # energon violet
]

# HUD scanline / grid colour
HUD_GRID = (0.000, 0.898, 0.898, 0.10)


# ---------------------------------------------------------------------------
# Kivy KV styling (premium dark futuristic Rolex theme)
# ---------------------------------------------------------------------------
KV = """
#:import C gui.theme.COLORS
#:import dp kivy.metrics.dp

<RolexRoot>:
    canvas.before:
        Color:
            rgba: C['bg']
        Rectangle:
            pos: self.pos
            size: self.size

<RolexButton@Button>:
    background_normal: ''
    background_down: ''
    background_color: C['panel_light']
    color: C['text']
    font_size: '15sp'
    bold: True

<RolexLabel@Label>:
    color: C['text']
    font_size: '14sp'

<GoldButton@Button>:
    background_normal: ''
    background_down: ''
    background_color: C['gold']
    color: C['bg']
    font_size: '15sp'
    bold: True

<CyanButton@Button>:
    background_normal: ''
    background_down: ''
    background_color: C['cyan_dim']
    color: C['text']
    font_size: '15sp'
    bold: True

<GhostButton@Button>:
    background_normal: ''
    background_down: ''
    background_color: C['card_hi']
    color: C['text']
    font_size: '14sp'

<RolexInput@TextInput>:
    background_normal: ''
    background_active: ''
    background_color: C['panel_light']
    foreground_color: C['text']
    cursor_color: C['gold']
    hint_text_color: C['text_dim']
    font_size: '15sp'
    padding: [dp(12), dp(12), dp(12), dp(12)]
"""
