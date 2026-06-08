# -*- coding: utf-8 -*-
"""
server.py
=========
Soul Chart Engine — HTTP API Server for Render Deployment

職責：
    把原本是 CLI 工具的 chart_engine.py 包成 HTTP API，
    讓 Render Web Service 可以 24/7 對外服務。

部署位置：
    air6030i-star/soul-chart-engine/server.py（repo 根目錄）

授權說明：
    此檔案放在 AGPL-3.0 的 fork 內，**必須**保持 AGPL-3.0。
    意思是：你的 souluniverse.app 上線後，footer 要放原始碼連結。

Render 設定：
    Service Type: Web Service
    Region: Singapore
    Branch: main
    Root Directory: （留空，用 repo 根目錄）
    Runtime: Python 3
    Build Command:
        bash setup.sh && pip install -r requirements.txt && playwright install chromium --with-deps
    Start Command:
        .venv/bin/uvicorn server:app --host 0.0.0.0 --port $PORT
    Environment Variables:
        PYTHON_VERSION = 3.12
"""
from __future__ import annotations

import sys
from datetime import date as _date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

# 把 scripts/ 加進 sys.path，方便 import chart_engine
SCRIPTS_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# 從 engine import 核心函式
try:
    from chart_engine import build_json  # type: ignore
except ImportError as e:
    print(f"❌ 無法載入 chart_engine：{e}", file=sys.stderr)
    raise

# 人類圖報告 HTML 生成器
try:
    from hd_report import build_html, parse_tz, tz_to_coords  # type: ignore
    HD_REPORT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ hd_report 未載入，/api/hd_report 不可用：{e}", file=sys.stderr)
    HD_REPORT_AVAILABLE = False


# ============================================================
# FastAPI 設定
# ============================================================

app = FastAPI(
    title="Soul Chart Engine API",
    description="Soul Universe 排盤引擎 — 西洋星盤 + 紫微斗數 + 人類圖 三系統 HTTP API",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://souluniverse.app",
        "https://www.souluniverse.app",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================
# 輸入資料模型
# ============================================================

class BirthInput(BaseModel):
    name: str = Field(default="範例", description="姓名（顯示用）")
    gender: str = Field(..., description="性別：男 或 女", pattern="^[男女]$")
    date: str = Field(..., description="西曆生日，YYYY-MM-DD", pattern=r"^\d{4}-\d{1,2}-\d{1,2}$")
    time: str = Field(..., description="出生時間（24h），HH:MM", pattern=r"^\d{1,2}:\d{2}$")
    tz: float = Field(default=8.0, description="UTC 時差。台灣 = 8")
    lat: float = Field(..., ge=-90, le=90, description="緯度")
    lon: float = Field(..., ge=-180, le=180, description="經度")
    target: Optional[str] = Field(default=None, description="紫微大限參考日 YYYY-MM-DD")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "小明", "gender": "女", "date": "1990-06-15",
                "time": "08:30", "tz": 8.0, "lat": 25.0330, "lon": 121.5654,
            }
        }
    }


class HDReportInput(BaseModel):
    """人類圖報告請求（來自 n8n / Gumroad 訂單）"""
    name:   str = Field(default="朋友",  description="稱呼（報告封面顯示）")
    gender: str = Field(...,             description="性別：男 或 女")
    date:   str = Field(...,             description="出生日期 YYYY-MM-DD")
    time:   str = Field(...,             description="出生時間 HH:MM（24h）")
    tz:     str = Field(default="UTC+8", description="出生地時區，如 '台灣 UTC+8'")
    code:   str = Field(default="",     description="64型測驗結果（選填，如 INFJ）")
    email:  str = Field(default="",     description="客人 email（記錄用）")


# ============================================================
# Endpoints
# ============================================================

@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Soul Chart Engine API",
        "version": "1.0",
        "endpoints": {
            "POST /api/chart": "計算三系統盤面",
            "POST /api/hd_report": "人類圖個人報告 PDF",
            "GET /health": "健康檢查",
            "GET /docs": "Swagger UI",
        },
    }


