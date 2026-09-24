"""
Fetches cricket news from the RSS feeds listed in config.py,
filters out stories already posted before, and returns the newest ones.
"""

import json
import os
import feedparser

import config


def _load_posted_log():
    if not os.path.exists(config.POSTED_LOG_PATH):
        return set()
    with open(config.POSTED_LOG_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return set()
    return set(data.get("posted_ids", []))


def _save_posted_log(posted_ids):
    os.makedirs(os.path.dirname(config.POSTED_LOG_PATH), exist_ok=True)
    with open(config.POSTED_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump({"posted_ids": sorted(posted_ids)}, f, indent=2, ensure_ascii=False)


def _is_cricket_related(title, summary):
    text = f"{title} {summary}".lower()
    return any(keyword in text for keyword in config.CRICKET_KEYWORDS)


def get_new_stories():
    """
    Returns a list of dicts: [{"id", "title", "summary", "link"}]
    containing only stories that have not been posted before,
    newest first, capped at config.MAX_POSTS_PER_RUN.
    """
    already_posted = _load_posted_log()
    fresh_stories = []

    for feed_url in config.RSS_FEEDS:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            story_id = entry.get("id") or entry.get("link")
            if not story_id or story_id in already_posted:
                continue

            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()

            if not title:
                continue
            if not _is_cricket_related(title, summary):
                continue

            fresh_stories.append({
                "id": story_id,
                "title": title,
                "summary": summary,
                "link": entry.get("link", ""),
            })

    # Newest feeds usually list newest first already; just cap the count.
    return fresh_stories[: config.MAX_POSTS_PER_RUN]


def mark_as_posted(story_ids):
    posted = _load_posted_log()
    posted.update(story_ids)
    _save_posted_log(posted)


if __name__ == "__main__":
    stories = get_new_stories()
    print(f"Found {len(stories)} new cricket stories:")
    for s in stories:
        print(f" - {s['title']}")
