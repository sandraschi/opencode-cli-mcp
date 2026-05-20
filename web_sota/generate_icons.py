import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = r"D:\Dev\repos\opencode-cli-mcp\web_sota\public\icons"
SIZE = 256
S2 = SIZE // 2
ACCENT = (59, 130, 246)
PINK = (236, 72, 153)
GREEN = (34, 197, 94)
PURPLE = (168, 85, 247)
ORANGE = (249, 115, 22)
TEAL = (20, 184, 166)
RED = (239, 68, 68)
YELLOW = (234, 179, 8)
CYAN = (6, 182, 212)


def glass_panel(draw, pad=24):
    x0, y0 = pad, pad
    x1, y1 = SIZE - pad, SIZE - pad
    r = 48

    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([x0 + 6, y0 + 6, x1 + 6, y1 + 6], radius=r, fill=(0, 0, 0, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    draw.bitmap((0, 0), shadow, fill=None)

    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=(255, 255, 255, 20), outline=(255, 255, 255, 50), width=4)

    for i in range(y0, y0 + (y1 - y0) // 2, 2):
        alpha = int(18 * (1 - (i - y0) / ((y1 - y0) // 2)))
        if alpha > 0:
            draw.line([(x0 + 4, i), (x1 - 4, i)], fill=(255, 255, 255, alpha), width=1)


def glow(draw, cx, cy, color, radius=40, intensity=30):
    for i in range(radius, 0, -2):
        a = int(intensity * (1 - i / radius))
        if a <= 0:
            continue
        draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(*color, a))


def save(im, name):
    im.save(os.path.join(OUT, f"{name}.png"), "PNG")


def _load_font(size):
    try:
        return ImageFont.truetype("segoeui.ttf", size)
    except OSError:
        return ImageFont.load_default()


def icon_dashboard():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    s, gap = 32, 16
    ox, oy = 80, 80
    glow(draw, S2, S2, ACCENT, 48)
    for row in range(2):
        for col in range(2):
            x = ox + col * (s + gap)
            y = oy + row * (s + gap)
            draw.rounded_rectangle([x, y, x + s, y + s], radius=8, fill=(*ACCENT, 235))
            o = (255, 255, 255, 80)
            box = (x + 2, y + 2, x + s - 2, y + s - 2)
            draw.rounded_rectangle(box, radius=8, fill=(*ACCENT, 245), outline=o, width=2)
    save(im, "dashboard")


def icon_sessions():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ACCENT, 48)
    for i, w in enumerate([72, 56, 72]):
        y = 88 + i * 36
        cx = S2
        draw.rounded_rectangle([cx - w // 2 - 2, y - 2, cx + w // 2 + 2, y + 14 + 2], radius=8, fill=(*ACCENT, 140))
        draw.rounded_rectangle([cx - w // 2, y, cx + w // 2, y + 14], radius=8, fill=(*ACCENT, 245))
        draw.rounded_rectangle([cx - w // 2, y, cx - w // 2 + 10, y + 14], radius=4, fill=(255, 255, 255, 90), width=2)
    save(im, "sessions")


def icon_tools():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ACCENT, 48)
    pts = [
        (88, 92), (148, 92), (148, 104), (108, 104), (108, 120), (148, 120),
        (148, 132), (88, 132), (88, 120), (128, 120), (128, 104), (88, 104),
    ]
    draw.polygon(pts, fill=(*ACCENT, 245))
    draw.polygon(pts, outline=(255, 255, 255, 60), width=2)
    pts2 = [(144, 136), (164, 156), (156, 164), (136, 144)]
    draw.polygon(pts2, fill=(*ACCENT, 245))
    draw.polygon(pts2, outline=(255, 255, 255, 60), width=2)
    save(im, "tools")


def icon_apps():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ACCENT, 48)
    positions = [(68, 68), (96, 68), (124, 68), (68, 96), (96, 96), (124, 96), (68, 124), (96, 124), (124, 124)]
    for i, (x, y) in enumerate(positions):
        is_active = i in (0, 4, 8)
        c = (*ACCENT, 245) if is_active else (255, 255, 255, 120)
        draw.rounded_rectangle([x, y, x + 28, y + 28], radius=6, fill=c)
        if is_active:
            draw.rounded_rectangle([x + 2, y + 2, x + 26, y + 26], radius=6, outline=(255, 255, 255, 60), width=2)
    save(im, "apps")


def icon_chat():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ACCENT, 48)
    bx, by, bw, bh = 68, 72, 120, 84
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=24, fill=(*ACCENT, 235))
    draw.rounded_rectangle([bx + 2, by + 2, bx + bw - 2, by + bh - 2], radius=24, outline=(255, 255, 255, 60), width=2)
    tri = [(bx + 20, by + bh), (bx + 20, by + bh + 20), (bx + 36, by + bh)]
    draw.polygon(tri, fill=(*ACCENT, 235))
    draw.polygon(tri, outline=(255, 255, 255, 60), width=2)
    for i, w in enumerate([64, 48, 56]):
        ly = by + 20 + i * 20
        draw.rounded_rectangle([bx + 24, ly, bx + 24 + w, ly + 10], radius=4, fill=(255, 255, 255, 200))
    save(im, "chat")


def icon_help():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ACCENT, 48)
    cx, cy, r = S2, 116, 48
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*ACCENT, 235))
    draw.ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], outline=(255, 255, 255, 60), width=3)
    font = _load_font(72)
    draw.text((cx - 24, cy - 38), "?", fill=(255, 255, 255, 245), font=font)
    save(im, "help")


