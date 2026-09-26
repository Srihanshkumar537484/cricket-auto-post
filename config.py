"""
Central configuration for the cricket news auto-poster.
Edit this file to change news sources, template look, and posting behaviour.
"""

import os

# ---------------------------------------------------------------------------
# NEWS SOURCES (free, no API key needed)
# Add / remove RSS feeds here. Each feed is checked every run.
# ---------------------------------------------------------------------------
RSS_FEEDS = [
    "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",   # ESPN Cricinfo - all stories
    "https://www.cricbuzz.com/rss-feed",                             # Cricbuzz - news
]

# Keywords used to double check a story is actually cricket related
# (useful if you add a general sports feed later)
CRICKET_KEYWORDS = ["cricket", "ipl", "odi", "t20", "test match", "bcci", "icc"]

# Max number of new stories to post in a single run (keeps things sane)
MAX_POSTS_PER_RUN = 2

# ---------------------------------------------------------------------------
# TEMPLATE / IMAGE SETTINGS
# ---------------------------------------------------------------------------
IMG_WIDTH = 1080
IMG_HEIGHT = 1350          # 4:5 Instagram portrait, good for feed + reels cover

BACKGROUND_COLOR = (10, 20, 40)      # dark navy background
ACCENT_COLOR = (255, 200, 0)         # yellow accent bar / headline highlight
TEXT_COLOR = (255, 255, 255)         # white headline text
FOOTER_TEXT_COLOR = (180, 180, 180)

# Fonts: put .ttf files inside assets/fonts/ and reference them here.
FONT_BOLD_PATH = "assets/fonts/DejaVuSans-Bold.ttf"
FONT_REGULAR_PATH = "assets/fonts/DejaVuSans.ttf"

LOGO_PATH = "assets/logo.png"          # your page logo, put a transparent PNG here
BACKGROUND_IMAGE_PATH = "assets/background.jpg"  # optional custom background image

PAGE_HANDLE = "@crickimasala"          # shown in the footer of every post

# Auto-fetch a player photo / country flag related to the story (free, no key)
ENABLE_PLAYER_PHOTO = True     # tries Wikipedia for a real photo of the player/team named in the headline
ENABLE_COUNTRY_FLAG = True     # overlays a small flag badge if a cricket-playing country is named
PHOTO_CACHE_DIR = "cache/media"

# ---------------------------------------------------------------------------
# REEL (video) SETTINGS
# ---------------------------------------------------------------------------
ENABLE_REELS = True
REEL_WIDTH = 1080
REEL_HEIGHT = 1920           # 9:16 portrait, required for Reels
REEL_DURATION_SECONDS = 7

# ---------------------------------------------------------------------------
# OUTPUT / STATE
# ---------------------------------------------------------------------------
OUTPUT_DIR = "generated"
POSTED_LOG_PATH = "data/posted_log.json"

# ---------------------------------------------------------------------------
# INSTAGRAM GRAPH API (values come from GitHub Actions secrets / .env)
# ---------------------------------------------------------------------------
IG_USER_ID = os.environ.get("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
GRAPH_API_VERSION = "v21.0"

# Public base URL where generated images become reachable after being
# committed & pushed to the repo (GitHub raw content URL).
PUBLIC_RAW_BASE_URL = os.environ.get("PUBLIC_RAW_BASE_URL", "")
