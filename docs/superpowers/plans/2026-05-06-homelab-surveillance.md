# Homelab 租屋監控系統 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Raspberry Pi 400 上建立地端監控系統，支援即時串流、本地錄影、Telegram 通知、Tailscale 遠端存取、Synology NAS 備份。

**Architecture:** Frigate（NVR）+ Mosquitto（MQTT）+ notification-bridge（Python）跑在 Docker Compose，Tailscale 裝於 host 層提供安全遠端存取，rsync over SSH 每日備份至 Synology NAS。

**Tech Stack:** Raspberry Pi OS (64-bit), Docker, Docker Compose v2, Frigate 0.14, Mosquitto 2, Python 3.11, paho-mqtt, Tailscale, rsync

---

## 檔案結構

```
~/homelab/
  ├── docker-compose.yml
  ├── .env                              ← 機密，不進 git
  ├── .gitignore
  ├── config/
  │    └── config.yml                  ← Frigate 設定
  ├── mosquitto/
  │    └── mosquitto.conf
  └── notification-bridge/
       ├── Dockerfile
       ├── requirements.txt
       └── main.py
```

---

## Task 1: Raspberry Pi 400 系統準備

**Files:**
- 無（系統層設定）

- [ ] **Step 1: 安裝 Raspberry Pi OS (64-bit)**

至 https://www.raspberrypi.com/software/ 下載 Raspberry Pi Imager，選擇：
- OS: Raspberry Pi OS Lite (64-bit)
- 在 Imager 設定中啟用 SSH、設定 hostname (`homelab`)、設定 WiFi

燒錄至 microSD，插入 Pi 400 開機。

- [ ] **Step 2: 確認 SSH 連線**

```bash
ssh pi@homelab.local
```

Expected: 登入成功，顯示 Raspberry Pi OS prompt。

- [ ] **Step 3: 更新系統**

```bash
sudo apt update && sudo apt upgrade -y
```

- [ ] **Step 4: 安裝 Docker**

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker pi
newgrp docker
```

- [ ] **Step 5: 確認 Docker 正常**

```bash
docker run --rm hello-world
```

Expected: 輸出 `Hello from Docker!`

- [ ] **Step 6: 安裝 Docker Compose v2**

```bash
sudo apt install -y docker-compose-plugin
docker compose version
```

Expected: 輸出 `Docker Compose version v2.x.x`

- [ ] **Step 7: 掛載 USB SSD**

```bash
# 確認 SSD 裝置名稱
lsblk
# 假設為 /dev/sda，格式化為 ext4
sudo mkfs.ext4 /dev/sda1
sudo mkdir -p /media/frigate

# 取得 UUID
sudo blkid /dev/sda1
```

將以下加入 `/etc/fstab`（替換 UUID）：
```
UUID=<your-uuid>  /media/frigate  ext4  defaults,noatime  0  2
```

```bash
sudo mount -a
# 確認掛載
df -h /media/frigate
```

Expected: 顯示 USB SSD 掛載至 `/media/frigate`

- [ ] **Step 8: 建立 Frigate 資料目錄**

```bash
sudo mkdir -p /media/frigate/{recordings,clips,exports}
sudo chown -R pi:pi /media/frigate
```

- [ ] **Step 9: Commit（記錄 fstab 設定備忘）**

```bash
cd ~/homelab
echo "# USB SSD mounted at /media/frigate via /etc/fstab" >> README.md
git add README.md
git commit -m "docs: note USB SSD mount setup"
```

---

## Task 2: Tapo C200 攝影機設定

**Files:**
- 無（硬體設定）

- [ ] **Step 1: 安裝 Tapo App，完成初始設定**

在手機安裝 TP-Link Tapo App，新增 C200，完成 WiFi 配對。

- [ ] **Step 2: 確認 Camera IP**

在路由器管理介面找到 Tapo C200 的 IP，記下（例如 `192.168.1.100`）。

- [ ] **Step 3: 設定 RTSP 帳密**

Tapo App → 攝影機設定 → 進階設定 → 攝影機帳號 → 設定 username / password（記下，之後填入 `.env`）。

- [ ] **Step 4: 停用 Tapo 雲端**

Tapo App → 攝影機設定 → 隱私 → 關閉所有雲端功能（Tapo Care 等）。

- [ ] **Step 5: 封鎖 Camera 上網（路由器設定）**

進入路由器管理介面，找到 C200 的 MAC address，設定「封鎖網際網路存取」。

- [ ] **Step 6: 測試 RTSP 串流**

在同一 LAN 的電腦執行：
```bash
ffprobe -v quiet -print_format json -show_streams \
  "rtsp://<user>:<password>@192.168.1.100:554/stream1"
