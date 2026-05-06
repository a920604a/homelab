# 手動設置指南

這份文件列出所有需要手動操作的步驟，無法由程式自動完成。
按照順序執行。

---

## 第一部分：Raspberry Pi 400 系統準備

### 1-1. 安裝 Raspberry Pi OS

1. 下載 [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. 選擇 OS：**Raspberry Pi OS Lite (64-bit)**
3. 點擊齒輪圖示進入進階設定：
   - 啟用 SSH
   - 設定 hostname：`homelab`
   - 設定 WiFi（SSID + 密碼）
   - 設定使用者帳號密碼
4. 燒錄至 microSD，插入 Pi 400 開機

### 1-2. SSH 連入確認

```bash
ssh pi@homelab.local
```

### 1-3. 更新系統

```bash
sudo apt update && sudo apt upgrade -y
```

### 1-4. 安裝 Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker pi
newgrp docker
```

確認：
```bash
docker run --rm hello-world
# 預期輸出：Hello from Docker!
```

### 1-5. 安裝 Docker Compose v2

```bash
sudo apt install -y docker-compose-plugin
docker compose version
# 預期輸出：Docker Compose version v2.x.x
```

### 1-6. 掛載 USB SSD

```bash
# 確認裝置名稱（通常是 /dev/sda）
lsblk

# 格式化（替換 /dev/sda1 為實際裝置）
sudo mkfs.ext4 /dev/sda1
sudo mkdir -p /media/frigate

# 取得 UUID
sudo blkid /dev/sda1
# 輸出類似：UUID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

編輯 `/etc/fstab`，加入以下一行（替換 UUID）：
```
UUID=<your-uuid>  /media/frigate  ext4  defaults,noatime  0  2
```

```bash
sudo mount -a

# 確認掛載
df -h /media/frigate
# 預期看到 USB SSD 掛載在此路徑

# 建立目錄並設定權限
sudo mkdir -p /media/frigate/{recordings,clips,exports}
sudo chown -R pi:pi /media/frigate
```

### 1-7. 設定 Docker 開機自啟

```bash
sudo systemctl enable docker
```

---

## 第二部分：Tapo C200 攝影機設定

### 2-1. 初始設定

1. 手機安裝 **TP-Link Tapo App**
2. 新增裝置 → Tapo C200
3. 完成 WiFi 配對

### 2-2. 設定 RTSP 帳密

Tapo App → 攝影機設定 → 進階設定 → **攝影機帳號**

設定 username 和 password（記下，填入 `.env`）

### 2-3. 停用雲端功能

Tapo App → 攝影機設定 → 隱私

關閉所有雲端功能（Tapo Care 等）

### 2-4. 取得 Camera IP

進入路由器管理介面，找到 Tapo C200 的 IP（例如 `192.168.1.100`）。

填入 `.env` 的 `CAMERA_IP`。

### 2-5. 封鎖 Camera 上網

路由器管理介面 → 找到 C200 的 MAC address → 設定「封鎖網際網路存取」

> Camera 只需要在 LAN 內與 Pi 400 通訊，不需要上網。

### 2-6. 測試 RTSP（在同一 LAN 的電腦上）

```bash
ffprobe -v quiet -print_format json -show_streams \
  "rtsp://<user>:<password>@<camera-ip>:554/stream1"
```

預期輸出含：`"codec_name": "h264"`, `"width": 1920`, `"height": 1080`

---

## 第三部分：部署監控系統

### 3-1. Clone Repo 至 Pi 400

```bash
git clone <repo-url> ~/homelab
cd ~/homelab
```

### 3-2. 填入設定值

```bash
cp .env.example .env
nano .env
```

填入：
```
CAMERA_IP=192.168.1.100
RTSP_USER=<Tapo RTSP 帳號>
RTSP_PASSWORD=<Tapo RTSP 密碼>
TELEGRAM_TOKEN=<Bot Token>
TELEGRAM_CHAT_ID=<你的 Chat ID>
```

**取得 Telegram Bot Token：**
1. Telegram 搜尋 `@BotFather`
2. 輸入 `/newbot`，依指示完成建立
3. 複製 Token

**取得 Telegram Chat ID：**
1. Telegram 搜尋 `@userinfobot`
2. 傳送任意訊息，它會回覆你的 ID

### 3-3. 啟動服務

```bash
docker compose up -d
docker compose ps
```

預期所有服務狀態為 `Up`：
```
homelab-frigate-1              Up
homelab-mosquitto-1            Up
homelab-notification-bridge-1  Up
```

### 3-4. 確認 Frigate 正常

```bash
curl -s http://127.0.0.1:5000/api/version
# 預期輸出：{"version": "0.14.x", ...}

# 確認攝影機有畫面
curl -s http://127.0.0.1:5000/api/living_room/latest.jpg -o /tmp/test.jpg
ls -lh /tmp/test.jpg
# 預期：檔案 > 10KB
```

---

## 第四部分：Tailscale 設定

### 4-1. Pi 400 安裝 Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

終端機會顯示一個 URL，用瀏覽器開啟並登入 Tailscale 帳號授權。

### 4-2. 確認 Tailscale IP

```bash
tailscale ip -4
# 輸出類似：100.x.x.x（記下此 IP）
```

### 4-3. 設定開機自啟

```bash
sudo systemctl enable tailscaled
```

### 4-4. 手機安裝 Tailscale App

1. iOS / Android 安裝 **Tailscale**
2. 登入與 Pi 400 相同的帳號
3. 確認 Pi 400 出現在裝置列表

### 4-5. 測試遠端存取

手機開啟 Tailscale，用瀏覽器開啟：
```
http://100.x.x.x:5000
```
（替換為 Step 4-2 的 Tailscale IP）

預期：看到 Frigate Web UI，有 `living_room` 攝影機畫面

### 4-6. 加到手機主畫面（PWA）

Safari / Chrome → 分享 → 加入主畫面

---

## 第五部分：Synology NAS 備份設定

### 5-1. Synology 開啟 SSH

DSM → 控制台 → 終端機與 SNMP → 勾選「啟動 SSH 功能」

### 5-2. 建立備份帳號與目錄

SSH 進入 Synology：
```bash
ssh admin@<synology-ip>
```

在 Synology 上執行：
```bash
sudo mkdir -p /volume1/frigate-backup
# 建立專用帳號（在 DSM 控制台 → 使用者帳號 → 新增）
# 帳號名：frigate-sync
# 給予 /volume1/frigate-backup 的讀寫權限
```

或直接在 DSM 控制台操作：
- 控制台 → 使用者帳號 → 新增使用者 `frigate-sync`
- 共用資料夾 → 建立 `frigate-backup`，給 `frigate-sync` 讀寫權限

### 5-3. Pi 400 生成 SSH Key

```bash
ssh-keygen -t ed25519 -f ~/.ssh/synology_key -N ""
```

### 5-4. 複製 Public Key 至 Synology

```bash
ssh-copy-id -i ~/.ssh/synology_key.pub frigate-sync@<synology-ip>
```

輸入 frigate-sync 密碼完成。

### 5-5. 測試免密碼連線

```bash
ssh -i ~/.ssh/synology_key frigate-sync@<synology-ip> "echo ok"
# 預期：輸出 ok，不要求輸入密碼
```

### 5-6. 測試 rsync

```bash
rsync -av --dry-run \
  -e "ssh -i /home/pi/.ssh/synology_key" \
  /media/frigate/ \
  frigate-sync@<synology-ip>:/volume1/frigate-backup/
# 預期：顯示檔案清單，無錯誤
```

### 5-7. 建立每日備份 Cron Job

```bash
mkdir -p ~/logs
crontab -e
```

加入這一行（替換 synology-ip）：
```
0 2 * * * rsync -av --delete -e "ssh -i /home/pi/.ssh/synology_key" /media/frigate/ frigate-sync@<synology-ip>:/volume1/frigate-backup/ >> /home/pi/logs/frigate-backup.log 2>&1
```

---

## 第六部分：驗證（開機自啟）

### 6-1. 重開機測試

```bash
sudo reboot
```

等待 60 秒後重新 SSH 連入。

### 6-2. 確認服務自動起來

```bash
docker compose -f ~/homelab/docker-compose.yml ps
```

預期全部顯示 `Up`。

### 6-3. 確認 Tailscale 自動起來

```bash
tailscale status
# 預期：顯示已連線
```

---

## 第七部分：端到端驗證

### 7-1. 確認串流

```bash
timeout 30 ffmpeg \
  -rtsp_transport tcp \
  -i "rtsp://127.0.0.1:8554/living_room" \
  -c copy /dev/null \
  -loglevel error
echo "Exit code: $?"
# 預期：Exit code 0
```

### 7-2. 確認錄影寫入 SSD

```bash
ls -lh /media/frigate/recordings/
# 預期：有以日期命名的目錄
```

### 7-3. 確認 Motion Event

在攝影機前揮手，等待 10 秒後：
```bash
curl -s http://127.0.0.1:5000/api/events | python3 -m json.tool | head -30
# 預期：看到 living_room 的 event 記錄
```

### 7-4. 確認 Telegram 通知

在攝影機前揮手，**30 秒內** Telegram 應收到含 snapshot 的通知。

### 7-5. 確認 NAS 備份（隔日）

```bash
cat ~/logs/frigate-backup.log
# 預期：無錯誤，顯示傳輸完成
```

---

## 快速參考

| 服務 | 存取方式 |
|---|---|
| Frigate Web UI（LAN）| `http://homelab.local:5000` |
| Frigate Web UI（遠端）| `http://<tailscale-ip>:5000` |
| 備份 log | `~/logs/frigate-backup.log` |
| 服務 log | `docker compose logs -f` |
| 重啟所有服務 | `docker compose restart` |
