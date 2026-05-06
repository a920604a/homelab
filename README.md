# Homelab 租屋監控系統

地端、低成本、不依賴訂閱的租屋監控系統。

## 架構

```
Camera (Tapo C200, WiFi)
    │ RTSP / H264 / 5fps
    ▼
Frigate (NVR + motion detection)  ──recordings──▶  USB SSD
    │ MQTT events
    ▼
Mosquitto (MQTT broker)
    │
    ▼
notification-bridge  ──▶  Telegram Bot  ──▶  📱

Tailscale (host)  ──▶  手機遠端存取 Frigate Web UI

USB SSD  ──rsync over SSH, daily 02:00──▶  Synology NAS
```

## 硬體需求

| 元件 | 規格 |
|---|---|
| 主機 | Raspberry Pi 400 |
| 攝影機 | TP-Link Tapo C200 |
| 本地儲存 | USB SSD 128GB+ |
| 備份 | Synology NAS |

## 快速啟動（Pi 400 上）

```bash
# 1. clone repo
git clone <repo-url> ~/homelab
cd ~/homelab

# 2. 填入實際設定值
cp .env.example .env
nano .env

# 3. 啟動所有服務
docker compose up -d

# 4. 確認狀態
docker compose ps
docker compose logs -f
```

## 設定檔

複製 `.env.example` 為 `.env` 並填入：

```bash
CAMERA_IP=192.168.1.100        # Tapo C200 的 LAN IP
RTSP_USER=your_rtsp_username   # Tapo App 設定的 RTSP 帳號
RTSP_PASSWORD=your_rtsp_pass   # Tapo App 設定的 RTSP 密碼
TELEGRAM_TOKEN=your_bot_token  # BotFather 取得
TELEGRAM_CHAT_ID=your_chat_id  # @userinfobot 取得
```

## 服務說明

| 服務 | Port | 用途 |
|---|---|---|
| Frigate | 5000 | Web UI、影像串流、錄影管理 |
| go2rtc (內建) | 8554 | RTSP relay |
| Mosquitto | 1883 | MQTT broker（內部用） |
| notification-bridge | — | Frigate events → Telegram |

所有 port 只綁定 `127.0.0.1`，透過 Tailscale 遠端存取。

## 遠端存取

手機安裝 Tailscale App，登入同一帳號後開啟：

```
http://<Pi的Tailscale IP>:5000
```

## 儲存策略

| 位置 | 內容 | 保留 |
|---|---|---|
| USB SSD `/media/frigate` | 連續錄影 | 3 天 |
| USB SSD `/media/frigate` | Motion clips | 7 天 |
| Synology NAS | 全部備份 | 30+ 天 |

每日 02:00 自動 rsync 至 NAS。

## 專案結構

```
homelab/
├── docker-compose.yml
├── .env                    ← 機密，不進 git
├── .env.example            ← 範本，已進 git
├── config/
│   └── config.yml          ← Frigate 設定
├── mosquitto/
│   └── mosquitto.conf
├── notification-bridge/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
└── docs/
    └── superpowers/
        ├── specs/          ← 架構設計文件
        └── plans/          ← 實作計畫
```

## Tailscale IP

記錄在 Pi 400 上執行 `tailscale ip -4` 的結果。