```

Expected: 輸出含 `codec_name: h264`、`width: 1920`、`height: 1080`。

---

## Task 3: 專案目錄結構建立

**Files:**
- Create: `~/homelab/.gitignore`
- Create: `~/homelab/.env`
- Create: `~/homelab/docker-compose.yml`（空殼，後續任務填充）

- [ ] **Step 1: 建立 .gitignore**

```bash
cat > ~/homelab/.gitignore << 'EOF'
.env
mosquitto/data/
mosquitto/log/
EOF
```

- [ ] **Step 2: 建立 .env 模板**

```bash
cat > ~/homelab/.env << 'EOF'
CAMERA_IP=192.168.1.100
RTSP_USER=your_rtsp_username
RTSP_PASSWORD=your_rtsp_password
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
EOF
```

填入實際值（RTSP 帳密從 Task 2 取得）。

- [ ] **Step 3: 建立空殼 docker-compose.yml**

```bash
cat > ~/homelab/docker-compose.yml << 'EOF'
services: {}
EOF
```

- [ ] **Step 4: Commit**

```bash
cd ~/homelab
git add .gitignore docker-compose.yml
git commit -m "chore: init project structure"
```

---

## Task 4: Mosquitto MQTT Broker 設定

**Files:**
- Create: `~/homelab/mosquitto/mosquitto.conf`
- Modify: `~/homelab/docker-compose.yml`

- [ ] **Step 1: 建立 mosquitto.conf**

```bash
mkdir -p ~/homelab/mosquitto
cat > ~/homelab/mosquitto/mosquitto.conf << 'EOF'
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest stdout
EOF
```

- [ ] **Step 2: 建立資料目錄**

```bash
mkdir -p ~/homelab/mosquitto/{data,log}
```

- [ ] **Step 3: 更新 docker-compose.yml**

```yaml
services:
  mosquitto:
    image: eclipse-mosquitto:2
    restart: unless-stopped
    volumes:
      - ./mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    ports:
      - "127.0.0.1:1883:1883"
```

- [ ] **Step 4: 啟動並測試**

```bash
cd ~/homelab
docker compose up -d mosquitto
docker compose logs mosquitto
```

Expected: 輸出含 `Starting in local-only mode`

```bash
# 測試 pub/sub
docker run --rm --network host eclipse-mosquitto:2 \
  mosquitto_pub -h 127.0.0.1 -t test -m "hello"
```

Expected: 無錯誤輸出。

- [ ] **Step 5: Commit**

```bash
git add mosquitto/ docker-compose.yml
git commit -m "feat: add mosquitto mqtt broker"
```

---

## Task 5: Frigate NVR 設定

**Files:**
- Create: `~/homelab/config/config.yml`
- Modify: `~/homelab/docker-compose.yml`

- [ ] **Step 1: 建立 config.yml**

```bash
mkdir -p ~/homelab/config
```

建立 `~/homelab/config/config.yml`：

```yaml
mqtt:
  enabled: true
  host: mosquitto
  port: 1883

cameras:
  living_room:
    ffmpeg:
      inputs:
        - path: rtsp://{FRIGATE_RTSP_USER}:{FRIGATE_RTSP_PASSWORD}@{FRIGATE_CAMERA_IP}:554/stream2
          roles:
            - detect
        - path: rtsp://{FRIGATE_RTSP_USER}:{FRIGATE_RTSP_PASSWORD}@{FRIGATE_CAMERA_IP}:554/stream1
          roles:
            - record
    detect:
      enabled: true
      width: 640
      height: 360
      fps: 5
    record:
      enabled: true
      retain:
        days: 3
        mode: all
      events:
        retain:
          default: 7
          mode: active_objects
    motion:
      threshold: 25
    snapshots:
      enabled: true
      retain:
        default: 7

detectors:
  cpu:
    type: cpu
    num_threads: 2
