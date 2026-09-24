"""
Turns a news story dict into a branded 1080x1350 image using a fixed
template: background + accent bar + headline text + logo + footer.
"""

import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

import config


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        # Fallback to Pillow's built-in font if a custom .ttf isn't present yet
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


def build_image(story, output_path):
    """
    story: dict with at least "title" (and optionally "summary")
    output_path: where to save the generated .jpg
    """
    img = Image.new("RGB", (config.IMG_WIDTH, config.IMG_HEIGHT), config.BACKGROUND_COLOR)

    # Optional custom background photo, dimmed so text stays readable
    if os.path.exists(config.BACKGROUND_IMAGE_PATH):
        bg = Image.open(config.BACKGROUND_IMAGE_PATH).convert("RGB")
        bg = bg.resize((config.IMG_WIDTH, config.IMG_HEIGHT))
        overlay = Image.new("RGB", bg.size, (0, 0, 0))
        bg = Image.blend(bg, overlay, alpha=0.55)
        img.paste(bg, (0, 0))

    draw = ImageDraw.Draw(img)

    # Accent bar at the top
    draw.rectangle([(0, 0), (config.IMG_WIDTH, 18)], fill=config.ACCENT_COLOR)

    # "BREAKING" / category tag
    tag_font = _load_font(config.FONT_BOLD_PATH, 38)
    draw.rectangle([(60, 90), (460, 156)], fill=config.ACCENT_COLOR)
    draw.text((80, 102), "CRICKET NEWS", font=tag_font, fill=(0, 0, 0))

    # Headline
    headline_font = _load_font(config.FONT_BOLD_PATH, 64)
    max_text_width = config.IMG_WIDTH - 140
    lines = _wrap_text(draw, story["title"], headline_font, max_text_width)

    y = 260
    for line in lines[:6]:  # cap lines so it never overflows the canvas
        draw.text((70, y), line, font=headline_font, fill=config.TEXT_COLOR)
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        y += (bbox[3] - bbox[1]) + 20

    # Logo (bottom-left), if provided
    if os.path.exists(config.LOGO_PATH):
        logo = Image.open(config.LOGO_PATH).convert("RGBA")
        logo.thumbnail((160, 160))
        img.paste(logo, (60, config.IMG_HEIGHT - 220), logo)

    # Footer / page handle
    footer_font = _load_font(config.FONT_REGULAR_PATH, 36)
    draw.text(
        (60, config.IMG_HEIGHT - 60),
        config.PAGE_HANDLE,
        font=footer_font,
        fill=config.FOOTER_TEXT_COLOR,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "JPEG", quality=92)
    return output_path


if __name__ == "__main__":
    demo_story = {
        "title": "India wins thrilling last-over T20 against Australia to seal the series",
    }
    path = build_image(demo_story, os.path.join(config.OUTPUT_DIR, "demo.jpg"))
    print(f"Saved demo image to {path}")
