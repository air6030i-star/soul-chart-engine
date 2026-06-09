# -*- coding: utf-8 -*-
"""
hd_report.py
============
人類圖個人報告 HTML 生成器（API 版）
從 gen_report.py 提取 build_html / bodygraph_svg，供 server.py 的 /api/hd_report 使用。

依賴：hd_data.json、gates_64.json（與本檔同目錄）
"""
from __future__ import annotations
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ── 載入靜態資料 ──────────────────────────────────────────────
with open(HERE / "hd_data.json", encoding="utf-8") as f:
    HD_DATA: dict = json.load(f)

with open(HERE / "gates_64.json", encoding="utf-8") as f:
    GATES: dict = json.load(f)

ENGINE_SRC = "https://github.com/air6030i-star/soul-chart-engine"

PLANET_CN = {
    "☉": "太陽", "⊕": "地球", "☊": "北交點", "☋": "南交點", "☾": "月亮",
    "☿": "水星", "♀": "金星", "♂": "火星", "♃": "木星", "♄": "土星",
    "♅": "天王星", "♆": "海王星", "♇": "冥王星",
}
PLANET_MEAN = {
    "太陽": "你意識的核心、最閃耀的本質", "地球": "讓你落地、平衡的力量",
    "北交點": "今生要走向的方向", "南交點": "過去帶來的習性",
    "月亮": "驅動你的情感", "水星": "你怎麼思考與溝通", "金星": "你的價值與愛的方式",
    "火星": "你的行動與慾望", "木星": "你的擴展與幸運", "土星": "你的課題與紀律",
    "天王星": "你的獨特與變革", "海王星": "你的靈性與想像", "冥王星": "你的蛻變與深層力量",
}

# 時區 → 預設座標（用於排盤引擎）
TZ_COORDS: dict[float, tuple[float, float]] = {
    8.0:  (25.033,  121.565),   # 台灣 / 香港 / 新加坡
    9.0:  (35.689,  139.692),   # 日本
    7.0:  (13.756,  100.502),   # 泰國 / 越南
    5.5:  (28.614,   77.209),   # 印度
    0.0:  (51.507,   -0.128),   # 英國 UTC
    1.0:  (48.856,    2.352),   # 西歐 UTC+1
    2.0:  (31.768,   35.215),   # 以色列 / 東歐
    3.0:  (55.751,   37.618),   # 莫斯科
    -5.0: (40.712,  -74.006),   # 美東
    -6.0: (41.878,  -87.630),   # 美中
    -7.0: (33.449, -112.074),   # 美山
    -8.0: (37.774, -122.419),   # 美西
    -3.0: (-23.550, -46.633),   # 巴西
}


def parse_tz(tz_str: str) -> float:
    """從 '台灣 UTC+8'、'UTC+8'、'+8'、'8' 等字串解析浮點時差。"""
    m = re.search(r"([+-]?\s*\d+(?:\.\d+)?)\s*$", tz_str.strip())
    if m:
        return float(m.group(1).replace(" ", ""))
    raise ValueError(f"無法解析時區：{tz_str!r}")


def tz_to_coords(tz: float) -> tuple[float, float]:
    """時差 → (lat, lon)，找不到對應則用 (tz*15, 0)。"""
    if tz in TZ_COORDS:
        return TZ_COORDS[tz]
    # 每 15° 一個時區，以赤道為預設緯度
    return (0.0, tz * 15.0)


# ── 內部工具函式 ───────────────────────────────────────────────

def _match_key(text: str | None, table: dict) -> str | None:
    for k in table:
        if k and k in (text or ""):
            return table[k]
    return None


def _gate_label(num: int) -> str:
    g = GATES.get(str(num))
    return f"{num} {g['name']}卦" if g else str(num)


