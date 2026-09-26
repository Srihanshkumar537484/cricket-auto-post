"""
Turns a news story dict into a branded template image using a fixed
layout: background + accent bar + headline text + optional player
photo / country flag + logo + footer.

build_image()       -> normal 4:5 feed post
build_reel_frame()  -> tall 9:16 frame used as the base for the reel video
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageOps

import config
from entity_media import fetch_player_photo, find_country, fetch_flag


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _rounded_photo(path, size):
    """Opens an image, crops it to a square, and rounds the corners."""
    try:
        img = Image.open(path).convert("RGB")
    except Exception:
        return None
    img = ImageOps.fit(img, (size, size), method=Image.LANCZOS)

    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, size, size], radius=int(size * 0.08), fill=255)

    rounded = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rounded.paste(img, (0, 0), mask)
    return rounded


def _draw_template(story, width, height, headline_font_size, tag_font_size):
    """Shared drawing logic used by both the feed image and the reel frame."""
    img = Image.new("RGB", (width, height), config.BACKGROUND_COLOR)

    if os.path.exists(config.BACKGROUND_IMAGE_PATH):
        bg = Image.open(config.BACKGROUND_IMAGE_PATH).convert("RGB")
        bg = bg.resize((width, height))
        overlay = Image.new("RGB", bg.size, (0, 0, 0))
        bg = Image.blend(bg, overlay, alpha=0.55)
        img.paste(bg, (0, 0))

    draw = ImageDraw.Draw(img)

    # Accent bar at the top
    bar_h = max(14, int(height * 0.013))
    draw.rectangle([(0, 0), (width, bar_h)], fill=config.ACCENT_COLOR)

    # Category tag
    tag_font = _load_font(config.FONT_BOLD_PATH, tag_font_size)
    tag_text = "CRICKET NEWS"
    tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tag_w = tag_bbox[2] - tag_bbox[0]
    pad_x, pad_y = 24, 18
    tag_top = int(height * 0.075)
    draw.rectangle(
        [(60, tag_top), (60 + tag_w + pad_x * 2, tag_top + tag_bbox[3] + pad_y * 2)],
        fill=config.ACCENT_COLOR,
    )
    draw.text((60 + pad_x, tag_top + pad_y - tag_bbox[1]), tag_text, font=tag_font, fill=(0, 0, 0))

    # Optional real photo (player/team) fetched from Wikipedia
    photo_path = None
    if config.ENABLE_PLAYER_PHOTO:
        photo_path = fetch_player_photo(story["title"], story["id"])
        print(f"[generate_image] photo_path = {photo_path}")

    photo_size = int(width * 0.42)
    photo_top = tag_top + tag_bbox[3] + pad_y * 2 + 40
    if photo_path:
        rounded = _rounded_photo(photo_path, photo_size)
        if rounded:
            photo_x = width - photo_size - 60
            img.paste(rounded, (photo_x, photo_top), rounded)
        else:
            photo_path = None

    # Headline — narrower if a photo is showing, so text never overlaps it
    headline_font = _load_font(config.FONT_BOLD_PATH, headline_font_size)
    max_text_width = (width - 140 - photo_size - 40) if photo_path else (width - 140)
    max_text_width = max(max_text_width, int(width * 0.4))
    lines = _wrap_text(draw, story["title"], headline_font, max_text_width)

    y = photo_top
    line_x = 70
    for line in lines[:8]:
        draw.text((line_x, y), line, font=headline_font, fill=config.TEXT_COLOR)
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        y += (bbox[3] - bbox[1]) + int(headline_font_size * 0.3)

    # Country flag badge (top-right corner), if a nation is named — drawn with
    # a white card behind it so it's clearly visible against any background
    if config.ENABLE_COUNTRY_FLAG:
        iso = find_country(story["title"])
        flag_path = fetch_flag(iso) if iso else None
        print(f"[generate_image] flag_path = {flag_path}")
        if flag_path and os.path.exists(flag_path):
            try:
                flag_img = Image.open(flag_path).convert("RGBA")
                flag_w = int(width * 0.20)
                ratio = flag_img.height / flag_img.width
                flag_h = int(flag_w * ratio)
                flag_img = flag_img.resize((flag_w, flag_h))

                card_pad = 16
                card_x0 = width - flag_w - 60 - card_pad
                card_y0 = int(bar_h + 24)
                card_x1 = width - 60 + card_pad
                card_y1 = card_y0 + flag_h + card_pad * 2
                draw.rounded_rectangle(
                    [(card_x0, card_y0), (card_x1, card_y1)],
                    radius=12,
                    fill=(255, 255, 255, 255),
                )
                img.paste(flag_img, (width - flag_w - 60, card_y0 + card_pad), flag_img)
            except Exception as e:
                print(f"[generate_image] failed to paste flag: {e}")

    # Logo (bottom-left), if provided
    if os.path.exists(config.LOGO_PATH):
        logo = Image.open(config.LOGO_PATH).convert("RGBA")
        logo_size = int(width * 0.15)
        logo.thumbnail((logo_size, logo_size))
        img.paste(logo, (60, height - int(height * 0.16)), logo)

    # Footer / page handle
    footer_font = _load_font(config.FONT_REGULAR_PATH, int(width * 0.033))
    draw.text(
        (60, height - int(height * 0.045)),
        config.PAGE_HANDLE,
        font=footer_font,
        fill=config.FOOTER_TEXT_COLOR,
    )

    return img


def build_image(story, output_path):
    """Builds the normal 4:5 feed post image."""
    img = _draw_template(
        story,
        config.IMG_WIDTH,
        config.IMG_HEIGHT,
        headline_font_size=64,
        tag_font_size=38,
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "JPEG", quality=92)
    return output_path


def build_reel_frame(story, output_path):
    """Builds a tall 9:16 frame used as the base image for the reel video."""
    img = _draw_template(
        story,
        config.REEL_WIDTH,
        config.REEL_HEIGHT,
        headline_font_size=68,
        tag_font_size=38,
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "JPEG", quality=92)
    return output_path


if __name__ == "__main__":
    demo_story = {
        "id": "demo123",
        "title": "India wins thrilling last-over T20 against Australia to seal the series",
    }
    path = build_image(demo_story, os.path.join(config.OUTPUT_DIR, "demo.jpg"))
    print(f"Saved demo image to {path}")
    reel_path = build_reel_frame(demo_story, os.path.join(config.OUTPUT_DIR, "demo_reel_frame.jpg"))
    print(f"Saved demo reel frame to {reel_path}")
