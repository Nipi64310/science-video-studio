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


def scene(d, i, u, dur):
    t = d.t
    if i == 0:
        d.header(1, "它不陪聊，却能参与游戏")
        d.text(52, 145, "不会聊天", 65, WHITE, ease(u / 0.45))
        d.text(52, 224, "去打游戏了？", 58, CYAN, ease((u - 0.35) / 0.55))
        d.text(55, 335, "Jev", 100, BLUE, ease((u - 0.7) / 0.5))
        d.text(59, 464, "TypeSafe 的决策模型", 22, MUTED)
        p = ease((u - 1) / 2)
        d.board(602, 180, 608, 340, px=1 + 3 * p, py=3, hazard=4 + 0.35 * math.sin(u))
        for j, lab in enumerate(["左", "右", "等"]):
            d.chip(657 + j * 160, 555, 135, lab, j == 1 and u > 1)
        d.text(606, 140, "原创动画 · 原理示意", 17, MUTED)
    elif i == 1:
        d.header(2, "先把屏幕拆开")
        d.title(
            "画面给你看，状态给模型",
            "官方 Doom 演示使用整理后的状态，并非直接输入游戏画面",
        )
        d.board(53, 282, 637, 294, px=2, py=3, hazard=4)
        for j, (a, b) in enumerate(
            [
                ("角色", "位置  [2, 3]"),
                ("障碍", "位置  [4, 2]"),
                ("出口", "位置  [6, 1]"),
            ]
        ):
            q = ease((u - 0.4 - j * 0.45) / 0.65)
            x = 850 + 55 * (1 - q)
            if q > 0:
                d.rr(x, 275 + j * 98, 355, 76, "#22324A", 13, out="#3E5475")
                d.text(x + 18, 287 + j * 98, a, 19, CYAN)
                d.text(x + 95, 296 + j * 98, b, 24, WHITE, q)
        d.arrow(720, 430, 823, 430, CYAN, ease((u - 1) / 1))
        d.pulse(720, 430, 823, 430, (u * 0.4) % 1)
    elif i == 2:
        d.header(3, "先把能做的动作告诉它")
        d.title("这一步，可以怎么走？", "状态 + 问题 + 预先给定的选项")
        d.board(54, 267, 654, 317, px=1, py=3, hazard=4)
        d.panel(795, 260, 408, 100, "下一步动作", "选项由开发者定义", True)
        for j, lab in enumerate(["往左", "往右", "原地等"]):
            q = ease((u - j * 0.5) / 0.5)
            y = 411 + 50 * (1 - q)
            d.chip(787 + j * 146, y, 134, lab, j == 1 and u > 2.7)
        d.text(805, 516, "模型在这些选项里判断", 22, CYAN)
    elif i == 3:
        d.header(4, "一次判断怎样变成动作")
        d.title("它来选，程序负责按键", "动作发生以后，把新状态送回来")
        phase = clamp(u / max(dur, 1))
        movement = ease((u - 2.8) / 0.8)
        d.board(
            52, 277, 644, 306, px=1 + movement * 1.5, py=3, hazard=4 + 0.2 * math.sin(u)
        )
        d.panel(797, 272, 402, 106, "Jev 选择：往右", "判断", u > 0.5)
        d.arrow(1000, 394, 1000, 442, CYAN, ease((u - 0.7) / 0.6))
        d.panel(797, 456, 402, 105, "代码 → 按右键", "执行", phase > 0.35)
        d.arrow(781, 511, 716, 511, CYAN, ease((phase - 0.3) / 0.15))
        if phase > 0.3:
            d.pulse(781, 511, 716, 511, ((phase - 0.3) * 4) % 1)
        d.line(
            [(375, 593), (375, 618), (1217, 618), (1217, 307), (1210, 307)],
            "#465E79",
            2,
        )
        d.text(738, 593, "更新状态，再来一轮", 18, MUTED)
    elif i == 4:
        d.header(5, "接回你的 Agent")
        d.title("同一个小判断，换个工作现场", "先判断怎么处理，再调用工具或模型")
        d.panel(53, 338, 238, 131, "用户请求", "你的任务")
        d.panel(465, 338, 285, 131, "Jev 判断", "该走哪条路？", True)
        d.arrow(311, 403, 445, 403)
        dest = [(848, 256, "搜索工具"), (848, 408, "模型 A"), (848, 560, "模型 B")]
        for j, (x, y, l) in enumerate(dest):
            yy = y - 45
            d.panel(x, yy, 350, 105, l, "", j == int(u / 2) % 3)
            d.arrow(770, 403, x - 18, y + 8, BLUE, ease((u - 0.4 - j * 0.15) / 0.8))
            if j == int(u / 2) % 3:
                d.pulse(770, 403, x - 18, y + 8, (u * 0.65) % 1)
    elif i == 5:
        d.header(6, "别把结构化输出当独家能力")
        d.title("普通大模型，也能做", "Jev 专门围绕这类判断来设计")
        for j, (label, sub) in enumerate(
            [("通用大模型", "生成文本，也能按格式回答"), ("Jev", "侧重决策与概率输出")]
        ):
            x = 65 + j * 628
            d.panel(x, 277, 524, 204, label, sub, j == 1)
            for k in range(3):
                d.rr(x + 45 + k * 145, 415, 123, 24, BLUE if j else "#59768C", 6)
        d.center(640, 552, "真正要比：同一任务的效果、延迟和费用", 27, CYAN)
        d.text(68, 606, "本片未进行 Jev 性能跑分", 17, MUTED)
    elif i == 6:
        d.header(7, "一个合法答案，也可能选错")
        d.title("往右，确实是个合法选项", "但右边，偏偏有个坑。")
        p = clamp(u / max(dur, 1))
        mx = ease((u - 5.1) / 1.2)
        drop = ease((u - 7.5) / 0.7)
        # draw empty board then move bot into pit
        d.board(53, 280, 720, 313, px=1 + mx, py=3 + drop * 3, pit=True, hazard=4)
        if drop > 0.8:
            d.rr(56, 598, 720, 39, BG, 0)
        d.chip(871, 280, 274, "→ 往右", True)
        d.text(884, 392, "格式  ✓", 40, GREEN)
        if p > 0.57:
            d.text(884, 463, "判断  ×", 40, ORANGE, ease((p - 0.57) / 0.12))
        d.text(876, 551, "原创反例 · 非实测翻车", 16, MUTED)
    elif i == 7:
        d.header(8, "最后，回到实际效果")
        d.title("少花了多少？选错了几次？", "接进自己的工作流，一起算。")
        for j, (a, b, c) in enumerate(
            [
                ("效果", "任务做对了吗", CYAN),
                ("延迟", "等了多久", BLUE),
                ("费用", "总共花了多少", ORANGE),
            ]
        ):
            q = ease((u - 0.1 - j * 0.22) / 0.65)
            x = 58 + j * 413
            y = 285 + 42 * (1 - q)
            d.rr(x, y, 377, 233, "#1D2C42", 21, out="#3D536D")
            d.text(x + 26, y + 26, a, 43, c, q)
            d.text(x + 27, y + 99, b, 24, WHITE, q)
            for z in range(8):
                d.rr(
                    x + 28 + z * 38, y + 160, 27, 30 + 9 * math.sin(z + u), "#32465E", 5
                )
        d.center(640, 558, "Jev 负责判断，整个系统负责把事办好。", 27)
        d.text(61, 611, "资料：TypeSafe 官方文档 · 原创原理演示", 16, MUTED)


DATA = json.loads((P / "timeline.json").read_text())


def frame(t):
    cues = DATA
    sc = cues["scenes"]
    subs = cues["subtitles"]
    dur = cues["duration"]
    idx = next((i for i, s in enumerate(sc) if s["start"] <= t < s["end"]), len(sc) - 1)
    s = sc[idx]
    d = Draw(t)
    scene(d, idx, max(0, t - s["start"]), s["end"] - s["start"])
    d.rr(0, 716, 1280, 4, "#24364D", 0)
    d.rr(0, 716, max(1, 1280 * t / dur), 4, CYAN, 0)
    cap = next((x["text"] for x in subs if x["start"] <= t < x["end"]), "")
    if cap:
        tw = font(29).getlength(cap) / K
        d.rr(640 - tw / 2 - 20, 654, tw + 40, 48, "#080D16", 12)
        d.center(640, 663, cap, 29)
    if idx > 0 and t - s["start"] < 0.18:
        alpha = 1 - (t - s["start"]) / 0.18
        ov = Image.new("RGBA", (W, H), (8, 13, 23, int(100 * alpha)))
        d.im = Image.alpha_composite(d.im.convert("RGBA"), ov).convert("RGB")
    return d
