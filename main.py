"""
Orchestrates the pipeline in TWO separate steps, because Instagram's Graph
API needs the image to already be live at a public URL before it can post
it — so the image must be committed & pushed to GitHub BEFORE we call the
Instagram API.

  Step 1 (generate):  fetch new stories -> build images -> save a
                       pending.json list. (workflow then commits & pushes)
  Step 2 (publish):   read pending.json -> images are now live on
                       raw.githubusercontent.com -> post each to Instagram
                       -> mark as posted -> clear pending.json

Run manually with:
    python main.py generate
    python main.py publish

Runs automatically via .github/workflows/post_cricket_news.yml
"""

import json
import os
import sys

import config
from fetch_news import get_new_stories, mark_as_posted
from generate_image import build_image
from post_instagram import post_image, build_caption, InstagramPostError

PENDING_PATH = os.path.join("data", "pending.json")


def _save_pending(items):
    os.makedirs(os.path.dirname(PENDING_PATH), exist_ok=True)
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def _load_pending():
    if not os.path.exists(PENDING_PATH):
        return []
    with open(PENDING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def generate():
    """Step 1: fetch news + build images, save list of pending posts."""
    stories = get_new_stories()

    if not stories:
        print("No new cricket stories found. Nothing to generate.")
        _save_pending([])
        return

    print(f"Found {len(stories)} new stor{'y' if len(stories) == 1 else 'ies'}.")

    pending = []
    for story in stories:
        safe_name = "".join(c for c in story["id"] if c.isalnum())[-20:]
        image_filename = f"{safe_name}.jpg"
        image_path = os.path.join(config.OUTPUT_DIR, image_filename)

        print(f"Generating image for: {story['title']}")
        build_image(story, image_path)

        pending.append({
            "id": story["id"],
            "title": story["title"],
            "link": story.get("link", ""),
            "image_filename": image_filename,
        })

    _save_pending(pending)
    print(f"Saved {len(pending)} pending post(s) to {PENDING_PATH}")


def publish():
    """Step 2: images are now live on GitHub — post each to Instagram."""
    pending = _load_pending()

    if not pending:
        print("No pending posts to publish.")
        return

    if not config.PUBLIC_RAW_BASE_URL:
        print(
            "PUBLIC_RAW_BASE_URL is not set — cannot publish. "
            "Set it as an env var (see README.md).",
            file=sys.stderr,
        )
        sys.exit(1)

    posted_ids = []
    for item in pending:
        image_public_url = f"{config.PUBLIC_RAW_BASE_URL}/{item['image_filename']}"
        caption = build_caption({"title": item["title"], "link": item["link"]})

        try:
            media_id = post_image(image_public_url, caption)
            print(f"Posted '{item['title']}' -> media ID {media_id}")
            posted_ids.append(item["id"])
        except InstagramPostError as e:
            print(f"Failed to post '{item['title']}': {e}", file=sys.stderr)

    if posted_ids:
        mark_as_posted(posted_ids)
        print(f"Marked {len(posted_ids)} stories as posted.")

    _save_pending([])  # clear the queue either way


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "generate":
        generate()
    elif mode == "publish":
        publish()
    else:
        print("Usage: python main.py [generate|publish]")
        sys.exit(1)
