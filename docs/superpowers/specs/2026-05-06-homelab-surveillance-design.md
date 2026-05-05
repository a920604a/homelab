# 租屋處地端監控系統 — 架構設計 (MVP)

**日期：** 2026-05-06
**狀態：** 已確認
**PRD：** /PRD.md

---

## 1. 系統概覽

一套完全地端、低成本、不依賴訂閱的租屋監控系統。以 Raspberry Pi 400 為主機，Frigate 為 NVR 核心，Tailscale 提供安全遠端存取，Synology NAS 作為長期備份。

---

## 2. 硬體

| 元件 | 規格 | 備註 |
|---|---|---|
| 主機 | Raspberry Pi 400 | 已有，ARM64，4GB RAM |
| 攝影機 | TP-Link Tapo C200 | 待購，< NTD 1000 |
| 本地儲存 | USB SSD，128GB+ | 外接 Pi 400 |
| NAS | Synology | 已有，長期 archive |

---

## 3. 整體架構

```
┌─────────────── Raspberry Pi 400 ───────────────────┐
│                                                     │
│  Camera (Tapo C200, WiFi)                           │
│       │ RTSP / H264 / 5fps                          │
│       ▼                                             │
│  ┌─────────────────────────────┐                    │
│  │  Frigate                    │                    │
│  │  - go2rtc (RTSP relay)      │──recordings──▶ USB SSD
│  │  - motion detection         │                    │
│  │  - event clips              │                    │
│  └──────────┬──────────────────┘                    │
│             │ MQTT events                           │
│             ▼                                       │
│  ┌──────────────────┐                               │
│  │  Mosquitto       │                               │
│  └──────┬───────────┘                               │
│         │                                           │
│         ▼                                           │
│  ┌──────────────────┐                               │
│  │  notification-   │──▶ Telegram Bot API ──▶ 📱    │
│  │  bridge (Python) │                               │
│  └──────────────────┘                               │
│                                                     │
│  Tailscale (host service)                           │
└─────────────────────────────────────────────────────┘

USB SSD
  └─ /media/frigate/
       │ rsync over SSH，每天 02:00
       ▼
Synology NAS /volume1/frigate-backup/
```

---

## 4. 元件說明

### Frigate
NVR 核心。從 Camera 拉 RTSP 串流，執行 motion detection，將 event clips 與連續錄影存到 USB SSD，提供 Web UI（port 5000）。

### go2rtc
內建於 Frigate。RTSP relay，讓多個 client 同時看即時畫面而不直接拉 Camera，避免 Camera 過載。

### Mosquitto
輕量 MQTT broker。Frigate 將 motion/detection events 發布至此，notification-bridge 訂閱後觸發通知。

### notification-bridge
小型 Python 容器。訂閱 Mosquitto Frigate event topic，呼叫 Telegram Bot API 發送通知與 snapshot。

### Tailscale
點對點加密 VPN（WireGuard-based）。裝在 Pi 400 host 層與手機，讓手機在外也能像在 LAN 內一樣連回 Pi 400，無需 port forwarding。

---

## 5. 手機端 App

| App | 用途 |
|---|---|
| Tailscale | VPN 連回家中 Pi 400 |
| 瀏覽器（Safari/Chrome）| 開啟 Frigate Web UI，可加到主畫面（PWA）|
| Telegram | 接收 motion 通知與 snapshot |

---

## 6. 儲存設計

### 錄影設定

| 串流 | 用途 | 設定 |
|---|---|---|
| Detect stream | motion 偵測 | 低解析，5fps |
| Record stream | 錄影存檔 | 1080p，5fps |

5fps 相較 24fps 減少約 75% 儲存空間，每天約 3-4 GB（單台 1080p）。

### 保留策略

| 儲存位置 | 資料類型 | 保留時間 |
|---|---|---|
| USB SSD | 連續錄影 | 3 天 |
| USB SSD | Event clips | 7 天 |
| Synology NAS | 全部備份 | 30+ 天 |

