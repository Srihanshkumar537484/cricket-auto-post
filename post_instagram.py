"""
Publishes an image to Instagram using the Instagram Graph API.

Requirements (one-time setup, see README.md):
  - Instagram account must be a Business or Creator account
  - It must be linked to a Facebook Page
  - You need a long-lived access token with instagram_content_publish permission
  - IG_USER_ID and IG_ACCESS_TOKEN must be set as environment variables
    (in GitHub Actions these come from repository secrets)

The image must be reachable at a public URL. This project generates the
image, the GitHub Action commits it to the repo, and PUBLIC_RAW_BASE_URL
(raw.githubusercontent.com link) is used as the public URL.
"""

import time
import requests

import config


class InstagramPostError(Exception):
    pass


def _graph_url(path):
    return f"https://graph.facebook.com/{config.GRAPH_API_VERSION}/{path}"


def post_image(image_public_url, caption):
    """
    Two-step Graph API flow:
      1. Create a media container pointing at the public image URL
      2. Publish that container
    Returns the published media ID.
    """
    if not config.IG_USER_ID or not config.IG_ACCESS_TOKEN:
        raise InstagramPostError(
            "IG_USER_ID / IG_ACCESS_TOKEN not set. Add them as GitHub Actions secrets "
            "or in your local .env file."
        )

    # Step 1: create container
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

    # Small delay so Instagram has time to process the container
    time.sleep(5)

    # Step 2: publish container
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


def build_caption(story):
    hashtags = "#cricket #cricketnews #ipl #india #cricketfan"
    link_line = f"\n\nFull story: {story['link']}" if story.get("link") else ""
    return f"{story['title']}{link_line}\n\n{hashtags}"
