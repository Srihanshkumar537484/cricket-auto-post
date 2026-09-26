"""
Looks at a news headline and tries to find:
  1. A real photo of the player/team it's about (via Wikipedia's free API)
  2. A country flag, if a cricket-playing nation is named

Both are best-effort and fail silently — if nothing is found (no internet,
no match, Wikipedia has no image), the template just falls back to the
plain background, so the pipeline never breaks because of this.
"""

import os
import re
import requests

import config

# Cricket-playing nations -> ISO codes used by flagcdn.com (free, no key).
# England/Scotland/Wales use flagcdn's UK-subdivision codes.
COUNTRY_FLAGS = {
    "india": "in",
    "australia": "au",
    "england": "gb-eng",
    "pakistan": "pk",
    "south africa": "za",
    "new zealand": "nz",
    "sri lanka": "lk",
    "bangladesh": "bd",
    "afghanistan": "af",
    "ireland": "ie",
    "scotland": "gb-sct",
    "zimbabwe": "zw",
    "west indies": None,     # no single flag - regional team, skip
    "usa": "us",
    "united states": "us",
    "uae": "ae",
    "nepal": "np",
    "namibia": "na",
    "netherlands": "nl",
}


def _ensure_cache_dir():
    os.makedirs(config.PHOTO_CACHE_DIR, exist_ok=True)


def find_country(text):
    """Returns a flagcdn ISO code if a cricket-playing country is named, else None."""
    text_lower = text.lower()
    for name in sorted(COUNTRY_FLAGS, key=len, reverse=True):
        if name in text_lower:
            return COUNTRY_FLAGS[name]
    return None


def fetch_flag(iso_code):
    """Downloads a country flag PNG, returns local path or None on failure."""
    if not iso_code:
        return None
    _ensure_cache_dir()
    local_path = os.path.join(config.PHOTO_CACHE_DIR, f"flag_{iso_code}.png")
    if os.path.exists(local_path):
        return local_path
    try:
        url = f"https://flagcdn.com/w320/{iso_code}.png"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200 and resp.content:
            with open(local_path, "wb") as f:
                f.write(resp.content)
            return local_path
    except requests.RequestException:
        pass
    return None


def _clean_query(headline):
    text = re.sub(r"\(.*?\)", "", headline)
    return text.strip()


def fetch_player_photo(headline, story_id):
    """
    Tries to find a real photo related to the headline via Wikipedia's
    free REST API. Returns a local image path, or None if nothing found.
    """
    if not config.ENABLE_PLAYER_PHOTO:
        return None

    _ensure_cache_dir()
    safe_name = "".join(c for c in story_id if c.isalnum())[-20:]
    local_path = os.path.join(config.PHOTO_CACHE_DIR, f"photo_{safe_name}.jpg")
    if os.path.exists(local_path):
        return local_path

    query = _clean_query(headline)

    try:
        search_resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": 1,
                "namespace": 0,
                "format": "json",
            },
            timeout=10,
        )
        search_data = search_resp.json()
        titles = search_data[1] if len(search_data) > 1 else []
        if not titles:
            return None
        title = titles[0]

        summary_resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}",
            timeout=10,
        )
        if summary_resp.status_code != 200:
            return None
        summary_data = summary_resp.json()
        thumbnail = summary_data.get("thumbnail", {}).get("source")
        if not thumbnail:
            return None

        img_resp = requests.get(thumbnail, timeout=10)
        if img_resp.status_code == 200 and img_resp.content:
            with open(local_path, "wb") as f:
                f.write(img_resp.content)
            return local_path

    except (requests.RequestException, ValueError, KeyError, IndexError):
        pass

    return None
