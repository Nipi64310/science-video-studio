from pathlib import Path
import json, math, sys, subprocess, time
from PIL import Image, ImageDraw
from graphics import Draw as Base, font, tile, ease, clamp, mix, K, W, H, FPS

P = Path(__file__).resolve().parent
DATA = (
    json.loads((P / "timeline.json").read_text())
    if (P / "timeline.json").exists()
    else None
)
INK = "#17223B"
PAPER = "#F2F0E8"
BLUE = "#5671ED"
CYAN = "#7AE0D8"
ORANGE = "#EE8761"
GREEN = "#A7DA87"
WHITE = "#F4F3ED"


class Draw(Base):
    def __init__(self, t, light=False):
        super().__init__(t)
        self.light = light
        self.fg = INK if light else WHITE
        self.muted = "#607087" if light else "#A1B0C8"
        self.accent = "#315DD2" if light else CYAN
        self.boxes = []
        if light:
            self.im = Image.new("RGB", (W, H), PAPER)
            self.d = ImageDraw.Draw(self.im)

    def text(self, x, y, txt, sz=28, col=None, alpha=1):
        col = col or self.fg
        super().text(x, y, txt, sz, col, alpha)
        if alpha > 0.8 and txt.strip():
            bb = font(sz).getbbox(txt)
            self.boxes.append(
                (
                    x,
                    y + sz * 0.12,
                    x + font(sz).getlength(txt) / K,
                    y + sz * 0.12 + (bb[3] - bb[1]) / K,
                    txt,
                )
            )

    def center(self, x, y, txt, sz=28, col=None):
        self.text(x - font(sz).getlength(txt) / K / 2, y, txt, sz, col)

    def header(self, label):
        self.text(53, 28, "Jev / 不会聊天，怎么打游戏？", 18, self.muted)
        self.text(935, 28, "原理动画 · 三分钟版", 18, self.muted)
        self.rr(53, 75, 5, 29, BLUE, 2)
        self.text(73, 77, label, 21, self.muted)

    def title(self, a, b=None):
        self.text(53, 128, a, 46)
        if b:
            self.text(55, 192, b, 22, self.muted)

    def card(self, x, y, w, h, label, sub="", active=False, size=27):
        fill = (
            ("#DBE4FC" if active else "#FFFFFF")
            if self.light
            else ("#2B4164" if active else "#1E2D43")
        )
        self.rr(
            x,
            y,
            w,
            h,
            fill,
            18,
            out=BLUE if active else ("#CDD3DA" if self.light else "#3B4E68"),
        )
        self.center(x + w / 2, y + 24, label, size, self.accent if active else self.fg)
        if sub:
            self.center(x + w / 2, y + 70, sub, 20, self.muted)

    def button(self, x, y, w, label, active=False):
        self.rr(
            x,
            y,
            w,
            58,
            BLUE if active else ("#E1E5ED" if self.light else "#22344D"),
            12,
        )
        self.center(x + w / 2, y + 14, label, 25, WHITE if active else self.fg)

    def foot(self, s):
        self.text(55, 616, s, 17, self.muted)

    def rule(self, x, y, w, txt, col=None):
        self.rr(x, y, w, 56, col or BLUE, 12)
        self.center(x + w / 2, y + 13, txt, 25, WHITE)


def marker(s, phrase, default):
    text = s["text"]
    pos = text.find(phrase)
    if pos < 0:
        return default
    for c in s["chars"]:
        if c["index"] >= pos:
            return c["start"] - s["start"]
    return default


