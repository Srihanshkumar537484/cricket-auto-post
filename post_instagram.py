"""
Publishes content to Instagram using the Instagram Graph API.
"""

import time
import requests

import config


class InstagramPostError(Exception):
    pass


def _graph_url(path):
    return f"https://graph.facebook.com/{config.GRAPH_API_VERSION}/{path}"


def post_image(image_public_url, caption):
    """Feed post: two-step Graph API flow (create container, then publish)."""
    if not config.IG_USER_ID or not config.IG_ACCESS_TOKEN:
        raise InstagramPostError(
            "IG_USER_ID / IG_ACCESS_TOKEN not set. Add them as GitHub Actions secrets "
            "or in your local .env file."
        )

    container_resp = requests.post(
        _graph_url(f"{config.IG_USER_ID}/media"),
        data={
            "image_url": image_public_url,
            "caption": caption,
            "access_token": config.IG_ACCESS_TOKEN,
        },
        timeout=30,
    )
    container_data = container_resp.json()
    if "id" not in container_data:
        raise InstagramPostError(f"Container creation failed: {container_data}")

    creation_id = container_data["id"]
    time.sleep(5)

    publish_resp = requests.post(
        _graph_url(f"{config.IG_USER_ID}/media_publish"),
        data={
            "creation_id": creation_id,
            "access_token": config.IG_ACCESS_TOKEN,
        },
        timeout=30,
    )
    publish_data = publish_resp.json()
    if "id" not in publish_data:
        raise InstagramPostError(f"Publishing failed: {publish_data}")

    return publish_data["id"]


def post_reel(video_public_url, caption, max_wait_seconds=180, poll_interval=8):
    """
    Reel post: create a REELS container pointing at the public video URL,
    poll until Instagram finishes processing it, then publish.
    """
    if not config.IG_USER_ID or not config.IG_ACCESS_TOKEN:
        raise InstagramPostError(
            "IG_USER_ID / IG_ACCESS_TOKEN not set. Add them as GitHub Actions secrets "
            "or in your local .env file."
        )

    container_resp = requests.post(
        _graph_url(f"{config.IG_USER_ID}/media"),
        data={
            "media_type": "REELS",
            "video_url": video_public_url,
            "caption": caption,
            "access_token": config.IG_ACCESS_TOKEN,
        },
        timeout=30,
    )
    container_data = container_resp.json()
    if "id" not in container_data:
        raise InstagramPostError(f"Reel container creation failed: {container_data}")

    creation_id = container_data["id"]

    waited = 0
    status = None
    while waited < max_wait_seconds:
        time.sleep(poll_interval)
        waited += poll_interval
        status_resp = requests.get(
            _graph_url(creation_id),
            params={"fields": "status_code", "access_token": config.IG_ACCESS_TOKEN},
            timeout=30,
        )
        status_data = status_resp.json()
        status = status_data.get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise InstagramPostError(f"Reel processing failed: {status_data}")

    if status != "FINISHED":
        raise InstagramPostError(
            f"Reel still processing after {max_wait_seconds}s (status: {status}). "
            "It may still publish later — check the Instagram app."
        )

    publish_resp = requests.post(
        _graph_url(f"{config.IG_USER_ID}/media_publish"),
        data={
            "creation_id": creation_id,
            "access_token": config.IG_ACCESS_TOKEN,
        },
        timeout=30,
    )
    publish_data = publish_resp.json()
    if "id" not in publish_data:
        raise InstagramPostError(f"Reel publishing failed: {publish_data}")

    return publish_data["id"]


def build_caption(story):
    hashtags = "#cricket #cricketnews #ipl #india #cricketfan #crickimasala"
    link_line = f"\n\nFull story: {story['link']}" if story.get("link") else ""
    return f"{story['title']}{link_line}\n\n{hashtags}"