```

注意：Frigate 支援從環境變數替換 `{VAR}` 格式。

- [ ] **Step 2: 更新 docker-compose.yml，加入 frigate service**

完整 `docker-compose.yml`：

```yaml
services:
  frigate:
    image: ghcr.io/blakeblackshear/frigate:stable
    restart: unless-stopped
    shm_size: "64mb"
    volumes:
      - ./config:/config
      - /media/frigate:/media/frigate
    ports:
      - "127.0.0.1:5000:5000"
      - "127.0.0.1:8554:8554"
      - "127.0.0.1:8555:8555/tcp"
      - "127.0.0.1:8555:8555/udp"
    environment:
      - FRIGATE_RTSP_USER=${RTSP_USER}
      - FRIGATE_RTSP_PASSWORD=${RTSP_PASSWORD}
      - FRIGATE_CAMERA_IP=${CAMERA_IP}
    privileged: true
    depends_on:
      - mosquitto

  mosquitto:
    image: eclipse-mosquitto:2
    restart: unless-stopped
    volumes:
      - ./mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    ports:
      - "127.0.0.1:1883:1883"
```

- [ ] **Step 3: 啟動 Frigate**

```bash
cd ~/homelab
docker compose up -d frigate
docker compose logs -f frigate
```

等待約 30 秒，確認輸出含：
```
Frigate startup complete
```

- [ ] **Step 4: 確認 Frigate Web UI**

```bash
curl -s http://127.0.0.1:5000/api/version
```

Expected: 輸出 `{"version": "0.14.x", ...}`

- [ ] **Step 5: 確認攝影機串流**

```bash
curl -s http://127.0.0.1:5000/api/living_room/latest.jpg -o /tmp/test.jpg
ls -lh /tmp/test.jpg
```

Expected: 檔案大小 > 10KB（表示有拿到實際影像）。

- [ ] **Step 6: Commit**

```bash
git add config/docker-compose.yml
git commit -m "feat: add frigate nvr with cpu detector"
```

---

## Task 6: Notification Bridge（Telegram 通知）

**Files:**
- Create: `~/homelab/notification-bridge/Dockerfile`
- Create: `~/homelab/notification-bridge/requirements.txt`
- Create: `~/homelab/notification-bridge/main.py`
- Modify: `~/homelab/docker-compose.yml`

- [ ] **Step 1: 建立 Telegram Bot**

1. 在 Telegram 搜尋 `@BotFather`
2. 輸入 `/newbot`，取得 `TELEGRAM_TOKEN`
3. 搜尋 `@userinfobot`，取得自己的 `TELEGRAM_CHAT_ID`
4. 填入 `~/homelab/.env`

- [ ] **Step 2: 建立 requirements.txt**

```bash
mkdir -p ~/homelab/notification-bridge
cat > ~/homelab/notification-bridge/requirements.txt << 'EOF'
paho-mqtt==2.1.0
requests==2.32.3
EOF
```

- [ ] **Step 3: 建立 main.py**

```python
# ~/homelab/notification-bridge/main.py
import os
import json
import time
import requests
import paho.mqtt.client as mqtt

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
FRIGATE_HOST = os.environ.get("FRIGATE_HOST", "http://frigate:5000")


def send_telegram_photo(caption: str, image_bytes: bytes) -> None:
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
        data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
        files={"photo": ("snapshot.jpg", image_bytes, "image/jpeg")},
        timeout=10,
    )


def send_telegram_text(text: str) -> None:
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=10,
    )


def handle_event(data: dict) -> None:
    if data.get("type") != "new":
        return

    after = data.get("after", {})
    camera = after.get("camera", "unknown")
    label = after.get("label", "motion")
    event_id = after.get("id", "")
    score = after.get("score", 0)

    caption = f"[{camera}] {label} detected ({score:.0%})"

    try:
        resp = requests.get(
            f"{FRIGATE_HOST}/api/events/{event_id}/snapshot.jpg",
            timeout=5,
        )
        if resp.status_code == 200:
            send_telegram_photo(caption, resp.content)
            return
    except Exception:
        pass

    send_telegram_text(caption)