def icon_settings():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ACCENT, 48)
    cx, cy, r_out, r_in = S2, S2, 48, 24
    draw.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=None, outline=(*ACCENT, 235), width=10)
    draw.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=(*ACCENT, 245))
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        ex = cx + int(r_out * 1.45 * math.cos(rad))
        ey = cy + int(r_out * 1.45 * math.sin(rad))
        draw.ellipse([ex - 10, ey - 10, ex + 10, ey + 10], fill=(*ACCENT, 235))
    save(im, "settings")


def icon_status():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ACCENT, 48)
    pts = [(52, 152), (76, 144), (96, 120), (112, 136), (132, 88), (148, 104), (168, 80), (204, 80)]
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=(*ACCENT, 235), width=6)
    for p in pts:
        draw.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=(*ACCENT, 245))
    draw.ellipse([pts[4][0] - 12, pts[4][1] - 12, pts[4][0] + 12, pts[4][1] + 12], fill=(*ACCENT, 255))
    save(im, "status")


def icon_apidocs():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ACCENT, 48)
    doc = [(76, 60), (76, 196), (164, 196), (180, 180), (180, 60)]
    draw.polygon(doc, fill=(*ACCENT, 200))
    draw.polygon(doc, outline=(255, 255, 255, 60), width=2)
    draw.polygon([(164, 60), (164, 80), (180, 80)], fill=(*ACCENT, 245))
    draw.polygon([(164, 60), (164, 80), (180, 80)], outline=(255, 255, 255, 60), width=1)
    for i, (y, w) in enumerate([(96, 64), (120, 56), (144, 48)]):
        draw.rounded_rectangle([92, y, 92 + w, y + 8], radius=4, fill=(255, 255, 255, 180))
    font = _load_font(20)
    draw.text((108, 154), "</>", fill=(255, 255, 255, 200), font=font)
    save(im, "apidocs")


def icon_avatar():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, PINK, 50, 40)
    draw.ellipse([52, 40, 204, 192], fill=(255, 215, 230, 235))
    draw.ellipse([52, 40, 204, 192], outline=(*PINK, 160), width=4)
    draw.ellipse([84, 80, 116, 116], fill=(255, 255, 255, 245))
    draw.ellipse([140, 80, 172, 116], fill=(255, 255, 255, 245))
    draw.ellipse([92, 90, 108, 110], fill=(50, 50, 70, 250))
    draw.ellipse([148, 90, 164, 110], fill=(50, 50, 70, 250))
    draw.ellipse([100, 96, 106, 104], fill=(255, 255, 255, 230))
    draw.ellipse([156, 96, 162, 104], fill=(255, 255, 255, 230))
    draw.ellipse([64, 112, 96, 136], fill=(*PINK, 100))
    draw.ellipse([160, 112, 192, 136], fill=(*PINK, 100))
    draw.ellipse([118, 128, 138, 140], fill=(*PINK, 200))
    draw.arc([116, 6, 172, 80], 180, 0, fill=(*PINK, 210), width=6)
    draw.arc([120, 8, 168, 76], 180, 0, fill=(*PINK, 140), width=4)
    save(im, "avatar")


