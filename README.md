# life-chart-engine

> 一份出生資料，一次算出 **西洋星盤 + 人類圖 + 紫微斗數** 三套盤面，並以原生天文／曆法計算（非查表、非記憶），結果可重現、可交叉驗證。

`life-chart-engine` 是一個小巧的命令列引擎。給它出生的「日期、時間、經緯度、時區」，它用 [Swiss Ephemeris](https://www.astro.com/swisseph/) 算行星與宮位、用 88° 太陽弧推導人類圖、用 [py-iztro](https://github.com/x-haose/py-iztro) 排紫微斗數，輸出一份結構化盤面。

支援兩種輸出：

- **Markdown**（預設）— 給人看。
- **JSON**（`--json`）— 給 AI agent 看。介面契約見 [`AGENTS.md`](./AGENTS.md)。

---

## 三套系統

| 系統 | 引擎 | 算出什麼 |
|------|------|----------|
| 西洋星盤 | Swiss Ephemeris（Tropical / Placidus / Moshier） | 上升、天頂、十大行星 + 南北交點（含落宮與逆行）、12 宮頭、主要相位 |
| 人類圖 Human Design | Swiss Ephemeris（太陽退 88°） | 類型、權威、角色、定義、定義／開放中心、通道、輪迴交叉、26 閘門（個性盤＋設計盤） |
| 紫微斗數 | py-iztro | 五行局、命主、身主、12 宮全星（含亮度與四化）、大限／流年 |

類型／權威／定義等並非寫死，而是由「定義中心的連通圖」自動推導。

---

## 為什麼要原生計算

- **可重現**：同一組輸入永遠得到同一份盤；不靠模型記憶、不會「每次講不一樣」。
- **精度高**：行星位置與紫微星曜入宮由天文與曆法決定，不是估算。
- **可交叉驗證**：三套系統同時指向同一件事的訊號，才當高可信主幹；單一系統細節僅供參考。

---

## 安裝

需要 [`uv`](https://docs.astral.sh/uv/)。引擎依賴 py-iztro，其原生套件（pythonmonkey / pydantic-core）**只支援 CPython 3.12**，較新版本（3.13+/3.14）無法編譯，請務必走 3.12 venv。

```bash
git clone https://github.com/zhenheco/life-chart-engine.git
cd life-chart-engine
bash setup.sh          # 建立 .venv（Python 3.12）+ 安裝相依 + 冒煙測試
```

`setup.sh` 等同：

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

---

## 使用

### 給人看（Markdown）

```bash
.venv/bin/python scripts/chart_engine.py \
  --name "小明" --gender 女 \
  --date 1990-06-15 --time 08:30 \
  --tz 8 --lat 25.0330 --lon 121.5654 \
  --target 2025-01-01
```

### 給 agent 看（JSON）

```bash
.venv/bin/python scripts/chart_engine.py --json \
  --name "小明" --gender 女 \
  --date 1990-06-15 --time 08:30 \
  --tz 8 --lat 25.0330 --lon 121.5654
```

輸出單一 JSON 物件（`ok / input / western / human_design / ziwei / meta`）。完整欄位 schema、exit code、錯誤格式見 [`AGENTS.md`](./AGENTS.md)；範例輸出見 [`examples/`](./examples/)。

### 參數

| 旗標 | 必填 | 說明 |
|------|:---:|------|
| `--name` | 否 | 純標籤，只用於顯示 |
| `--gender` | 是* | `男` / `女`。紫微用於大限方向與命主／身主；星盤與人類圖不需要 |
| `--date` | 是 | 出生日期（**西曆／陽曆**）`YYYY-MM-DD`。只有農曆時請先換算 |
| `--time` | 是 | 出生時間 `HH:MM`（24 小時，**本地時鐘時間**） |
| `--tz` | 是 | 出生地當時的 UTC 時差，**必須含夏令時**（台灣 1980 後固定 `8`） |
| `--lat` / `--lon` | 是 | 緯度／經度（城市級即可，誤差對盤面 < 0.1°） |
| `--target` | 否 | 紫微運限參考日 `YYYY-MM-DD`，預設帶入內建值，通常傳「今天」 |

\* 省略時使用內建範例值。實際排盤請一律明確傳入。

> ⚠️ **時區與夏令時是最常見的錯誤來源。** `--tz` 是「出生地、出生當下」的 UTC 時差。非台灣、或 1980 年前出生，務必查證當年是否實施日光節約時間。引擎不會自己查城市時區，由呼叫端（人或 agent）負責換算。

---

## 精準度分級

| 可信度 | 項目 |
|--------|------|
| 最高（天文／曆法決定） | 行星位置；紫微星入宮、命宮／身宮、五行局、生年四化 |
| 高（依賴出生時間精準度） | 上升、宮位、人類圖爻線、紫微時辰 |
| 高（已驗證） | 紫微星曜亮度（py-iztro 對齊文墨天機） |
| 需標注 | 任何行星／閘門／爻落在分界 ±0.3° 內者 → 標為「待定」並說明影響 |

---

## 已知限制

- Moshier 星曆不含凱龍等小天體。
- 紫微四化採 py-iztro 預設派系；慣用飛星等其他流派時主結構不變、細節可能略異。
- 出生時間只有「大概」時，上升／宮位／爻線／時辰皆為敏感項，建議用生命事件回推校時。

---

## 計算原理

- **星盤**：Tropical 黃道、Placidus 分宮、Moshier 星曆。
- **人類圖**：個性盤＝出生時刻；設計盤＝太陽退 88° 黃道弧度之時刻（約出生前 3 個月）。閘門用 Rave 曼陀羅序列，offset 以已知盤校準。
- **紫微**：py-iztro；時辰 index 由出生小時換算（子 0 … 戌 10 … 晚子 12）。

---

## 授權

本專案以 **GNU AGPL v3** 釋出（見 [`LICENSE`](./LICENSE)）。原因：引擎連結 Swiss Ephemeris，後者採 AGPL／商用雙授權。**若你將本引擎部署為網路服務，AGPL §13 要求你向服務使用者提供完整原始碼。** 需閉源／商用，請改向 Astrodienst 取得 Swiss Ephemeris 商用授權。

相依與致謝見 [`CREDITS.md`](./CREDITS.md)。

---

## 免責

命理是**詮釋性的自我覺察框架，不是預測工具**。請以「校準」而非「宿命」的角度使用，並以你的實際經驗為最終權威。本工具不提供醫療、法律、財務或心理診斷。