def _bodygraph_svg(defined: list) -> str:
    D = set(defined)
    centers = [
        ("頭",  150,  24, 56, 40, "tri-up"),
        ("邏輯",150,  92, 56, 40, "tri-down"),
        ("喉",  150, 158, 60, 44, "rect"),
        ("G",   150, 244, 56, 56, "diamond"),
        ("意志",226, 212, 40, 34, "tri-left"),
        ("薦骨",150, 330, 60, 44, "rect"),
        ("脾",   56, 300, 44, 70, "tri-right"),
        ("情緒",244, 300, 44, 70, "tri-left2"),
        ("根",  150, 410, 60, 44, "rect"),
    ]
    DEF, OPEN_S, STK = "#7b4fa6", "#ffffff", "#b9a9e0"
    p = ['<svg viewBox="0 0 300 470" xmlns="http://www.w3.org/2000/svg" '
         'font-family="\'Noto Serif TC\',serif">']
    for name, x, y, w, h, shape in centers:
        fill = DEF if name in D else OPEN_S
        tcol = "#fff" if name in D else "#6b5b8a"
        if shape == "rect":
            p.append(f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" rx="4" '
                     f'fill="{fill}" stroke="{STK}" stroke-width="2"/>')
        elif shape == "diamond":
            p.append(f'<polygon points="{x},{y-h/2} {x+w/2},{y} {x},{y+h/2} {x-w/2},{y}" '
                     f'fill="{fill}" stroke="{STK}" stroke-width="2"/>')
        elif shape == "tri-up":
            p.append(f'<polygon points="{x},{y-h/2} {x+w/2},{y+h/2} {x-w/2},{y+h/2}" '
                     f'fill="{fill}" stroke="{STK}" stroke-width="2"/>')
        elif shape == "tri-down":
            p.append(f'<polygon points="{x-w/2},{y-h/2} {x+w/2},{y-h/2} {x},{y+h/2}" '
                     f'fill="{fill}" stroke="{STK}" stroke-width="2"/>')
        elif shape == "tri-right":
            p.append(f'<polygon points="{x-w/2},{y-h/2} {x+w/2},{y} {x-w/2},{y+h/2}" '
                     f'fill="{fill}" stroke="{STK}" stroke-width="2"/>')
        else:  # tri-left / tri-left2
            p.append(f'<polygon points="{x+w/2},{y-h/2} {x-w/2},{y} {x+w/2},{y+h/2}" '
                     f'fill="{fill}" stroke="{STK}" stroke-width="2"/>')
        p.append(f'<text x="{x}" y="{y+4}" text-anchor="middle" '
                 f'font-size="13" fill="{tcol}">{name}</text>')
    p.append('</svg>')
    return "".join(p)


