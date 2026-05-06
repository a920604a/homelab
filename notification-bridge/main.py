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
