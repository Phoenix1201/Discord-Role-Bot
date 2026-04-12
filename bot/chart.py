from PIL import Image, ImageDraw, ImageFont
import math
from io import BytesIO
from utils import get_enabled_entries, normalize_color
import os

FONT_PATH = os.path.join(os.path.dirname(__file__), "NotoSansJP-VariableFont_wght.ttf")

FONT = ImageFont.truetype(FONT_PATH, 16)
SMALL_FONT = ImageFont.truetype(FONT_PATH, 12)

def create_pie_chart(entries):
    size = 260
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)

    center = size // 2
    radius = 95

    entries = get_enabled_entries(entries)
    total = sum(e["weight"] for e in entries.values())
    if total <= 0:
        total = 1

    start_angle = -90  # 上スタート

    sorted_entries = sorted(entries.items(), key=lambda x: x[1]["weight"], reverse=True)

    for i, (uid, e) in enumerate(sorted_entries, start=1):
        weight = e["weight"]
        angle = 360 * (weight / total)
        color_val = normalize_color(e.get("color"))
        hex_color = f"#{color_val:06x}"

        # ===== 円 =====
        draw.pieslice(
            [
                center - radius,
                center - radius,
                center + radius,
                center + radius
            ],
            start=start_angle,
            end=start_angle + angle,
            fill=hex_color,
            outline="white"
        )

        percent = (weight / total * 100)
        mid_angle = math.radians(start_angle + angle / 2)

        # ===== 中に％ =====
        if percent >= 5:
            text = f"{percent:.0f}%"

            tx = center + (radius * 0.6) * math.cos(mid_angle)
            ty = center + (radius * 0.6) * math.sin(mid_angle)

            bbox = draw.textbbox((0, 0), text, font=FONT)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]

            draw.text(
                (tx - w/2, ty - h/2),
                text,
                fill="black",
                font=FONT
            )

        # ===== 外側：番号だけ =====
        label = str(i)

        lx = center + (radius * 1.15) * math.cos(mid_angle)
        ly = center + (radius * 1.15) * math.sin(mid_angle)

        bbox = draw.textbbox((0, 0), label, font=FONT)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        draw.text(
            (lx - w/2, ly - h/2),
            label,
            fill="black",
            font=FONT
        )

        start_angle += angle

    # タイトル
    draw.text((10, 5), "Participants", fill="black", font=SMALL_FONT)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