def sc(d, s, u):
    i = s["id"]
    dur = s["end"] - s["start"]
    p = clamp(u / dur)
    at = lambda phrase, fallback=0: marker(s, phrase, fallback)
    if i == 0:
        d.header("从一个反常识的小实验开始")
        d.text(55, 149, "不会聊天", 66)
        d.text(54, 232, "怎么打游戏？", 61, CYAN)
        d.text(58, 362, "Jev", 97, BLUE)
        d.text(62, 492, "TypeSafe 的决策模型", 25, d.muted)
        q = ease((u - at("打游戏")) / 1.2)
        d.board(
            610, 224, 586, 298, px=1 + 2 * q, py=3, hazard=4 + 0.3 * math.sin(u * 0.7)
        )
        for j, l in enumerate(["左", "右", "等"]):
            d.button(645 + j * 172, 561, 144, l, j == 1 and q > 0)
        d.text(615, 172, "官方展示过 Doom · 此处为原创示意", 19, d.muted)
    elif i == 1:
        d.header("先看接口，再看能力")
        d.title("不回一段话，回一个判断")
        q = ease((u - at("直接给程序")) / 0.65)
        d.card(56, 294, 246, 144, "输入", "状态与问题")
        d.arrow(321, 365, 423, 365, BLUE, q)
        d.card(444, 294, 263, 144, "Jev", "判断", True)
        d.arrow(727, 365, 809, 365, BLUE, q)
        labs = [("选哪个", "Choice"), ("打几分", "Score"), ("是否成立", "Noul")]
        for j, (a, b) in enumerate(labs):
            v = ease((u - at(["选哪个", "打几分", "某个条件"][j])) / 0.55)
            if v > 0:
                d.card(835 + 40 * (1 - v), 244 + j * 118, 375, 99, a, b, True, 26)
        d.foot("输出由预先定义的类型约束；不是自由生成聊天文本")
    elif i == 2:
        d.header("别把游戏画面当成模型输入")
        d.title(
            "画面给你看，状态交给模型", "官方 Doom 演示输入结构化文字状态，不是游戏截图"
        )
        d.board(59, 290, 628, 279, px=2, py=3, hazard=4)
        for j, (label, val, key) in enumerate(
            [
                ("角色", "[2, 3]", "角色在哪"),
                ("障碍", "[4, 2]", "障碍在哪"),
                ("出口", "[6, 1]", "出口在哪"),
            ]
        ):
            v = ease((u - at(key)) / 0.45)
            if v > 0:
                y = 281 + j * 100
                d.rr(856, y, 350, 79, "#213650", 13)
                d.text(882, y + 21, label, 25, CYAN)
                d.text(1046, y + 21, val, 25)
        d.arrow(714, 429, 822, 429, CYAN, ease((u - at("状态交给")) / 0.5))
        d.foot("地图与坐标是本片自编示意，非 Doom 实际请求")
    elif i == 3:
        d.header("选择 → 执行 → 更新")
        d.title("按钮亮了，角色还不能先动")
        select = at("模型选完")
        execute = at("程序负责")
        move = at("角色动了")
        again = at("再问下一次")
        right = ease((u - move) / 0.75)
        d.board(58, 300, 622, 267, px=1 + right, py=3, hazard=4)
        for j, l in enumerate(["往左", "往右", "原地等"]):
            d.button(
                758 + j * 151,
                275,
                137,
                l,
                (j == 1 and select <= u < again) or (j == 2 and u >= again),
            )
        d.card(784, 412, 390, 107, "程序按键", "执行器", u >= execute)
        d.arrow(980, 344, 980, 394, CYAN, ease((u - execute) / 0.4))
        d.arrow(765, 464, 705, 464, CYAN, ease((u - move + 0.3) / 0.3))
        if u >= move:
            d.pulse(765, 464, 705, 464, clamp((u - move) / 0.7))
        if u >= again:
            d.line(
                [(370, 580), (370, 609), (1234, 609), (1234, 304), (1215, 304)], CYAN, 2
            )
            d.text(810, 562, "状态更新，再问一轮", 22, CYAN)
        else:
            d.text(797, 563, "判断和执行，各有分工", 22, d.muted)
    elif i == 4:
        d.header("三种小判断，各问各的问题")
        phase = at("也可以问")
        if u < phase:
            d.title("评分，先把标准写清楚", "Score：分数对应有顺序、可解释的档位")
            labs = ["远离路线", "路线可能相交", "已经逼近"]
            for j, l in enumerate(labs):
                x = 80 + j * 414
                d.card(x, 292, 360, 125, str(j), l, j == 1, 33)
            d.line([(245, 476), (1073, 476)], d.muted, 4)
            for j in range(3):
                d.circle(245 + j * 414, 476, 7, BLUE)
            v = ease((u - at("按标准评分")) / 0.7)
            x = 245 + 1.1 * 414 * v
            d.circle(x, 476, 13, BLUE)
            d.center(x, 508, "示意分数 1.1" if v > 0.98 else "按标准评分", 25, BLUE)
            d.foot("假设档位概率为 0.1 / 0.7 / 0.2；分数不是百分比")
        else:
            d.title("“是”的概率，不是露出了多少", "Noul：这个条件成立的可能性")
            d.card(73, 292, 479, 192, "出口出现了吗？", "这是一个是非问题", True, 34)
            d.arrow(579, 386, 692, 386, BLUE)
            d.text(754, 283, "0.9", 91, BLUE)
            d.text(758, 409, "回答“是”的概率", 27)
            q = ease((u - phase) / 0.6)
            d.rr(746, 467, 411, 25, "#D7DBE3", 8)
            d.rr(746, 467, 411 * 0.9 * q, 25, BLUE, 8)
            d.center(640, 561, "不是“出口露出了 90%”", 32, INK)
            d.foot("0.9 为讲解用假设值，非模型实测")
    elif i == 5:
        d.header("一个很自然的质疑")
        a = at("分支当然")
        b = at("同一句")
        c = at("什么信息")
        if u < a:
            d.center(640, 234, "这不就是个", 55)
            d.center(640, 330, "高级 if？", 94, CYAN)
            d.center(640, 508, "条件 → 分支", 30, d.muted)
        else:
            d.title("分支不难，难的是前面那道判断")
            d.rr(66, 271, 682, 102, "#243652", 18)
            d.text(91, 299, "“改完还是报错”", 38)
            labs = (
                ("缺少报错、环境信息", "先问清楚")
                if u >= c
                else ("有具体报错堆栈", "继续排查")
            )
            if u >= b:
                d.card(69, 419, 677, 133, labs[0], "同一句话，上下文不同", True, 30)
                d.arrow(768, 477, 877, 477, CYAN)
                d.card(898, 419, 310, 133, labs[1], "程序进入对应分支", True, 27)
            d.foot("上下文判断可以用模型；清楚、稳定的条件继续用代码")
    elif i == 6:
        d.header("普通大模型也会，为什么还要它？")
        d.title("结构化输出，并非 Jev 独有")
        for j, (a, b) in enumerate(
            [("通用大模型", "文本生成，也能按格式回答"), ("Jev", "围绕判断任务设计")]
        ):
            x = 72 + j * 621
            d.card(x, 284, 538, 209, a, b, j == 1, 35)
            for k in range(3):
                d.rr(x + 56 + k * 145, 435, 125, 23, BLUE if j else "#89A0AD", 6)
        if u >= at("官方介绍"):
            d.center(640, 528, "官方描述：并行给出判断结果", 27, BLUE)
        if u >= at("同一批任务"):
            d.rule(280, 576, 720, "同一批任务，再比效果、延迟、费用")
        else:
            d.foot("接口概念示意；没有模拟两种模型的实际响应速度")
    elif i == 7:
        d.header("把这道判断，放回 Agent")
        d.title("先分流，再干活")
        d.card(58, 313, 243, 132, "你的请求", "一个待办任务")
        d.card(425, 313, 280, 132, "Jev 判断", "先选处理路线", True)
        d.arrow(321, 378, 405, 378, CYAN)
        for j, l in enumerate(["搜索工具", "强模型", "便宜模型"]):
            yy = 250 + j * 119
            d.card(866, yy, 340, 90, l, "", False, 27)
            d.arrow(727, 378, 844, yy + 45, CYAN, ease((u - j * 0.4) / 0.7))
        if u >= at("别忘了"):
            d.rule(139, 581, 1000, "总成本 = 分流调用 + 后续执行 + 可能的返工")
        else:
            d.foot("流程示意：分流后，工具和模型才开始实际执行")
    elif i == 8:
        d.header("不确定，也是一条有用信息")
        d.title("三个答案挤在一起，先别冲")
        probs = [0.36, 0.34, 0.30]
        for j, (pr, l) in enumerate(zip(probs, ["继续排查", "查文档", "补信息"])):
            x = 134 + j * 230
            v = ease((u - at("假设")) / 0.65)
            h = pr * 520 * v
            d.rr(x, 495 - h, 134, h, BLUE, 10)
            d.center(x + 67, 452 - h, f"{pr:.2f}", 30, BLUE)
            d.center(x + 67, 515, l, 25)
        if u >= at("可以补信息"):
            d.arrow(827, 403, 902, 403, BLUE)
            d.card(925, 342, 294, 123, "先补信息", "由程序策略决定", True, 28)
        if u >= at("置信度"):
            d.rule(174, 580, 932, "confidence ≠ 这一次答对的保证")
        else:
            d.foot("假设分布，非实测；三项概率相加为 1")
    elif i == 9:
        d.header("回到刚才那局游戏")
        d.title("按钮没越界，人掉下去了")
        move = at("选了往右")
        fall = at("掉下去了")
        mx = ease((u - move) / 0.75)
        dy = ease((u - fall) / 0.55)
        d.board(59, 284, 714, 297, px=100, py=100, pit=True, hazard=4)
        if dy < 0.96:
            d.bot(
                59 + (1.5 + mx) * 714 / 8, 284 + 3.5 * 297 / 5 + dy * 14, 35 * (1 - dy)
            )
        for j, l in enumerate(["左", "右", "等"]):
            d.button(851 + j * 126, 278, 111, l, j == 1 and mx > 0)
        d.text(879, 395, "格式  ✓", 40, GREEN)
        if u >= fall:
            d.text(879, 480, "判断  ×", 40, ORANGE)
        d.foot("原创反例，非 Jev 实测翻车：类型约束不等于答案正确")
    elif i == 10:
        d.header("把科普变成可执行的测试")
        d.title("别只记省钱，也记返工")
        headers = ["任务", "该走的路线", "实际选择", "最终完成？"]
        widths = [360, 220, 220, 275]
        xs = [70, 430, 650, 870]
        for x, w, h in zip(xs, widths, headers):
            d.rr(x, 275, w, 60, BLUE, 0)
            d.text(x + 18, 291, h, 24, WHITE)
        rows = [
            ["需要最新资料", "搜索", "待测", "待测"],
            ["复杂调试", "强模型", "待测", "待测"],
            ["简单格式转换", "便宜模型", "待测", "待测"],
        ]
        for j, row in enumerate(rows):
            if u < j * 0.5:
                continue
            for x, w, v in zip(xs, widths, row):
                d.rr(x, 337 + j * 68, w, 65, "#FFFFFF" if j % 2 == 0 else "#E4E9F1", 0)
                d.text(x + 18, 355 + j * 68, v, 23)
        d.foot("测试记录模板，不含虚构成绩；正确路线需按任务预先标注")
        if u >= at("返工"):
            d.center(640, 560, "总成本，才是最后的账单", 29, BLUE)
    elif i == 11:
        d.header("最后，把账算完整")
        d.title("小判断省下来，整件事还得办对")
        for j, (a, b, c) in enumerate(
            [("代码", "清楚、稳定的规则", CYAN), ("模型", "需要理解上下文", BLUE)]
        ):
            x = 84 + j * 627
            d.card(x, 277, 530, 149, a, b, False, 39)
        keys = ["效果", "延迟", "费用"]
        if u >= at("最后一起看"):
            for j, l in enumerate(keys):
                d.rule(158 + j * 346, 489, 294, l, BLUE)
        d.center(640, 578, "Jev 负责判断，系统负责把事办好。", 28, CYAN)
        d.foot("资料：TypeSafe 官方文档｜画面原创｜Next 参考音配音")


def frame(t):
    s = next(
        (x for x in DATA["scenes"] if x["start"] <= t < x["end"]), DATA["scenes"][-1]
    )
    d = Draw(t, s["id"] in [1, 4, 6, 8, 10])
    sc(d, s, t - s["start"])
    cap = next((c["text"] for c in DATA["subtitles"] if c["start"] <= t < c["end"]), "")
    if cap:
        tw = font(29).getlength(cap) / K
        d.rr(640 - tw / 2 - 22, 655, tw + 44, 49, "#0A1220", 11)
        d.center(640, 665, cap, 29, WHITE)
    d.rr(0, 716, 1280, 4, "#C7D0DF" if d.light else "#304459", 0)
    d.rr(0, 716, max(1, 1280 * t / DATA["duration"]), 4, BLUE, 0)
    return d