def on_message(client, userdata, msg) -> None:
    try:
        data = json.loads(msg.payload)
        handle_event(data)
    except Exception as e:
        print(f"Error processing message: {e}", flush=True)


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message

    while True:
        try:
            client.connect(MQTT_HOST, 1883, 60)
            client.subscribe("frigate/events")
            print(f"Connected to MQTT at {MQTT_HOST}, listening for events", flush=True)
            client.loop_forever()
        except Exception as e:
            print(f"MQTT error: {e}, retrying in 5s", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 建立 Dockerfile**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
CMD ["python", "main.py"]
```

- [ ] **Step 5: 更新 docker-compose.yml，加入 notification-bridge**

在 `services:` 底下加入：

```yaml
  notification-bridge:
    build: ./notification-bridge
    restart: unless-stopped
    environment:
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
      - MQTT_HOST=mosquitto
      - FRIGATE_HOST=http://frigate:5000
    depends_on:
      - mosquitto
      - frigate
```

- [ ] **Step 6: Build 並啟動**

```bash
cd ~/homelab
docker compose build notification-bridge
docker compose up -d notification-bridge
docker compose logs -f notification-bridge
```

Expected: 輸出 `Connected to MQTT at mosquitto, listening for events`

- [ ] **Step 7: 測試通知（模擬 MQTT 事件）**

```bash
docker compose exec mosquitto mosquitto_pub \
  -t "frigate/events" \
  -m '{"type":"new","after":{"camera":"living_room","label":"motion","id":"test123","score":0.85}}'
```

Expected: Telegram 收到 `[living_room] motion detected (85%)`（可能無圖，因為是假 event ID）。

- [ ] **Step 8: Commit**

```bash
git add notification-bridge/ docker-compose.yml
git commit -m "feat: add telegram notification bridge"
```

---

## Task 7: Tailscale 安裝

**Files:**
- 無（host 系統層設定）

- [ ] **Step 1: 在 Pi 400 安裝 Tailscale**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

輸出會有一個 URL，用瀏覽器開啟並登入 Tailscale 帳號授權。

- [ ] **Step 2: 確認 Tailscale IP**

```bash
tailscale ip -4
```

Expected: 輸出類似 `100.x.x.x` 的 Tailscale IP，記下此 IP。

- [ ] **Step 3: 設定開機自啟**

```bash
sudo systemctl enable tailscaled
```

- [ ] **Step 4: 在手機安裝 Tailscale App**

iOS / Android 安裝 Tailscale，登入同一帳號，確認 Pi 400 出現在裝置列表。

- [ ] **Step 5: 測試手機連線**

手機開 Tailscale，用瀏覽器開啟：
```
http://100.x.x.x:5000
```
（替換為 Step 2 的 Tailscale IP）

Expected: 看到 Frigate Web UI，有 `living_room` 攝影機畫面。

- [ ] **Step 6: Commit（記錄 Tailscale IP）**

```bash
cd ~/homelab
echo "TAILSCALE_IP=100.x.x.x" >> README.md
git add README.md
git commit -m "docs: note tailscale ip for remote access"
```

---

## Task 8: Synology NAS 備份設定

**Files:**
- 無（host 系統層設定）

- [ ] **Step 1: 在 Synology 開啟 SSH**

Synology DSM → 控制台 → 終端機與 SNMP → 啟動 SSH 服務。

- [ ] **Step 2: 在 Synology 建立備份帳號與目錄**

```bash
# 在 Synology SSH 中執行
sudo mkdir -p /volume1/frigate-backup
sudo useradd -m frigate-sync
sudo chown frigate-sync:users /volume1/frigate-backup
```

- [ ] **Step 3: 在 Pi 400 生成 SSH key**

```bash
ssh-keygen -t ed25519 -f ~/.ssh/synology_key -N ""
```

- [ ] **Step 4: 複製 Public Key 至 Synology**

```bash
ssh-copy-id -i ~/.ssh/synology_key.pub frigate-sync@192.168.x.x
```

輸入 frigate-sync 密碼完成設定。

- [ ] **Step 5: 測試免密碼連線**

```bash
ssh -i ~/.ssh/synology_key frigate-sync@192.168.x.x "echo ok"
```

Expected: 輸出 `ok`，沒有要求輸入密碼。

- [ ] **Step 6: 測試 rsync**

```bash
rsync -av --dry-run \
  -e "ssh -i /home/pi/.ssh/synology_key" \
  /media/frigate/ \
  frigate-sync@192.168.x.x:/volume1/frigate-backup/
```

Expected: 輸出檔案清單，沒有錯誤。

- [ ] **Step 7: 建立 cron job**

```bash
crontab -e
```

加入：
```
0 2 * * * rsync -av --delete -e "ssh -i /home/pi/.ssh/synology_key" /media/frigate/ frigate-sync@192.168.x.x:/volume1/frigate-backup/ >> /home/pi/logs/frigate-backup.log 2>&1
```

```bash
mkdir -p ~/logs
```

- [ ] **Step 8: 手動執行一次確認**

```bash
rsync -av \
  -e "ssh -i /home/pi/.ssh/synology_key" \
  /media/frigate/ \
  frigate-sync@192.168.x.x:/volume1/frigate-backup/
```

Expected: 傳輸完成，無錯誤。

- [ ] **Step 9: Commit**

```bash
cd ~/homelab
cat >> README.md << 'EOF'

## NAS Backup
- rsync over SSH to Synology, daily at 02:00
- Backup user: frigate-sync
- Destination: /volume1/frigate-backup/
- Log: ~/logs/frigate-backup.log
EOF
git add README.md
git commit -m "docs: note nas backup configuration"
```

---

## Task 9: 開機自啟驗證

**Files:**
- 無

- [ ] **Step 1: 確認 Docker 開機自啟**

```bash
sudo systemctl enable docker
sudo systemctl is-enabled docker
```

Expected: `enabled`

- [ ] **Step 2: 模擬重開機**

```bash
sudo reboot
```

等待 Pi 400 重開完畢（約 60 秒），重新 SSH 連入。

- [ ] **Step 3: 確認所有服務自動起來**

```bash
ssh pi@homelab.local
docker compose -f ~/homelab/docker-compose.yml ps
```

Expected:
```
NAME                    STATUS
homelab-frigate-1       Up
homelab-mosquitto-1     Up
homelab-notification-bridge-1  Up
```

- [ ] **Step 4: 確認 Tailscale 自動起來**

```bash
tailscale status
```

Expected: 顯示已連線，Pi 400 出現在列表。

---

## Task 10: 端到端系統驗證

**Files:**
- 無

- [ ] **Step 1: 確認 24h 串流穩定性（快速版）**

```bash
# 連續拉 60 秒串流，確認無中斷
timeout 60 ffmpeg \
  -rtsp_transport tcp \
  -i "rtsp://127.0.0.1:8554/living_room" \
  -c copy /dev/null \
  -loglevel error
echo "Exit code: $?"
```

Expected: Exit code 0，無錯誤輸出。

- [ ] **Step 2: 確認錄影檔案寫入 USB SSD**

```bash
ls -lh /media/frigate/recordings/
```

Expected: 有以日期命名的目錄，且持續有新檔案產生。

- [ ] **Step 3: 確認 Motion Event 可回放**

在 Frigate Web UI（`http://100.x.x.x:5000`）：
1. 在攝影機前揮手觸發 motion
2. 點選 Events 頁籤
3. 確認 event clip 出現且可播放

- [ ] **Step 4: 確認 Telegram 通知**

在攝影機前揮手，等待 30 秒內 Telegram 收到含 snapshot 的通知。

- [ ] **Step 5: 確認斷網後仍可運作**

```bash
# 拔掉 Pi 400 網路線（WiFi 斷開），或在路由器封鎖 Pi 的 WAN 存取
# 確認 Frigate 仍在錄影（本地 LAN 仍可連）
curl -s http://192.168.x.x:5000/api/version
```

Expected: 成功回應（注意：此測試需在 LAN 內執行，Tailscale 遠端無法測試斷網狀況）。

- [ ] **Step 6: 確認 NAS 備份（隔天確認）**

```bash
cat ~/logs/frigate-backup.log
```

Expected: 無錯誤，顯示傳輸完成訊息。

- [ ] **Step 7: 最終 Commit**

```bash
cd ~/homelab
git add -A
git commit -m "chore: finalize mvp setup documentation"
```

---

## 完成後系統狀態

```
Pi 400
  ├── Docker Compose (frigate + mosquitto + notification-bridge)
  ├── Tailscale (系統服務，開機自啟)
  └── cron: 每日 02:00 rsync → Synology NAS

手機
  ├── Tailscale App
  ├── 瀏覽器書籤: http://100.x.x.x:5000 (Frigate Web UI)
  └── Telegram Bot (接收通知)
```

## Phase 2 預備清單

- [ ] 加入 Home Assistant（docker-compose 新增 service）
- [ ] Coral USB TPU（Frigate config 改用 `edgetpu` detector）
- [ ] 換可管理路由器，設定 Camera VLAN
- [ ] 第二台攝影機（Frigate config 加 camera entry）
- [ ] NAS 掛為 Frigate 主儲存（NFS mount）
