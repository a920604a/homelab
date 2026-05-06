# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案性質

這是一個地端監控系統的 **infrastructure-as-code** 專案，部署目標是 Raspberry Pi 400（ARM64）。唯一需要撰寫程式碼的元件是 `notification-bridge`（Python）。其餘都是設定檔。

## 常用指令

```bash
# 啟動所有服務
docker compose up -d

# 查看所有服務狀態
docker compose ps

# 看 log（全部）
docker compose logs -f

# 看單一服務 log
docker compose logs -f frigate
docker compose logs -f notification-bridge

# 重建並重啟 notification-bridge（改完 main.py 後）
docker compose build notification-bridge && docker compose restart notification-bridge

# 停止所有服務
docker compose down
```

## 架構

三個 Docker 服務 + host 層的 Tailscale：

```
Frigate ←── RTSP ── Tapo C200
   │
   │ MQTT events
   ▼
Mosquitto ──→ notification-bridge ──→ Telegram Bot API
```

- **Frigate** (`ghcr.io/blakeblackshear/frigate:stable`)：NVR 核心，內建 go2rtc。設定在 `config/config.yml`，錄影存至 `/media/frigate`（Pi 400 上的 USB SSD）。
- **Mosquitto** (`eclipse-mosquitto:2`)：MQTT broker，設定在 `mosquitto/mosquitto.conf`。有 healthcheck，其他服務的 `depends_on` 都等它 healthy 才啟動。
- **notification-bridge**（本地 build）：唯一自己寫的程式，見下方說明。
- **Tailscale**：裝在 Pi 400 host 層，不在 Docker Compose 裡。提供遠端存取，所有 port 只綁 `127.0.0.1`。

## notification-bridge 的設計

`notification-bridge/main.py` 是唯一需要維護的程式碼：

- 訂閱 Mosquitto 的 `frigate/events` topic
- 只處理 `type: "new"` 事件（忽略 update/end，避免重複通知）
- Rate limiting：同一 `camera:label` 組合，60 秒內只發一次（`RATE_LIMIT_SECONDS` 可覆寫）
- 從 Frigate HTTP API 取得 snapshot（`/api/events/{id}/snapshot.jpg`），有圖就發 photo，失敗則 fallback 發純文字
- HTTP 呼叫在 daemon thread 裡執行，不阻塞 MQTT loop
- `on_connect` callback 處理 resubscribe（確保 broker 重啟後自動恢復訂閱）

## 設定檔說明

**`config/config.yml`（Frigate）：**
- 攝影機帳密用 `{FRIGATE_RTSP_USER}` 格式（Frigate 的 env var 語法，非 shell 語法）
- stream2（640x360, 5fps）給 detect，stream1（1080p）給 record
- CPU detector，2 threads（Pi 400 的 ARM Cortex-A72 @ 1.8GHz）
- hwaccel：`preset-rpi-64-h264`（Pi 400 的 V4L2 M2M 硬體解碼）

**`.env`（不進 git）：**
```
CAMERA_IP=          # Tapo C200 的 LAN IP
RTSP_USER=          # Tapo RTSP 帳號
RTSP_PASSWORD=      # Tapo RTSP 密碼
TELEGRAM_TOKEN=     # Telegram Bot token
TELEGRAM_CHAT_ID=   # 接收通知的 chat ID
```

## 新增攝影機

在 `config/config.yml` 的 `cameras:` 下新增一個 entry（複製 `living_room` 結構），調整 stream URL 中的 IP 即可。Frigate 和 notification-bridge 都會自動處理多攝影機。

## 已知限制與 Phase 2

- `/media/frigate` 只存在於 Pi 400（USB SSD），在開發機上 docker compose 無法正常啟動
- `privileged: true` 已移除（IP camera 不需要）；若日後加 Coral TPU，需加回 `devices: /dev/bus/usb`
- Home Assistant 整合預留在 Phase 2，屆時加入 `docker-compose.yml` 並透過 MQTT 與 Frigate 整合
- NAS 備份透過 Pi 400 host 的 cron job 執行，不在 Docker Compose 管理範圍內