def icon_windows_ops():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, TEAL, 50, 40)
    cx, cy = S2, S2
    hw = 60
    draw.rectangle([cx - hw, cy - hw, cx + hw, cy + hw], fill=(*TEAL, 235))
    draw.rectangle([cx - hw, cy - hw, cx + hw, cy + hw], outline=(255, 255, 255, 80), width=4)
    draw.line([cx, cy - hw, cx, cy + hw], fill=(255, 255, 255, 160), width=4)
    draw.line([cx - hw, cy, cx + hw, cy], fill=(255, 255, 255, 160), width=4)
    d = 16
    draw.ellipse([cx - d, cy - d, cx + d, cy + d], fill=(255, 255, 255, 235))
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        ex = cx + int(30 * math.cos(rad))
        ey = cy + int(30 * math.sin(rad))
        draw.ellipse([ex - 6, ey - 6, ex + 6, ey + 6], fill=(255, 255, 255, 200))
    small = [(cx - hw + 10, cy + 8), (cx - hw + 10, cy + 28), (cx - hw + 30, cy + 8)]
    for (x, y) in small:
        draw.rectangle([x, y, x + 10, y + 10], fill=(255, 255, 255, 100))
    save(im, "windows_ops")


def icon_safety():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, GREEN, 50, 50)
    cx, cy = S2, S2
    for angle in [0, 120, 240]:
        for i in range(1, 5):
            r2 = 30 + i * 12
            start_a = angle - 40 + i * 5
            end_a = angle + 40 - i * 5
            a = max(60, 220 - i * 35)
            draw.arc([cx - r2, cy - r2, cx + r2, cy + r2], start_a, end_a, fill=(*GREEN, a), width=8)
    draw.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=(*GREEN, 235))
    draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(255, 255, 255, 220))
    drip = [(cx, 108), (cx - 8, 88), (cx, 72), (cx + 8, 88)]
    draw.polygon(drip, fill=(*GREEN, 245))
    draw.ellipse([cx - 8, 100, cx + 8, 116], fill=(*GREEN, 235))
    draw.line([(cx, 72), (cx, 40)], fill=(*GREEN, 200), width=4)
    save(im, "safety")


def icon_docker():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ACCENT, 50, 40)
    cy = 144
    body = [
        (64, 156), (64, 128), (96, 128), (96, 112), (120, 112),
        (120, 96), (144, 96), (160, 112), (184, 112), (188, 120), (188, 156),
    ]
    draw.polygon(body, fill=(*ACCENT, 235))
    draw.polygon(body, outline=(255, 255, 255, 60), width=3)
    tail = [(188, 120), (212, 104), (212, 136)]
    draw.polygon(tail, fill=(*ACCENT, 235))
    draw.polygon(tail, outline=(255, 255, 255, 60), width=2)
    fin = [(136, 112), (128, 88), (148, 100)]
    draw.polygon(fin, fill=(*ACCENT, 245))
    draw.polygon(fin, outline=(255, 255, 255, 60), width=2)
    draw.ellipse([92, 118, 108, 134], fill=(255, 255, 255, 235))
    draw.ellipse([97, 123, 103, 129], fill=(30, 30, 40, 250))
    for i, (x, w, h) in enumerate([(70, 24, 16), (70, 24, 20), (70, 24, 24)]):
        oln = (255, 255, 255, 50)
        draw.rectangle([x + 4, cy - 8 - h, x + 4 + w - 8, cy - 8], fill=(*ACCENT, 180), outline=oln, width=2)
    draw.line([(96, 76), (96, 56)], fill=(*ACCENT, 160), width=4)
    draw.line([(96, 56), (116, 56)], fill=(*ACCENT, 160), width=4)
    draw.line([(116, 56), (116, 80)], fill=(*ACCENT, 160), width=4)
    save(im, "docker")


