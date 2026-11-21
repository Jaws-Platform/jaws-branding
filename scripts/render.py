# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow==12.0.0"]
# ///
"""Render every published asset from the logo in source/ and the fonts in fonts/.

    uv run scripts/render.py           write every asset
    uv run scripts/render.py --check   fail if a committed asset is out of date

The output paths are a contract: other repositories link to them from
`main`, so a path is never renamed or removed. Change what is drawn freely.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parent.parent
SOURCE_LOGO = ROOT / "source" / "coiled-shark-tattoo-flash.png"
WORDMARK_FONT = ROOT / "fonts" / "AlfaSlabOne-Regular.ttf"
TAGLINE_FONT = ROOT / "fonts" / "IBMPlexMono-SemiBold.ttf"

# The palette is sampled from the logo itself.
INK = (0x13, 0x10, 0x10, 255)
CREAM = (0xF7, 0xE2, 0xCA, 255)
RED = (0xD4, 0x51, 0x33, 255)
# A shade darker than the cream, so the shark's cream belly stays visible on it.
PAPER = (0xEC, 0xCF, 0xAB, 255)

WORDMARK = "JAWS"
TAGLINE = "ONE PLATFORM FOR EVERY PROJECT ON AWS"

# Everything is drawn at SCALE times its final size and scaled down once,
# which anti-aliases the card's outlines.
SCALE = 4


def trimmed_logo() -> Image.Image:
    """The logo cropped to its visible pixels."""
    logo = Image.open(SOURCE_LOGO).convert("RGBA")
    alpha = logo.getchannel("A").point(lambda v: 255 if v > 16 else 0)
    return logo.crop(alpha.getbbox())


def fit(image: Image.Image, width: int, height: int) -> Image.Image:
    """Scale an image to fit inside width x height, keeping its aspect ratio."""
    ratio = min(width / image.width, height / image.height)
    size = (round(image.width * ratio), round(image.height * ratio))
    return image.resize(size, Image.Resampling.LANCZOS)


def paste_centered(canvas: Image.Image, image: Image.Image) -> None:
    left = (canvas.width - image.width) // 2
    top = (canvas.height - image.height) // 2
    canvas.alpha_composite(image, (left, top))


def logo(size: int = 1024, padding: float = 0.04) -> Image.Image:
    """The logo on a transparent square, for places that supply a background."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = round(size * (1 - 2 * padding))
    paste_centered(canvas, fit(trimmed_logo(), inner, inner))
    return canvas


def avatar(size: int = 1024, padding: float = 0.13) -> Image.Image:
    """The logo on a solid paper square, for avatars cropped to a circle."""
    canvas = Image.new("RGBA", (size, size), PAPER)
    inner = round(size * (1 - 2 * padding))
    paste_centered(canvas, fit(trimmed_logo(), inner, inner))
    return canvas.convert("RGB")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    """A font with the basic layout engine on every platform.

    Pillow uses Raqm for text layout where its build has it (Linux) and the
    basic engine where it does not (macOS), and the two place glyphs a little
    differently. Forcing the basic engine renders identically everywhere.
    """
    return ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.BASIC)


def tracked_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    tracking: float,
) -> float:
    """Draw text letter by letter with extra spacing; returns the end x."""
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill, anchor="ls")
        x += font.getlength(char) + tracking
    return x - tracking


def banner(width: int = 1280, height: int = 320) -> Image.Image:
    """The README banner: a paper flash-sheet card with the logo and wordmark."""
    s = SCALE
    w, h = width * s, height * s
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # The card, with a heavy outer line and a fine inner one, like a flash sheet.
    radius = 28 * s
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=INK)
    border = 7 * s
    draw.rounded_rectangle(
        (border, border, w - 1 - border, h - 1 - border),
        radius=radius - border,
        fill=PAPER,
    )
    inset = 17 * s
    draw.rounded_rectangle(
        (inset, inset, w - 1 - inset, h - 1 - inset),
        radius=radius - inset + 4 * s,
        outline=INK,
        width=2 * s,
    )

    # The logo, on the left.
    mark = fit(trimmed_logo(), 400 * s, 236 * s)
    mark_left = 64 * s
    canvas.alpha_composite(mark, (mark_left, (h - mark.height) // 2))

    # The wordmark, with an offset red shadow, and the tagline under a red rule.
    text_left = mark_left + mark.width + 44 * s
    wordmark_font = font(WORDMARK_FONT, 150 * s)
    tagline_font = font(TAGLINE_FONT, 27 * s)
    baseline = 186 * s
    shadow = 7 * s
    tracking = 6 * s
    tracked_text(draw, (text_left + shadow, baseline + shadow), WORDMARK, wordmark_font, RED, tracking)
    wordmark_right = tracked_text(draw, (text_left, baseline), WORDMARK, wordmark_font, INK, tracking)

    rule_top = baseline + 30 * s
    tagline_right = tracked_text(draw, (text_left, rule_top + 52 * s), TAGLINE, tagline_font, INK, 2.5 * s)
    rule_right = max(wordmark_right + shadow, tagline_right)
    draw.rectangle((text_left, rule_top, rule_right, rule_top + 5 * s), fill=RED)

    return canvas.resize((width, height), Image.Resampling.LANCZOS)


ASSETS = {
    "assets/logo/jaws-logo.png": logo,
    "assets/avatar/jaws-avatar.png": avatar,
    "assets/banner/jaws-readme-banner.png": banner,
}


# The largest mean difference per channel, out of 255, that still counts as
# the same image. It absorbs anti-aliasing differences between platforms and
# catches any real change to what is drawn.
TOLERANCE = 1.0


def differs(committed: Path, rendered: Image.Image) -> float | None:
    """The mean per-channel difference, or None when the sizes differ."""
    with Image.open(committed) as image:
        current = image.convert("RGBA")
    rendered = rendered.convert("RGBA")
    if current.size != rendered.size:
        return None
    return max(ImageStat.Stat(ImageChops.difference(current, rendered)).mean)


def main(argv: list[str]) -> int:
    check = argv == ["--check"]
    stale = []
    for relative, render in ASSETS.items():
        path = ROOT / relative
        image = render()
        if check:
            difference = differs(path, image) if path.is_file() else None
            if difference is None or difference > TOLERANCE:
                stale.append(relative)
                print(f"  STALE  {relative}  (difference: {difference})")
            else:
                print(f"  ok     {relative}  (difference: {difference:.3f})")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, optimize=True)
        print(f"{relative}  {image.width}x{image.height}  {path.stat().st_size // 1024} KiB")
    if stale:
        print("Run `uv run scripts/render.py` and commit the assets it writes.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