### NAS 備份

Protocol：rsync over SSH（不使用 SMB mount）

```bash
# Pi 400 cron（每天 02:00）
0 2 * * * rsync -av --delete \
  -e "ssh -i /home/pi/.ssh/synology_key" \
  /media/frigate/ \
  frigate-sync@192.168.x.x:/volume1/frigate-backup/
```

Synology 端：開啟 SSH，建立專用帳號 `frigate-sync`，限制存取路徑。

---

## 7. 安全設計

### 三層防護

**Layer 1 — Camera**
- 停用 Tapo 雲端帳號綁定（Tapo Care）
- 設強密碼 RTSP credentials
- 關閉 UPnP

**Layer 2 — 路由器**
- 以 Camera MAC address 封鎖 WAN 上網存取
- Camera 只能在 LAN 內與 Pi 400 通訊

**Layer 3 — Pi 400**
- 所有服務 port 只綁 `127.0.0.1`，不直接暴露至 LAN
- 無任何 port forwarding
- 遠端存取唯一通道為 Tailscale（加密，需帳號驗證）

```
Internet
   │  ✗ Camera blocked (MAC rule)
   │  ✗ 無 port forwarding
   │  ✓ Tailscale (WireGuard 加密)
   ▼
Router
   ├── Camera ──(RTSP, LAN only)──▶ Pi 400
   └── Pi 400 ──(Tailscale)──▶ 手機
```

---

## 8. 部署設計

### 目錄結構

```
~/homelab/
  ├── docker-compose.yml
  ├── .env                      ← 機密，不進 git
  ├── config/
  │    └── config.yml           ← Frigate 設定
  ├── mosquitto/
  │    └── mosquitto.conf
  └── notification-bridge/
       ├── Dockerfile
       └── main.py
```

### docker-compose.yml

```yaml
services:
  frigate:
    image: ghcr.io/blakeblackshear/frigate:stable
    restart: unless-stopped
    volumes:
      - ./config:/config
      - /media/frigate:/media/frigate
    ports:
      - "127.0.0.1:5000:5000"
      - "127.0.0.1:8554:8554"
    privileged: true

  mosquitto:
    image: eclipse-mosquitto:2
    restart: unless-stopped
    volumes:
      - ./mosquitto:/mosquitto/config
    ports:
      - "127.0.0.1:1883:1883"

  notification-bridge:
    build: ./notification-bridge
    restart: unless-stopped
    environment:
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
    depends_on:
      - mosquitto
```

### 開機自啟

```bash
sudo systemctl enable tailscaled docker
# docker compose restart: unless-stopped 處理其餘服務
```

Tailscale 安裝於 host layer（`apt install tailscale`），不進 Docker Compose。

---

## 9. 服務資源估算

| 服務 | RAM 估算 |
|---|---|
| Frigate | ~600-900 MB |
| Mosquitto | ~10 MB |
| notification-bridge | ~50 MB |
| Tailscale (host) | ~30 MB |
| **合計** | **~700 MB - 1 GB** |

Pi 400 的 4GB RAM 充裕，保留 3GB+ 給 OS 與未來擴充（Home Assistant Phase 2）。

---

## 10. Phase 2 擴充路徑

| 功能 | 方式 |
|---|---|
| Home Assistant 整合 | 加入 docker-compose，Frigate ↔ HA via MQTT |
| Coral TPU | USB Coral，Frigate 啟用硬體物件偵測 |
| NAS 作為主儲存 | Frigate recordings 改掛 NFS mount |
| VLAN 隔離 | 換可管理路由器後實施 |
| 更多攝影機 | Frigate config 加 camera，Pi 400 可支援 2-3 台（視 CPU）|

---

## 11. MVP 成功標準

- Camera 穩定串流 24h 不中斷
- Motion event 可在 Frigate Web UI 回放
- 通知在 30 秒內送達 Telegram
- 斷網後 LAN 內串流與錄影仍正常運作
- 每日自動備份至 Synology NAS
