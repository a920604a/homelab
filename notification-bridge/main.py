import os
import json
import time
import threading
import requests
import paho.mqtt.client as mqtt

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
FRIGATE_HOST = os.environ.get("FRIGATE_HOST", "http://frigate:5000")
RATE_LIMIT_SECONDS = int(os.environ.get("RATE_LIMIT_SECONDS", "60"))

_last_sent: dict[str, float] = {}
_lock = threading.Lock()


def send_telegram_photo(caption: str, image_bytes: bytes) -> None:
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
            files={"photo": ("snapshot.jpg", image_bytes, "image/jpeg")},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"Telegram photo error: {e}", flush=True)
        send_telegram_text(caption)


def send_telegram_text(text: str) -> None:
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"Telegram text error: {e}", flush=True)


def _dispatch_notification(camera: str, label: str, event_id: str, score: float) -> None:
    caption = f"[{camera}] {label} detected ({score:.0%})"

    if event_id:
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


def handle_event(data: dict) -> None:
    if data.get("type") != "new":
        return

    after = data.get("after", {})
    camera = after.get("camera", "unknown")
    label = after.get("label", "motion")
    event_id = after.get("id")
    score = after.get("score", 0)

    rate_key = f"{camera}:{label}"
    now = time.monotonic()
    with _lock:
        if now - _last_sent.get(rate_key, 0) < RATE_LIMIT_SECONDS:
            return
        _last_sent[rate_key] = now

    threading.Thread(
        target=_dispatch_notification,
        args=(camera, label, event_id, score),
        daemon=True,
    ).start()


def on_connect(client, userdata, flags, reason_code, properties) -> None:
    if reason_code.is_failure:
        print(f"MQTT connection failed: {reason_code}", flush=True)
        return
    client.subscribe("frigate/events")
    print(f"Connected to MQTT at {MQTT_HOST}:{MQTT_PORT}, subscribed to frigate/events", flush=True)


def on_message(client, userdata, msg) -> None:
    try:
        data = json.loads(msg.payload)
        handle_event(data)
    except Exception as e:
        print(f"Error processing message: {e}", flush=True)


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.loop_forever()
        except Exception as e:
            print(f"MQTT error: {e}, retrying in 5s", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
