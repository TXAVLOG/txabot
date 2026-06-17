import os

# Font paths with fallbacks
FONT_MAIN = "font/arial unicode ms.otf"
FONT_MAIN_BOLD = "font/arial unicode ms bold.otf"
FONT_EMOJI = "font/NotoEmoji-Bold.ttf"
FONT_FALLBACKS = ["font/arial.ttf", "font/Roboto-Regular.ttf"]
FONT_FALLBACKS_BOLD = ["font/Roboto-Bold.ttf", "font/NotoSans-Bold.ttf", "font/arial.ttf"]

# Color palette (RGBA)
COLORS = {
    "bg": (18, 18, 24, 255),
    "card": (40, 40, 50, 220),
    "card_border": (255, 255, 255, 30),
    "text_primary": (255, 255, 255, 255),
    "text_secondary": (180, 180, 190, 255),
    "text_muted": (140, 140, 150, 255),
    "shadow": (0, 0, 0, 150),
    "shadow_light": (0, 0, 0, 80),
    "accent_capcut": (0, 210, 106, 255),
    "accent_tiktok": (254, 44, 85, 255),
    "accent_tiktok_cyan": (37, 244, 238, 255),
    "placeholder": (60, 60, 70, 255),
    "verified": (0, 200, 255, 255),
}

# Brand gradients
GRADIENTS = {
    "capcut": [(0, 210, 106, 255), (0, 180, 160, 255)],
    "tiktok": [(254, 44, 85, 255), (37, 244, 238, 255)],
    "dark": [(30, 30, 38, 255), (18, 18, 24, 255)],
}

# Responsive size presets
SIZES = {
    "sm": {
        "scale": 1.5,
        "card_width": 360,
        "card_height": 90,
        "thumb_size": 60,
        "padding": 14,
        "spacing_y": 8,
        "card_padding": 8,
        "header_height": 50,
        "footer_height": 36,
        "radius": 12,
        "thumb_radius": 8,
        "max_title_lines": 1,
    },
    "md": {
        "scale": 2,
        "card_width": 480,
        "card_height": 110,
        "thumb_size": 80,
        "padding": 18,
        "spacing_y": 10,
        "card_padding": 10,
        "header_height": 60,
        "footer_height": 44,
        "radius": 16,
        "thumb_radius": 10,
        "max_title_lines": 2,
    },
    "lg": {
        "scale": 2,
        "card_width": 640,
        "card_height": 130,
        "thumb_size": 96,
        "padding": 20,
        "spacing_y": 12,
        "card_padding": 12,
        "header_height": 70,
        "footer_height": 50,
        "radius": 18,
        "thumb_radius": 12,
        "max_title_lines": 2,
    },
}

# Paths
BACKGROUND_PATH = "background/"
CACHE_PATH = "modules/cache/"
os.makedirs(CACHE_PATH, exist_ok=True)
