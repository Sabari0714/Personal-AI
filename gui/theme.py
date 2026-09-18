"""
ROLEX AI — Visual Identity / Theme
LOCKED DESIGN DIRECTION: original Rolex dark futuristic theme.
Do NOT replace with generic Jarvis styling.
"""

# Rolex palette — deep obsidian + gold/cyan accents
COLORS = {
    "bg":            (0.043, 0.055, 0.078, 1),   # #0B0E14 deep obsidian
    "bg_alt":        (0.070, 0.086, 0.118, 1),   # #12161E panel
    "panel":         (0.094, 0.113, 0.153, 1),   # #181D27
    "panel_light":   (0.129, 0.153, 0.204, 1),   # #212734
    "gold":          (0.831, 0.686, 0.216, 1),   # #D4AF37 Rolex gold
    "gold_dim":      (0.600, 0.490, 0.150, 1),
    "cyan":          (0.000, 0.898, 0.898, 1),   # #00E5E5 accent
    "cyan_dim":      (0.000, 0.500, 0.500, 1),
    "text":          (0.902, 0.925, 0.957, 1),   # #E6ECF4
    "text_dim":      (0.560, 0.620, 0.700, 1),
    "success":       (0.290, 0.870, 0.502, 1),
    "warning":       (0.980, 0.749, 0.290, 1),
    "error":         (0.937, 0.325, 0.314, 1),
    "user_bubble":   (0.129, 0.180, 0.259, 1),
    "ai_bubble":     (0.094, 0.113, 0.153, 1),
}

FONT = "Roboto"

# Kivy KV styling string (dark futuristic Rolex theme)
KV = """
#:import C gui.theme.COLORS

<RolexRoot>:
    canvas.before:
        Color:
            rgba: C['bg']
        Rectangle:
            pos: self.pos
            size: self.size

<RolexButton@Button>:
    background_normal: ''
    background_color: C['panel_light']
    color: C['text']
    font_size: '15sp'
    bold: True

<RolexLabel@Label>:
    color: C['text']
    font_size: '14sp'

<GoldButton@Button>:
    background_normal: ''
    background_color: C['gold']
    color: C['bg']
    font_size: '15sp'
    bold: True

<CyanButton@Button>:
    background_normal: ''
    background_color: C['cyan_dim']
    color: C['text']
    font_size: '15sp'
    bold: True
"""