def build_html(birth: dict, chart: dict, bridge_block: str = "") -> str:
    """
    birth: {"name", "gender", "date", "time", "tz"}
    chart: 排盤引擎回傳的完整 JSON（含 human_design、western、ziwei）
    bridge_block: 64型靈魂原型段落 HTML（可為空字串）
    """
    hd = chart["human_design"]
    t, auth, prof = hd["type"], hd["authority"], hd["profile"]
    defi, cross   = hd["definition"], hd["incarnation_cross"]
    defined, openc = hd["defined_centers"], hd["open_centers"]
    chans = hd.get("channels", [])

    tinfo    = HD_DATA["types"].get(t, {})
    ainfo    = _match_key(auth, HD_DATA["authorities"]) or {"name": auth, "how": ""}
    lines    = prof.split("/")
    pl       = HD_DATA["profile_lines"]
    defi_desc = _match_key(defi, HD_DATA["definitions"]) or ""
    ch_data  = HD_DATA["channels"]
    apply    = tinfo.get("apply", {})

    by_planet = {g["planet"]: g for g in hd["gates"]}
    sun   = by_planet.get("☉", {})
    earth = by_planet.get("⊕", {})
    sun_p = sun.get("personality", {})
    sun_d = sun.get("design", {})

    def center_rows(names: list, kind: str) -> str:
        rows = ""
        for n in names:
            c = HD_DATA["centers"].get(n)
            if not c:
                continue
            if kind == "defined":
                body = c["defined"]
            else:
                body = (f'{c["open"]}<br>'
                        f'<span class="trap">⚠ 制約陷阱：{c.get("trap","")}</span><br>'
                        f'<span class="wis">✦ 你的智慧：{c.get("wisdom","")}</span>')
            rows += f'<tr><td class="cn">{n}</td><td class="ct">{c["theme"]}</td><td>{body}</td></tr>'
        return rows

    # 通道
    if chans:
        ch_rows = ""
        for ch in chans:
            key = "-".join(sorted(ch.split("-"), key=lambda x: int(x)))
            info = ch_data.get(key)
            if info:
                ch_rows += (f'<tr><td class="cn">{ch}</td>'
                            f'<td class="ct">{info["name"]}</td>'
                            f'<td>{info["keynote"]}</td></tr>')
            else:
                ch_rows += f'<tr><td class="cn">{ch}</td><td colspan="2">能量通道</td></tr>'
        ch_block = (f'<table><tr><th>通道</th><th>名稱</th><th>你的核心天賦</th></tr>'
                    f'{ch_rows}</table>')
    else:
        ch_block = ('<p class="muted">你的盤面沒有完整連通的通道，能量以「單一閘門」的方式呈現'
                    '——這常見於投射者與反映者，代表你更像個獨立的取樣者與觀察者。</p>')

    # 13 行星閘門表
    def gate_cell(gd: dict) -> str:
        g = GATES.get(str(gd.get("gate")), {})
        if not g:
            return str(gd.get("gate", ""))
        return (f'第{gd["gate"]}閘門 {g["name"]}卦<br>'
                f'<span class="gk">{g["keynote"]}</span> '
                f'<span class="muted">· {gd["line"]}爻</span>')

    grows = ""
    for g in hd["gates"]:
        pcn = PLANET_CN.get(g["planet"], g["planet"])
        grows += (f'<tr><td class="pl">{pcn}<br>'
                  f'<span class="gk">{PLANET_MEAN.get(pcn,"")}</span></td>'
                  f'<td>{gate_cell(g["personality"])}</td>'
                  f'<td>{gate_cell(g["design"])}</td></tr>')

    # 重點行星深入
    def planet_deep(sym: str, label: str, role: str) -> str:
        g = by_planet.get(sym, {})
        p = g.get("personality", {})
        gg = GATES.get(str(p.get("gate")), {})
        if not gg:
            return ""
        return (f'<h4 style="color:var(--purple);font-size:13pt;margin:5mm 0 1mm;">'
                f'{label} · 第{p["gate"]}閘門 {gg["name"]}卦</h4>'
                f'<p>{label}代表{role}。它落在「{gg["name"]}卦」，'
                f'能量主題是<strong>{gg["keynote"]}</strong>（{gg.get("theme","")}）'
                f'——這股頻率，會自然地染上你在這個面向的樣子。</p>')

    _deep_list = [
        ("⊕", "地球", "讓你落地、平衡、腳踏實地的力量"),
        ("☾", "月亮", "驅動你情感與內在的動力"),
        ("☊", "北交點", "你今生要學習、走向的方向"),
        ("☋", "南交點", "你天生就熟練、帶著走的舊習與禮物"),
    ]
    deep_planets = "".join(planet_deep(s, l, r) for s, l, r in _deep_list)
    deep_planets += ('<p class="muted" style="margin-top:5mm;">＊木星、土星、天王星、海王星、'
                     '冥王星等外行星屬「世代能量」——同一個世代的人多半落在相近的閘門，'
                     '對「個人」來說較不獨特，因此這裡只列於上表、不逐一深寫。</p>')

    # 輪迴交叉四閘門
    cross_gates: list[str] = []
    for nm, gd in [("個性太陽", sun_p), ("個性地球", earth.get("personality", {})),
                   ("設計太陽", sun_d), ("設計地球", earth.get("design", {}))]:
        if gd.get("gate"):
            gg = GATES.get(str(gd["gate"]), {})
            cross_gates.append(
                f'<div class="kv">'
                f'<span class="k">{nm}</span>'
                f'<span class="v">{_gate_label(gd["gate"])}（{gg.get("keynote","")}）</span>'
                f'</div>'
            )

    def sun_theme(gd: dict, who: str) -> str:
        g = GATES.get(str(gd.get("gate")), {})
        if not g:
            return ""
        return (f'<div class="card">'
                f'<div style="font-size:15pt;color:var(--purple);font-weight:700;">'
                f'{who}：第 {gd["gate"]} 閘門 · {g["name"]}卦</div>'
                f'<p style="margin-top:2mm;">關鍵能量：{g["keynote"]}（{g.get("theme","")}）</p>'
                f'</div>')

    svg = _bodygraph_svg(defined)
    birth_line = (f'{birth["date"]} {birth["time"]}　'
                  f'{"♀ 女" if birth["gender"]=="女" else "♂ 男"}')

    css = """
  :root{--deep:#1a2030;--purple:#2d1b69;--light:#7b4fa6;--rose:#c0608f;--gold:#c89b4a;--paper:#fdfbf7;--ink:#252233;}
  *{margin:0;padding:0;box-sizing:border-box;-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important;}
  html,body{background:var(--paper);color:var(--ink);font-family:"Noto Serif TC","DejaVu Serif",serif;font-size:13pt;line-height:2.0;}
  @page{size:A4;margin:16mm 15mm;}
  .page{max-width:180mm;margin:0 auto;padding:6mm 0;page-break-after:always;}
  .page:last-child{page-break-after:auto;}
  h1{font-size:26pt;color:var(--purple);font-weight:900;letter-spacing:.04em;}
  h2{font-size:18pt;color:#fff;background:var(--purple);padding:4mm 6mm;border-radius:2mm;margin:0 0 6mm;}
  h3{font-size:14pt;color:var(--purple);border-left:4px solid var(--light);padding-left:3mm;margin:6mm 0 3mm;font-weight:700;}
  pymargin:0 0 3mm;} .muted{color:#6b647e;font-size:11pt;}
  .gk{color:var(--rose);font-size:10pt;}
  table{width:100%;border-collapse:collapse;margin:3mm 0;font-size:11.5pt;}
  th{background:var(--purple);color:#fff;text-align:left;padding:2mm 3mm;font-weight:500;}
  td{padding:2.5mm 3mm;border-bottom:1px solid #e8e3d6;vertical-align:top;line-height:1.75;}
  tr:nth-child(even) td{background:#faf6ee;}
  td.cn,td.pl{font-weight:700;color:var(--purple);white-space:nowrap;} td.ct{color:var(--rose);white-space:nowrap;}
  .trap{color:#b3603f;font-size:10.5pt;} .wis{color:#5a7d3a;font-size:10.5pt;}
  .card{background:#fff;border:2px solid var(--light);border-radius:3mm;padding:5mm 6mm;margin:4mm 0;}
  .kv{display:flex;justify-content:space-between;border-bottom:1px dashed #d8cdbb;padding:2.5mm 0;}
  .kv:last-child{border-bottom:none;} .kv .k{color:#6b647e;} .kv .v{font-weight:700;color:var(--purple);text-align:right;}
  .cover{text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:240mm;}
  .cover .eyebrow{letter-spacing:.4em;color:var(--light);font-size:12pt;}
  .big{font-size:40pt;font-weight:900;color:var(--purple);margin:4mm 0;}
  .tag{display:inline-block;background:var(--gold);color:#fff;padding:1mm 5mm;border-radius:99mm;font-size:12pt;margin:2mm;}
  .bg{width:62mm;margin:6mm auto;} .bg svg{width:100%;height:auto;}
  .legend{font-size:10.5pt;color:#6b647e;} .legend b{color:var(--light);}
  blockquote{background:#fde8f2;border-left:4px solid var(--rose);padding:3mm 5mm;border-radius:0 2mm 2mm 0;margin:3mm 0;}
  .footer{text-align:center;color:#7a7390;font-size:10pt;border-top:1px dashed #b9a9e0;padding-top:4mm;margin-top:8mm;}
  ul{padding-left:6mm;margin:0 0 3mm;} li{margin:1mm 0;}
"""

    cross_gates_html = "".join(cross_gates)

    return f"""<!DOCTYPE html><html lang="zh-Hant"><head>
<meta charset="UTF-8">
<title>{birth['name']} · 人類圖個人報告｜靈魂宇宙</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;500;700;900&display=swap" rel="stylesheet">
<style>{css}</style></head><body>

<section class="page cover">
  <div class="eyebrow">靈魂宇宙 · SOUL UNIVERSE</div>
  <h1 style="font-size:30pt;margin:6mm 0 2mm;">人類圖個人報告</h1>
  <div class="muted">Human Design Personal Report · 深度版</div>
  <div class="bg">{svg}</div>
  <div class="big">{birth['name']}</div>
  <div class="muted">{birth_line}</div>
  <div style="margin-top:5mm;">
    <span class="tag">{t}</span>
    <span class="tag">{prof} 角色</span>
    <span class="tag">{ainfo['name']}</span>
  </div>
</section>

<section class="page">
  <h2>你的人類圖速覽</h2>
  <div class="card">
    <div class="kv"><span class="k">能量類型 Type</span><span class="v">{t}</span></div>
    <div class="kv"><span class="k">人生策略 Strategy</span><span class="v">{tinfo.get('strategy','')}</span></div>
    <div class="kv"><span class="k">內在權威 Authority</span><span class="v">{ainfo['name']}</span></div>
    <div class="kv"><span class="k">人生角色 Profile</span><span class="v">{prof}</span></div>
    <div class="kv"><span class="k">定義 Definition</span><span class="v">{defi}</span></div>
    <div class="kv"><span class="k">內在指標 Signature</span><span class="v">{tinfo.get('signature','')}</span></div>
    <div class="kv"><span class="k">非自己主題 Not-Self</span><span class="v">{tinfo.get('not_self','')}</span></div>
  </div>
  <div class="bg" style="width:70mm;">{svg}</div>
  <p class="legend"><b>■ 紫色＝有定義的中心</b>（穩定、可依靠的能量）　□ 白色＝開放的中心（吸收與放大他人）</p>
</section>

<section class="page">
  <h2>1 · 你的能量類型：{t}</h2>
  <p class="muted">{tinfo.get('en','')}　·　{tinfo.get('ratio','')}　·　氣場：{tinfo.get('aura','')}</p>
  <p>{tinfo.get('summary','')}</p>
  <h3>你的人生策略：{tinfo.get('strategy','')}</h3>
  <blockquote>順著策略走 → 你會感受到「{tinfo.get('signature','')}」；違背策略 → 會累積「{tinfo.get('not_self','')}」。</blockquote>
  <h3>給你的提醒</h3>
  <ul>{"".join(f"<li>{x}</li>" for x in tinfo.get('tips',[]))}</ul>
</section>

<section class="page">
  <h2>2 · 你的內在權威：{ainfo['name']}</h2>
  <p>內在權威，是你「做對決定」的身體羅盤——不是用頭腦想，而是用你天生的決策機制。</p>
  <blockquote>{ainfo['how']}</blockquote>
  <p class="muted">當你用對的方式做決定，人生會越來越順；用頭腦硬推翻它，往往會後悔。這是你一生最值得練習的事。</p>
</section>

<section class="page">
  <h2>3 · 你的人生角色：{prof}</h2>
  <h3>第 {lines[0]} 爻</h3>
  <p>{pl.get(lines[0],'')}</p>
  <h3>第 {lines[1] if len(lines)>1 else ''} 爻</h3>
  <p>{pl.get(lines[1],'') if len(lines)>1 else ''}</p>
  <blockquote>你的 {prof} 角色，是這兩種能量的交織——前者是你立足的根基，後者是你與世界互動的方式。</blockquote>
  <h3>你的定義：{defi}</h3>
  <p>{defi_desc}</p>
</section>

<section class="page">
  <h2>4 · 你的能量中心</h2>
  <div class="bg" style="width:60mm;">{svg}</div>
  <h3>有定義的中心（你穩定的力量）</h3>
  <table><tr><th>中心</th><th>主題</th><th>對你的意義</th></tr>{center_rows(defined,'defined')}</table>
  <h3>開放的中心（你吸收、學習，也最容易被制約之處）</h3>
  <table><tr><th>中心</th><th>主題</th><th>陷阱與智慧</th></tr>{center_rows(openc,'open')}</table>
</section>

<section class="page">
  <h2>5 · 你的核心天賦：通道</h2>
  <p>通道，是兩個閘門連起來、貫穿兩個中心的能量。它是你最穩定、最強的天賦所在——別人要努力，你卻天生就會。</p>
  {ch_block}
  <h3>你的人生主題閘門</h3>
  {sun_theme(sun_p, '個性太陽（你意識的核心）')}
  {sun_theme(sun_d, '設計太陽（你身體與潛意識的天賦）')}
</section>

<section class="page">
  <h2>6 · 你的 13 行星閘門（你的能量配方）</h2>
  <p>你出生那一刻，13 顆行星各自落在某一個「閘門（易經卦象）」上——每個閘門都是一種具體的能量主題。這 13 個閘門組合起來，就是「<strong>只屬於你的能量配方</strong>」。</p>
  <h3>怎麼看這張表</h3>
  <ul>
    <li><strong>行星</strong>＝這股能量作用在你哪個面向</li>
    <li><strong>個性</strong>（中欄）＝你<strong>意識</strong>層面、自己認得的你</li>
    <li><strong>設計</strong>（右欄）＝出生前約 88 天、<strong>身體與潛意識</strong>帶來的天賦</li>
  </ul>
  <table><tr><th>行星 / 代表</th><th>個性（意識的你）</th><th>設計（潛意識天賦）</th></tr>{grows}</table>
  <h3>重點行星深入</h3>
  {deep_planets}
</section>

<section class="page">
  <h2>7 · 你的輪迴交叉</h2>
  <div class="card"><div style="font-size:16pt;color:var(--purple);font-weight:700;text-align:center;">{cross}</div></div>
  <p>{HD_DATA.get('cross_intro','')}</p>
  <h3>組成你人生主題的四個閘門</h3>
  <div class="card">{cross_gates_html}</div>
</section>

<section class="page">
  <h2>8 · 把人類圖活用在生活裡</h2>
  <h3>💼 工作與事業</h3><p>{apply.get('work','')}</p>
  <h3>💗 感情與關係</h3><p>{apply.get('love','')}</p>
  <h3>🔋 能量與健康</h3><p>{apply.get('energy','')}</p>
  <blockquote>人類圖不是要你照表操課，而是給你一個「最不費力、最像自己」的活法。</blockquote>
</section>

{bridge_block}

<section class="page">
  <h2>給你的話</h2>
  <p>這份報告裡的每一個字，都是從你出生那一刻的星空與曆法精算出來的——它是屬於你一個人的能量藍圖。</p>
  <blockquote>活出你的策略與權威，就是回到你原廠設定的過程。願這份報告，成為你這一生好好做自己的起點。</blockquote>
  <div class="footer">
    靈魂宇宙 Soul Universe · 人類圖個人報告（深度版）<br>
    排盤由開源引擎計算 · <a href="{ENGINE_SRC}">原始碼（AGPL-3.0）</a><br>
    本報告為自我探索參考，非醫療、命運或投資建議。
  </div>
</section>

</body></html>"""
