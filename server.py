# -*- coding: utf-8 -*-
"""
server.py
=========
Soul Chart Engine — HTTP API Server for Render Deployment

職責：
    把原本是 CLI 工具的 chart_engine.py 包成 HTTP API，
    讓 Render Web Service 可以 24/7 對外服務。

部署位置（明天 push 到 GitHub）：
    air6030i-star/soul-chart-engine/server.py（repo 根目錄）

授權說明：
    此檔案放在 AGPL-3.0 的 fork 內，**必須**保持 AGPL-3.0。
    意思是：你的 souluniverse.com 上線後，footer 要放原始碼連結。

Render 設定（明天用）：
    Service Type: Web Service
    Region: Singapore（既有 line-assistant 也在這）
    Branch: main
    Root Directory: （留空，用 repo 根目錄）
    Runtime: Python 3
    Build Command:
        bash setup.sh && pip install fastapi uvicorn
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
from pydantic import BaseModel, Field

# 把 scripts/ 加進 sys.path，方便 import chart_engine
SCRIPTS_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# 從 engine import 核心函式
# 注意：chart_engine.py 在 scripts/ 底下
try:
    from chart_engine import build_json  # type: ignore
except ImportError as e:
    print(f"❌ 無法載入 chart_engine：{e}", file=sys.stderr)
    print(f"   請確認 scripts/chart_engine.py 存在", file=sys.stderr)
    raise


# ============================================================
# FastAPI 設定
# ============================================================

app = FastAPI(
    title="Soul Chart Engine API",
    description="Soul Universe 排盤引擎 — 西洋星盤 + 紫微斗數 + 人類圖 三系統 HTTP API",
    version="1.0",
)

# CORS — 允許 Soul Universe 前端域名跨域呼叫
# 上線後改成只允許 souluniverse.com，更安全
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://souluniverse.com",
        "https://www.souluniverse.com",
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:8000",  # 本機測試
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================
# 輸入資料模型（Pydantic 自動驗證）
# ============================================================

class BirthInput(BaseModel):
    """使用者生辰資料"""

    name: str = Field(default="範例", description="姓名（顯示用）")
    gender: str = Field(..., description="性別：男 或 女", pattern="^[男女]$")
    date: str = Field(
        ...,
        description="西曆生日，YYYY-MM-DD",
        pattern=r"^\d{4}-\d{1,2}-\d{1,2}$",
    )
    time: str = Field(
        ...,
        description="出生時間（24h），HH:MM",
        pattern=r"^\d{1,2}:\d{2}$",
    )
    tz: float = Field(default=8.0, description="UTC 時差，含 DST。台灣 = 8")
    lat: float = Field(..., ge=-90, le=90, description="緯度")
    lon: float = Field(..., ge=-180, le=180, description="經度")
    target: Optional[str] = Field(
        default=None,
        description="紫微大限參考日 YYYY-MM-DD（不填用今天）",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "小明",
                "gender": "女",
                "date": "1990-06-15",
                "time": "08:30",
                "tz": 8.0,
                "lat": 25.0330,
                "lon": 121.5654,
                "target": "2026-06-03",
            }
        }
    }


# ============================================================
# Endpoints
# ============================================================

@app.get("/")
def root():
    """根路徑 — 給 Render 健康檢查 + 給人看的歡迎頁"""
    return {
        "ok": True,
        "service": "Soul Chart Engine API",
        "version": "1.0",
        "endpoints": {
            "POST /api/chart": "計算三系統盤面",
            "GET /health": "健康檢查",
            "GET /docs": "Swagger UI（自動生成）",
        },
    }


@app.get("/health")
def health():
    """健康檢查 — Render 會定期打這個"""
    return {"ok": True, "status": "alive"}


@app.post("/api/chart")
def compute_chart(birth: BirthInput) -> dict:
    """
    主要 endpoint — 接收生辰資料，回傳三系統盤面 JSON

    回傳格式見 engine 的 build_json：
    {
        "ok": true,
        "schema_version": "1.0",
        "input": {...},
        "western": {...},
        "human_design": {...},
        "ziwei": {...},
        "meta": {...}
    }
    """
    try:
        # 解析日期 / 時間
        y, m, d = map(int, birth.date.split("-"))
        hh, mm = map(int, birth.time.split(":"))

        # target 預設今天
        target = birth.target or _date.today().isoformat()

        # 轉成 engine 期望的 input 格式
        inp = {
            "name": birth.name,
            "gender": birth.gender,
            "date": (y, m, d),
            "time": (hh, mm),
            "tz_offset": birth.tz,
            "lat": birth.lat,
            "lon": birth.lon,
            "target": target,
        }

        # 呼叫 engine
        result = build_json(inp)

        if not result.get("ok"):
            raise HTTPException(
                status_code=500,
                detail=f"Engine 計算失敗：{result.get('error', '未知')}",
            )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"輸入格式錯誤：{e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{e}")


# ============================================================
# 本機測試（python server.py）
# ============================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Soul Chart Engine — 本機測試模式")
    print("=" * 60)
    print("API 文件：http://127.0.0.1:8000/docs")
    print("健康檢查：http://127.0.0.1:8000/health")
    print()
    print("測試 POST /api/chart：")
    print('  curl -X POST http://127.0.0.1:8000/api/chart \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"gender":"女","date":"1990-06-15","time":"08:30",'
          '"lat":25.0330,"lon":121.5654}\'')
    print()

    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # 本機開發 hot reload
    )
