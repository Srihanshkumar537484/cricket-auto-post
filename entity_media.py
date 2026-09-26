"""
Looks at a news headline and tries to find:
  1. A real photo of the player/team it's about (via Wikipedia's free API)
  2. A country flag, if a cricket-playing nation is named

Both are best-effort and fail silently — if nothing is found (no internet,
no match, Wikipedia has no image), the template just falls back to the
plain background, so the pipeline never breaks because of this.
Prints debug info so you can see what happened in the GitHub Actions logs.
"""

import os
import re
import requests

import config

# Cricket-playing nations -> ISO codes used by flagcdn.com (free, no key).
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
    "west indies": None,
    "usa": "us",
    "united states": "us",
    "uae": "ae",
    "nepal": "np",
    "namibia": "na",
    "netherlands": "nl",
}

GENERIC_WORDS = {
    "the", "a", "an", "in", "on", "at", "for", "from", "to", "of", "and", "vs",
    "test", "series", "match", "world", "cup", "asian", "games", "cricket",
    "first", "second", "third", "time", "since", "after", "before", "day",
    "odi", "odis", "t20", "t20i", "t20is", "ipl", "bcci", "icc", "squad",
    "team", "captain",
}

REQUEST_TIMEOUT = 20
HEADERS = {
    "User-Agent": "CricketNewsBot/1.0 (https://github.com/; contact: cricketnewsbot@example.com)",
    "Accept": "application/json",
}
MAX_CANDIDATES_TO_TRY = 4


def _ensure_cache_dir():
    os.makedirs(config.PHOTO_CACHE_DIR, exist_ok=True)


def find_country(text):
    """Country mentioned earliest in the text wins (usually the subject)."""
    text_lower = text.lower()
    best_name, best_pos = None, None
    for name in COUNTRY_FLAGS:
        pos = text_lower.find(name)
        if pos != -1 and (best_pos is None or pos < best_pos):
            best_name, best_pos = name, pos
    if best_name:
        code = COUNTRY_FLAGS[best_name]
        print(f"[entity_media] country matched: '{best_name}' -> {code}")
        return code
    print("[entity_media] no country matched in headline")
    return None


def fetch_flag(iso_code):
    if not iso_code:
        return None
    _ensure_cache_dir()
    local_path = os.path.join(config.PHOTO_CACHE_DIR, f"flag_{iso_code}.png")
    if os.path.exists(local_path):
        print(f"[entity_media] using cached flag: {local_path}")
        return local_path
    try:
        url = f"https://flagcdn.com/w320/{iso_code}.png"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        print(f"[entity_media] flag fetch {url} -> status {resp.status_code}")
        if resp.status_code == 200 and resp.content:
            with open(local_path, "wb") as f:
                f.write(resp.content)
            return local_path
    except requests.RequestException as e:
        print(f"[entity_media] flag fetch failed: {e}")
    return None


def _extract_candidates(headline):
    text = re.sub(r"[,:()]", " ", headline)
    matches = re.findall(r"\b[A-Z][a-zA-Z.]*(?:\s+[A-Z][a-zA-Z.]*)*\b", text)

    candidates = []
    seen = set()
    for m in matches:
        m = m.strip()
        words = m.split()
        if len(words) == 1 and words[0].lower() in GENERIC_WORDS:
            continue
        if m.lower() in COUNTRY_FLAGS:
            continue
        if len(m) < 3:
            continue
        if m.lower() not in seen:
            seen.add(m.lower())
            candidates.append(m)

    candidates.sort(key=lambda c: len(c.split()), reverse=True)
    return candidates[:MAX_CANDIDATES_TO_TRY]


def _wiki_summary(query):
    """
    Returns (title, thumbnail_url, description) for the best Wikipedia
    match, or None. Uses the newer REST search endpoint (more reliable
    than the old 'opensearch' action, which some hosts get blocked/
    rate-limited on).
    """
    try:
        search_resp = requests.get(
            "https://en.wikipedia.org/w/rest.php/v1/search/page",
            params={"q": query, "limit": 1},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if search_resp.status_code != 200:
            print(
                f"[entity_media] '{query}' -> search status {search_resp.status_code}, "
                f"body starts: {search_resp.text[:150]!r}"
            )
            return None

        try:
            search_data = search_resp.json()
        except ValueError:
            print(f"[entity_media] '{query}' -> search returned non-JSON: {search_resp.text[:150]!r}")
            return None

        pages = search_data.get("pages", [])
        if not pages:
            print(f"[entity_media] '{query}' -> no Wikipedia page match")
            return None

        title = pages[0].get("title") or pages[0].get("key", "").replace("_", " ")

        summary_resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}",
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if summary_resp.status_code != 200:
            print(
                f"[entity_media] '{query}' -> matched '{title}' but summary status "
                f"{summary_resp.status_code}: {summary_resp.text[:150]!r}"
            )
            return None

        try:
            summary_data = summary_resp.json()
        except ValueError:
            print(f"[entity_media] '{query}' -> summary returned non-JSON: {summary_resp.text[:150]!r}")
            return None

        thumbnail = summary_data.get("thumbnail", {}).get("source")
        description = (summary_data.get("description") or "").lower()
        print(
            f"[entity_media] '{query}' -> matched '{title}' "
            f"(desc: '{description}', has_thumb: {bool(thumbnail)})"
        )
        return title, thumbnail, description

    except requests.RequestException as e:
        print(f"[entity_media] '{query}' -> request failed: {e}")
        return None


def fetch_player_photo(headline, story_id):
    if not config.ENABLE_PLAYER_PHOTO:
        return None

    _ensure_cache_dir()
    safe_name = "".join(c for c in story_id if c.isalnum())[-20:]
    local_path = os.path.join(config.PHOTO_CACHE_DIR, f"photo_{safe_name}.jpg")
    if os.path.exists(local_path):
        print(f"[entity_media] using cached photo: {local_path}")
        return local_path

    candidates = _extract_candidates(headline)
    print(f"[entity_media] name candidates: {candidates}")

    person_keywords = ("cricketer", "cricket player", "batter", "batsman", "bowler", "all-rounder", "wicket-keeper")
    best_fallback = None

    for query in candidates:
        result = _wiki_summary(query)
        if not result:
            continue
        title, thumbnail, description = result
        if not thumbnail:
            continue
        if any(kw in description for kw in person_keywords):
            downloaded = _download_image(thumbnail, local_path)
            if downloaded:
                return downloaded
        elif best_fallback is None:
            best_fallback = (title, thumbnail)

    if best_fallback:
        title, thumbnail = best_fallback
        print(f"[entity_media] no confirmed cricketer match, using best fallback: '{title}'")
        return _download_image(thumbnail, local_path)

    print("[entity_media] no usable photo found for this headline")
    return None


def _download_image(url, local_path):
    try:
        img_resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if img_resp.status_code == 200 and img_resp.content:
            with open(local_path, "wb") as f:
                f.write(img_resp.content)
            print(f"[entity_media] saved photo to {local_path}")
            return local_path
        print(f"[entity_m
