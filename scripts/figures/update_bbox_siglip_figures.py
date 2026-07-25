from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from figure2_linear_layout import create_figure as create_linear_figure_2


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = PROJECT_ROOT / "SCIE용" / "산출물" / "도식"
FIGURE_1 = FIGURE_DIR / "figure1_overall_architecture.png"
FIGURE_2 = FIGURE_DIR / "figure2_g4_reranking.png"

NAVY = (27, 59, 99)
BODY = (88, 97, 108)
BLUE_FILL = (238, 244, 250)


def font(size, bold=False):
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def centered_lines(draw, box, lines, text_font, fill, spacing=7):
    x1, y1, x2, y2 = box
    bounds = [draw.textbbox((0, 0), line, font=text_font) for line in lines]
    heights = [bound[3] - bound[1] for bound in bounds]
    total = sum(heights) + spacing * max(0, len(lines) - 1)
    y = y1 + ((y2 - y1) - total) / 2
    for line, bound, height in zip(lines, bounds, heights):
        width = bound[2] - bound[0]
        draw.text((x1 + ((x2 - x1) - width) / 2, y), line, font=text_font, fill=fill)
        y += height + spacing


def update_figure_1():
    image = Image.open(FIGURE_1).convert("RGB")
    draw = ImageDraw.Draw(image)
    box = (820, 300, 1110, 470)
    draw.rectangle((box[0] + 5, box[1] + 5, box[2] - 5, box[3] - 5), fill=BLUE_FILL)
    centered_lines(draw, (835, 312, 1095, 385), ["Text-Image", "Association"], font(33, bold=True), NAVY, spacing=1)
    centered_lines(
        draw,
        (832, 392, 1098, 456),
        ["BBox candidate filtering", "SigLIP semantic ranking"],
        font(19),
        BODY,
        spacing=3,
    )
    image.save(FIGURE_1)


def update_figure_2():
    create_linear_figure_2(FIGURE_2, "en")


if __name__ == "__main__":
    update_figure_1()
    update_figure_2()
    print(FIGURE_1)
    print(FIGURE_2)
