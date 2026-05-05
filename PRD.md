# PRD — 租屋處地端監控系統（MVP）

## 1. 專案目標（Goal）

建立一套：

* 低成本
* 完全地端（Local-first）
* 可擴充
* 不依賴訂閱
* 可整合 Home Assistant / Frigate / NAS

的租屋監控系統。

---

# 2. 核心需求（Requirements）

## Functional Requirements

### FR-1 即時影像串流

系統需支援：

* 手機查看即時影像
* Web UI 查看
* 多 client 同時觀看

---

### FR-2 本地錄影

系統需支援：

* 事件錄影
* 連續錄影（可選）
* 保存至：

  * Local SSD
  * NAS

---

### FR-3 RTSP 支援

Camera 必須支援：

* RTSP
* H264/H265

供：

* Frigate
* VLC
* Home Assistant

使用。

---

### FR-4 多攝影機支援

系統需支援：

```text
>= 2 cameras
```

未來可擴展至：

```text
4~8 cameras
```

---

### FR-5 異常事件通知

系統需支援：

* Motion detection
* Person detection（未來）

通知方式：

* Telegram
* LINE
* Home Assistant App

---

### FR-6 Local-only Operation

系統在無網際網路時：

* 仍可錄影
* 仍可串流
* 仍可事件通知（LAN）

---

# 3. Non-Functional Requirements

---

## NFR-1 資訊安全

### 必須：

* Camera 不可直接暴露至 Internet
* 禁止 P2P cloud access
* Router firewall 阻擋 WAN

---

## NFR-2 可維護性

系統需：

* Docker 化
* 可 backup config
* 可快速更換 camera

---

## NFR-3 擴展性

後續需可整合：

* Home Assistant
* MQTT
* Zigbee
* Door sensor
* Temperature sensor

---

## NFR-4 成本限制

MVP 成本：

```text
< NTD 3000
```

單 camera：

```text
< NTD 1000
```

---

# 4. MVP Scope（第一階段）

---

## In Scope

### Hardware

* 1 台 Camera
* 舊筆電 / Mini PC

---

### Software

* Frigate
* Docker Compose
* RTSP Streaming

---

### Storage

* Local SSD recording

---

### Networking

* LAN only
* Router firewall rules

---

# 5. Out of Scope（暫不做）

---

## Phase 2 才做

* Face recognition
* AI anomaly detection
* Cloud backup
* Multi-site management
* Remote VPN access
* Zigbee sensors
* VLAN segmentation
* NAS HA clustering

---

# 6. Architecture

## MVP Architecture

```text
+------------------+
| Camera (RTSP)    |
| Tapo C200        |
+--------+---------+
         |
         | RTSP
         v
+------------------+
| Frigate Docker   |
| Mini PC / Laptop |
+--------+---------+
         |
         | recordings
         v
+------------------+
| Local SSD / NAS  |
+------------------+
```

---

# 7. Camera Selection Criteria

---

## Required

| Feature         | Required |
| --------------- | -------- |
| RTSP            | YES      |
| Local stream    | YES      |
| Night vision    | YES      |
| Local recording | YES      |
| WiFi            | YES      |

---

## Preferred

| Feature          | Preferred |
| ---------------- | --------- |
| ONVIF            | YES       |
| H265             | YES       |
| Dual stream      | YES       |
| Person detection | YES       |

---

# 8. Recommended Hardware

## Camera (MVP)

### Primary Recommendation

* TP-Link Tapo C200

### Backup Options

* Tapo C210
* Reolink E1 (conditional)

---

## Host Device

### Option A

* Old laptop

### Option B

* Intel N100 Mini PC

---

# 9. Security Design

---

## Network Isolation

```text
Camera VLAN / IoT subnet
        ↓
Firewall deny internet
        ↓
Allow LAN RTSP only
```

---

## Security Policies

### SP-1

Disable UPnP

### SP-2

Block outbound internet for cameras

### SP-3

Strong RTSP credentials

### SP-4

Disable vendor cloud access

---

# 10. Storage Strategy

---

## Phase 1

Local SSD

```text
Retention:
3~7 days
```

---

## Phase 2

NAS integration

```text
Frigate → SMB/NFS → NAS
```

---

# 11. Deployment Strategy

---

## Container Runtime

```yaml
Docker Compose
```

---

## Core Services

| Service        | Purpose             |
| -------------- | ------------------- |
| Frigate        | NVR                 |
| go2rtc         | RTSP relay          |
| Home Assistant | automation (future) |

---

# 12. Future Expansion Roadmap

---

## Phase 2

* Home Assistant integration
* Telegram notifications
* Door sensors

---

## Phase 3

* Coral TPU
* AI person detection
* Smart automations

---

## Phase 4

* Full smart home platform
* MQTT event bus
* Central observability

---

# 13. Success Criteria

---

## MVP Success

系統需達成：

* Camera 穩定串流 24h
* 本地錄影正常
* Motion event 可回放
* 不依賴 cloud
* Internet disconnect 仍可運作

---

# 14. Recommended Final Stack

## MVP

```text
Tapo C200
+
Docker Frigate
+
Local SSD
```

---

## Long-term

```text
Reolink PoE Cameras
+
Frigate
+
Home Assistant
+
NAS
+
VLAN
```