def icon_songgeneration():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, PURPLE, 50, 40)
    placements = [(80, 104), (140, 84), (108, 132)]
    for (x, y) in placements:
        r = 16
        draw.ellipse([x, y, x + r * 2, y + r * 2], fill=(*PURPLE, 245))
        draw.ellipse([x, y, x + r * 2, y + r * 2], outline=(255, 255, 255, 60), width=2)
        stem_top = y - 32
        draw.rectangle([x + r, stem_top, x + r + 4, y + r], fill=(*PURPLE, 245))
        draw.arc([x + r + 2, stem_top - 8, x + r + 16, y - r + 8], 180, 360, fill=(*PURPLE, 235), width=4)
    for i in range(2):
        pts = []
        for t in range(0, 110, 2):
            a = math.sin(t * 0.08 + i * 2.5)
            pts.append((56 + t * 1.3, 186 + a * 18 - i * 12))
        draw.line(pts, fill=(*PURPLE, 180), width=4)
    save(im, "songgeneration")


def icon_blender():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ORANGE, 50, 40)
    cx, cy, r = S2, S2, 52
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*ORANGE, 200))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 80), width=4)
    for i in range(-6, 7):
        y = cy + i * 7
        chord = int(math.sqrt(max(0, r * r - (i * 7) ** 2)))
        draw.arc([cx - chord, y - 2, cx + chord, y + 2], 0, 360, fill=(255, 255, 255, 90), width=2)
    for i in range(12):
        a = 15 + i * 30
        x = cx + int(r * 0.7 * math.cos(math.radians(a)))
        y1 = cy - int(r * 0.85 * math.sin(math.radians(a)))
        y2 = cy + int(r * 0.85 * math.sin(math.radians(a)))
        y_low, y_high = min(y1, y2), max(y1, y2)
        draw.arc([x - 2, y_low, x + 2, y_high], 0, 180, fill=(255, 255, 255, 60), width=2)
    draw.ellipse([cx - 28, cy - 36, cx - 8, cy - 16], fill=(255, 255, 255, 90))
    save(im, "blender")


def icon_dreame():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, ACCENT, 50, 40)
    cx, cy, r = S2, S2, 56
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*ACCENT, 215))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 60), width=4)
    draw.ellipse([cx - 22, cy - 44, cx + 22, cy + 0], fill=(*ACCENT, 245))
    draw.ellipse([cx - 14, cy - 38, cx + 14, cy - 10], fill=(255, 255, 255, 200))
    draw.ellipse([cx - 6, cy - 32, cx + 6, cy - 16], fill=(40, 40, 60, 245))
    bumper = 12
    bbox = [cx - r + bumper, cy - r + bumper, cx + r - bumper, cy + r - bumper]
    draw.arc(bbox, 200, 340, fill=(255, 255, 255, 130), width=6)
    for i in range(3):
        x1 = cx - 28 + i * 28
        draw.rectangle([x1, cy + 24, x1 + 14, cy + 32], fill=(255, 255, 255, 70))
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(*GREEN, 245))
    save(im, "dreame")


def icon_browser():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, GREEN, 50, 40)
    cx, cy, r = S2, S2, 60
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*GREEN, 200))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 80), width=4)
    blobs = [
        (108, 96, 20, 28), (128, 92, 16, 24), (96, 108, 24, 32),
        (148, 116, 16, 28), (132, 96, 12, 16)
    ]
    for bx, by, bw, bh in blobs:
        draw.ellipse([bx, by, bx + bw, by + bh], fill=(*GREEN, 245))
    for i in range(1, 5):
        y = cy - r + i * (2 * r) // 5
        draw.arc([cx - r, y, cx + r, y + r + 8], 0, 360, fill=(255, 255, 255, 60), width=2)
    for i in range(1, 5):
        x = cx - r + i * (2 * r) // 5
        draw.arc([x, cy - r, x + r + 8, cy + r], 270, 90, fill=(255, 255, 255, 60), width=2)
    draw.polygon([(108, 160), (148, 160), (148, 138), (168, 166), (148, 172), (148, 152)], fill=(255, 255, 255, 150))
    save(im, "browser")


def icon_wienerlinien():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, RED, 50, 40)
    draw.rounded_rectangle([48, 84, 208, 168], radius=16, fill=(*RED, 235))
    draw.rounded_rectangle([48, 84, 208, 168], radius=16, outline=(255, 255, 255, 80), width=4)
    for i, x in enumerate([60, 88, 116, 144]):
        draw.rounded_rectangle([x, 96, x + 24, 148], radius=8, fill=(150, 210, 255, 220))
    draw.rounded_rectangle([60, 78, 196, 90], radius=8, fill=(*RED, 215))
    draw.rectangle([108, 84, 116, 168], fill=(255, 255, 255, 150))
    draw.rectangle([140, 84, 148, 168], fill=(255, 255, 255, 150))
    draw.ellipse([52, 122, 60, 136], fill=(255, 255, 220, 235))
    draw.ellipse([196, 122, 204, 136], fill=(*RED, 235))
    draw.line([(42, 174), (214, 174)], fill=(200, 200, 200, 180), width=4)
    save(im, "wienerlinien")


