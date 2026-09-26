"""
Turns a static template image into a short vertical reel video using a
slow Ken-Burns style zoom (no external video clips needed, no copyright
concerns, completely free — just FFmpeg, which ships on GitHub's runners).
"""

import os
import subprocess

import config


def build_reel_video(frame_path, output_path):
    """
    frame_path: a 1080x1920 JPG (from generate_image.build_reel_frame)
    output_path: where to save the resulting .mp4
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fps = 30
    total_frames = config.REEL_DURATION_SECONDS * fps
    zoompan_filter = (
        f"scale={config.REEL_WIDTH * 2}:{config.REEL_HEIGHT * 2},"
        f"zoompan=z='min(zoom+0.0008,1.08)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:s={config.REEL_WIDTH}x{config.REEL_HEIGHT}:fps={fps}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", frame_path,
        "-vf", zoompan_filter,
        "-t", str(config.REEL_DURATION_SECONDS),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-1500:]}")

    return output_path


if __name__ == "__main__":
    from generate_image import build_reel_frame

    demo_story = {
        "id": "demo123",
        "title": "India wins thrilling last-over T20 against Australia to seal the series",
    }
    frame_path = build_reel_frame(demo_story, os.path.join(config.OUTPUT_DIR, "demo_reel_frame.jpg"))
    video_path = build_reel_video(frame_path, os.path.join(config.OUTPUT_DIR, "demo_reel.mp4"))
    print(f"Saved demo reel to {video_path}")