@app.get("/health")
def health():
    return {"ok": True, "status": "alive"}


@app.post("/api/chart")
def compute_chart(birth: BirthInput) -> dict:
    """接收生辰資料，回傳三系統盤面 JSON"""
    try:
        y, m, d = map(int, birth.date.split("-"))
        hh, mm = map(int, birth.time.split(":"))
        target = birth.target or _date.today().isoformat()
        inp = {
            "name": birth.name, "gender": birth.gender,
            "date": (y, m, d), "time": (hh, mm),
            "tz_offset": birth.tz, "lat": birth.lat, "lon": birth.lon,
            "target": target,
        }
        result = build_json(inp)
        if not result.get("ok"):
            raise HTTPException(500, detail=f"Engine 計算失敗：{result.get('error', '未知')}")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, detail=f"輸入格式錯誤：{e}")
    except Exception as e:
        raise HTTPException(500, detail=f"伺服器錯誤：{e}")


async def _html_to_pdf(html: str) -> bytes:
    """使用 playwright Chromium 將 HTML 轉為 PDF bytes。"""
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        pdf_bytes = await page.pdf(
            format="A4",
            margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"},
            print_background=True,
        )
        await browser.close()
    return pdf_bytes


@app.post("/api/hd_report", summary="人類圖個人報告（PDF）")
async def hd_report(req: HDReportInput) -> Response:
    """
    接收客人生辰 → 排盤 → 生成深度報告 HTML → 轉 PDF → 回傳 binary。
    n8n 設定：HTTP Request node，Response Format = File，再接 Gmail 寄附件。
    """
    if not HD_REPORT_AVAILABLE:
        raise HTTPException(503, "hd_report 模組未就緒")

    try:
        tz_float = parse_tz(req.tz)
    except ValueError as e:
        raise HTTPException(400, str(e))

    lat, lon = tz_to_coords(tz_float)

    try:
        y, m, d = map(int, req.date.split("-"))
        hh, mm  = map(int, req.time.split(":"))
        inp = {
            "name": req.name, "gender": req.gender,
            "date": (y, m, d), "time": (hh, mm),
            "tz_offset": tz_float, "lat": lat, "lon": lon,
            "target": _date.today().isoformat(),
        }
        chart = build_json(inp)
    except Exception as e:
        raise HTTPException(500, f"排盤引擎失敗：{e}")

    if not chart.get("ok"):
        raise HTTPException(500, f"排盤引擎錯誤：{chart.get('error','未知')}")

    # 64型靈魂原型段落（選填）
    code = (req.code or "").upper().strip()
    if code:
        mbti_type = code.split("-")[0][:4]
        bridge_block = f"""<section class="page">
  <h2>9 · 你的靈魂原型</h2>
  <p>依你做的「64 型靈魂密碼測驗」，你的型號是：</p>
  <div class="card" style="text-align:center;border-color:var(--gold);">
    <div style="font-size:23pt;color:var(--purple);font-weight:900;">{mbti_type}</div>
  </div>
  <p>這份人類圖，是從「你出生那一刻的能量設計」描繪同一個你——和你的靈魂原型互相輝映。</p>
  <blockquote>同一個靈魂，兩種語言：心理測驗看見你的「樣子」，人類圖看見你的「設計」。</blockquote>
</section>"""
    else:
        bridge_block = """<section class="page">
  <h2>9 · 你的靈魂原型</h2>
  <p>想知道你的 64 型靈魂原型，可以做「64 型靈魂密碼測驗」——兩者合看，最完整。</p>
</section>"""

    birth = {"name": req.name, "gender": req.gender, "date": req.date, "time": req.time, "tz": tz_float}
    try:
        html = build_html(birth, chart, bridge_block)
    except Exception as e:
        raise HTTPException(500, f"HTML 生成失敗：{e}")

    try:
        pdf_bytes = await _html_to_pdf(html)
    except Exception as e:
        raise HTTPException(500, f"PDF 轉檔失敗：{e}")

    safe_name = "".join(c for c in req.name if c not in r'\/:*?"<>|').strip() or "report"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_人類圖個人報告.pdf"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