def icon_discord():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, PURPLE, 50, 40)
    cx, cy = S2, 108
    hw, hh = 56, 44
    draw.rounded_rectangle([cx - hw, cy - hh, cx + hw, cy + hh], radius=16, fill=(*PURPLE, 235))
    draw.rounded_rectangle([cx - hw, cy - hh, cx + hw, cy + hh], radius=16, outline=(255, 255, 255, 60), width=3)
    draw.line([(cx + hw - 12, cy), (cx + hw + 20, cy - 20)], fill=(*PURPLE, 215), width=8)
    draw.ellipse([cx + hw + 12, cy - 32, cx + hw + 28, cy - 16], fill=(*PURPLE, 235))
    for x in [cx - 36, cx + 36]:
        draw.ellipse([x - 14, cy + 36, x + 14, cy + 64], fill=(*PURPLE, 180))
        draw.ellipse([x - 8, cy + 42, x + 8, cy + 58], fill=(255, 255, 255, 120))
    save(im, "discord")


def icon_virtualdj():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, CYAN, 50, 40)
    draw.arc([64, 48, 192, 136], 200, 340, fill=(*CYAN, 235), width=10)
    draw.rounded_rectangle([44, 96, 84, 168], radius=16, fill=(*CYAN, 200))
    draw.rounded_rectangle([44, 96, 84, 168], radius=16, outline=(255, 255, 255, 60), width=3)
    draw.rounded_rectangle([172, 96, 212, 168], radius=16, fill=(*CYAN, 200))
    draw.rounded_rectangle([172, 96, 212, 168], radius=16, outline=(255, 255, 255, 60), width=3)
    for x in [80, 176]:
        draw.ellipse([x - 30, 172, x + 30, 224], fill=(*CYAN, 160))
        draw.ellipse([x - 8, 196, x + 8, 208], fill=(255, 255, 255, 130))
    draw.rectangle([56, 200, 200, 210], fill=(*CYAN, 140), outline=(255, 255, 255, 50), width=2)
    draw.rectangle([112, 196, 144, 214], fill=(*CYAN, 220))
    save(im, "virtualdj")


def icon_openclaude():
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    glass_panel(draw)
    glow(draw, S2, S2, PURPLE, 50, 40)
    cx, cy = S2, 112
    draw.ellipse([64, 48, 124, 144], fill=(*PURPLE, 215))
    draw.ellipse([132, 48, 192, 144], fill=(*PURPLE, 215))
    draw.ellipse([64, 48, 124, 144], outline=(255, 255, 255, 60), width=3)
    draw.ellipse([132, 48, 192, 144], outline=(255, 255, 255, 60), width=3)
    draw.rectangle([112, 76, 144, 112], fill=(*PURPLE, 235))
    for i in range(8):
        a1 = i * 45 + 10
        a2 = a1 + 25
        x1 = cx + int(68 * math.cos(math.radians(a1)))
        y1 = cy + int(56 * math.sin(math.radians(a1)))
        x2 = cx + int(68 * math.cos(math.radians(a2)))
        y2 = cy + int(56 * math.sin(math.radians(a2)))
        draw.line([(x1, y1), (x2, y2)], fill=(*PURPLE, 120), width=2)
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x = cx + int(70 * math.cos(rad))
        y = cy + int(58 * math.sin(rad))
        draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(*PURPLE, 215))
    draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(255, 255, 255, 200))
    draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(255, 255, 255, 245))
    save(im, "openclaude")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)

    icon_dashboard()
    icon_sessions()
    icon_tools()
    icon_apps()
    icon_chat()
    icon_help()
    icon_settings()
    icon_status()
    icon_apidocs()

    icon_avatar()
    icon_windows_ops()
    icon_safety()
    icon_docker()
    icon_songgeneration()
    icon_blender()
    icon_dreame()
    icon_browser()
    icon_wienerlinien()
    icon_discord()
    icon_virtualdj()
    icon_openclaude()

    print("All 21 icons regenerated at", SIZE)
