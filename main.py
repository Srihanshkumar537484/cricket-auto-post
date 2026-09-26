"""
Orchestrates the pipeline in TWO separate steps, because Instagram's Graph
API needs the image/video to already be live at a public URL before it
can post it — so files must be committed & pushed to GitHub BEFORE we
call the Instagram API.
"""

import json
import os
import sys

import config
from fetch_news import get_new_stories, mark_as_posted
from generate_image import build_image, build_reel_frame
from generate_reel import build_reel_video
from post_instagram import post_image, post_reel, build_caption, InstagramPostError

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
    """Step 1: fetch news + build feed image and reel video for each story."""
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

        print(f"Generating feed image for: {story['title']}")
        build_image(story, image_path)

        item = {
            "id": story["id"],
            "title": story["title"],
            "link": story.get("link", ""),
            "image_filename": image_filename,
            "reel_filename": None,
        }

        if config.ENABLE_REELS:
            try:
                print(f"Generating reel for: {story['title']}")
                reel_frame_path = os.path.join(config.OUTPUT_DIR, f"{safe_name}_frame.jpg")
                build_reel_frame(story, reel_frame_path)

                reel_filename = f"{safe_name}.mp4"
                reel_path = os.path.join(config.OUTPUT_DIR, reel_filename)
                build_reel_video(reel_frame_path, reel_path)

                item["reel_filename"] = reel_filename
            except Exception as e:
                print(f"Reel generation failed for '{story['title']}': {e}", file=sys.stderr)

        pending.append(item)

    _save_pending(pending)
    print(f"Saved {len(pending)} pending post(s) to {PENDING_PATH}")


def publish():
    """Step 2: files are now live on GitHub — post feed image + reel to Instagram."""
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
        caption = build_caption({"title": item["title"], "link": item["link"]})
        story_posted = False

        image_public_url = f"{config.PUBLIC_RAW_BASE_URL}/{item['image_filename']}"
        try:
            media_id = post_image(image_public_url, caption)
            print(f"Posted feed image '{item['title']}' -> media ID {media_id}")
            story_posted = True
        except InstagramPostError as e:
            print(f"Failed to post feed image for '{item['title']}': {e}", file=sys.stderr)

        if item.get("reel_filename"):
            reel_public_url = f"{config.PUBLIC_RAW_BASE_URL}/{item['reel_filename']}"
            try:
                media_id = post_reel(reel_public_url, caption)
                print(f"Posted reel '{item['title']}' -> media ID {media_id}")
                story_posted = True
            except InstagramPostError as e:
                print(f"Failed to post reel for '{item['title']}': {e}", file=sys.stderr)

        if story_posted:
            posted_ids.append(item["id"])

    if posted_ids:
        mark_as_posted(posted_ids)
        print(f"Marked {len(posted_ids)} stories as posted.")

    _save_pending([])


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "generate":
        generate()
    elif mode == "publish":
        publish()
    else:
        print("Usage: python main.py [generate|publish]")
        sys.exit(1)
