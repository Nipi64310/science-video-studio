from pathlib import Path
from functools import lru_cache
import json, math, subprocess, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

P = Path(__file__).resolve().parent
W, H = 1920, 1080
K = 1.5
FPS = 30
FONT = str(P.parents[1] / "assets/fonts/NotoSansSC-Regular.otf")
BLUE = "#667CFF"
CYAN = "#75E0DD"
WHITE = "#F2F2EF"
MUTED = "#9CA9BC"
ORANGE = "#FF926E"
GREEN = "#BBEA88"
BG = "#101725"


def clamp(x):
    return max(0, min(1, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def mix(a, b, x):
    return a + (b - a) * x


@lru_cache(None)
def font(sz):
    return ImageFont.truetype(FONT, round(sz * K))


@lru_cache(maxsize=1500)
def tile(txt, sz, col):
    f = font(sz)
    b = f.getbbox(txt)
    im = Image.new("RGBA", (max(1, b[2] + 8), round(sz * K * 1.65)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((2, -b[1] + sz * K * 0.12), txt, font=f, fill=col)
    return im


# subtle pre-rendered background
xx, yy = np.meshgrid(np.linspace(0, 1, W), np.linspace(0, 1, H))
g = np.exp(-((xx - 0.68) ** 2 + (yy - 0.27) ** 2) * 5)
a = np.zeros((H, W, 3), dtype=np.uint8)
for c, (v, amp) in enumerate([(13, 11), (20, 14), (34, 26)]):
    a[:, :, c] = v + amp * g
BACKGROUND = Image.fromarray(a)


class Draw:
    def __init__(self, t):
        self.im = BACKGROUND.copy()
        self.d = ImageDraw.Draw(self.im)
        self.t = t

    def rr(self, x, y, w, h, col, r=14, out=None, lw=1):
        self.d.rounded_rectangle(
            (int(x * K), int(y * K), int((x + w) * K), int((y + h) * K)),
            radius=int(r * K),
            fill=col,
            outline=out,
            width=max(1, int(lw * K)),
        )

    def text(self, x, y, txt, sz=28, col=WHITE, alpha=1):
        im = tile(txt, sz, col)
        if alpha < 0.999:
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda z: int(z * clamp(alpha))))
        self.im.paste(im, (round(x * K), round(y * K)), im)

    def center(self, x, y, txt, sz=28, col=WHITE):
        self.text(x - font(sz).getlength(txt) / K / 2, y, txt, sz, col)

    def line(self, pts, col=MUTED, w=2):
        self.d.line(
            [(round(x * K), round(y * K)) for x, y in pts],
            fill=col,
            width=max(1, round(w * K)),
            joint="curve",
        )

    def circle(self, x, y, r, col):
        self.d.ellipse(
            (int((x - r) * K), int((y - r) * K), int((x + r) * K), int((y + r) * K)),
            fill=col,
        )

    def arrow(self, x, y, ex, ey, col=BLUE, p=1):
        ex, ey = mix(x, ex, p), mix(y, ey, p)
        self.line([(x, y), (ex, ey)], col, 2)
        if p > 0.95:
            ang = math.atan2(ey - y, ex - x)
            self.line(
                [
                    (ex - 9 * math.cos(ang - 0.5), ey - 9 * math.sin(ang - 0.5)),
                    (ex, ey),
                    (ex - 9 * math.cos(ang + 0.5), ey - 9 * math.sin(ang + 0.5)),
                ],
                col,
                2,
            )

    def pulse(self, x, y, ex, ey, q, col=CYAN):
        for j in range(4):
            z = clamp(q - j * 0.025)
            self.circle(mix(x, ex, z), mix(y, ey, z), 4 - j * 0.6, col)

    def chip(self, x, y, w, label, active=False):
        self.rr(x, y, w, 54, BLUE if active else "#202D43", 12, out="#495B7A")
        self.center(x + w / 2, y + 13, label, 23)

    def panel(self, x, y, w, h, label, sub="", active=False):
        self.rr(x, y + 5, w, h, "#080F1A", 18)
        self.rr(
            x,
            y,
            w,
            h,
            "#273756" if active else "#1A273B",
            18,
            out=BLUE if active else "#34445D",
        )
        self.center(x + w / 2, y + 24, label, 29, CYAN if active else WHITE)
        if sub:
            self.center(x + w / 2, y + 70, sub, 17, MUTED)

    def bot(self, x, y, size=40, drop=0):
        self.circle(x, y + size * 0.65, size * 0.54, "#0A111D")
        self.rr(x - size / 2, y - size / 2 + drop, size, size, CYAN, 10)
        self.rr(
            x - size * 0.3,
            y - size * 0.05 + drop,
            size * 0.6,
            size * 0.28,
            "#142738",
            4,
        )
        for z in [-0.17, 0.17]:
            self.circle(x + z * size, y + size * 0.08 + drop, size * 0.055, WHITE)
        self.line([(x, y - size * 0.5 + drop), (x, y - size * 0.72 + drop)], CYAN, 2)
        self.circle(x, y - size * 0.77 + drop, 3, ORANGE)

    def board(self, x, y, w, h, px=1, py=3, pit=False, hazard=4, labels=False):
        self.rr(x - 8, y - 8, w + 16, h + 16, "#111D2E", 20, out="#435573")
        cw = w / 8
        ch = h / 5
        for row in range(5):
            for col in range(8):
                self.rr(
                    x + col * cw + 2,
                    y + row * ch + 2,
                    cw - 4,
                    ch - 4,
                    "#213149" if (col + row) % 2 == 0 else "#1D2B40",
                    5,
                )
        # subtle track and moving hazard
        self.line(
            [
                (x + 1.5 * cw, y + 3.5 * ch),
                (x + 6.5 * cw, y + 3.5 * ch),
                (x + 6.5 * cw, y + 1.5 * ch),
            ],
            "#334D62",
            2,
        )
        self.rr(x + 6 * cw + 9, y + ch + 9, cw - 18, ch - 18, "#35624B", 8, out=GREEN)
        self.center(x + 6.5 * cw, y + ch + 17, "出口", 16, GREEN)
        self.rr(x + hazard * cw + 10, y + 2 * ch + 9, cw - 20, ch - 18, ORANGE, 7)
        if pit:
            self.rr(
                x + 2 * cw + 6,
                y + 3 * ch + 6,
                cw - 12,
                ch - 12,
                "#060A10",
                8,
                out=ORANGE,
                lw=2,
            )
            self.line(
                [
                    (x + 2 * cw + 10, y + 3 * ch + 12),
                    (x + 3 * cw - 12, y + 3 * ch + 12),
                ],
                "#85493D",
                3,
            )
        if py < 4.7:
            self.bot(x + (px + 0.5) * cw, y + (py + 0.5) * ch, min(cw, ch) * 0.59)
        if labels:
            self.text(x, y + h + 22, "角色位置  →  游戏状态", 18, MUTED)

    def header(self, n, lab):
        self.text(48, 28, "JEV / 一分钟拆开看", 18, MUTED)
        self.text(925, 28, "QWEN AUDIO · TTS NEXT", 16, MUTED)
        self.rr(48, 75, 42, 34, BLUE, 9)
        self.center(69, 82, f"{n:02}", 17)
        self.text(103, 80, lab, 20, MUTED)

    def title(self, a, b=None):
        self.text(48, 126, a, 49)
        if b:
            self.text(50, 187, b, 20, MUTED)
