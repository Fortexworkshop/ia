import json
import os
import random
import time

import paho.mqtt.client as mqtt


MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "fortex/capteurs/mesures")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_CA_CERT = os.getenv("MQTT_CA_CERT")  # defini = MQTTS


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="fortex-simulator",
)

if MQTT_USER:
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
if MQTT_CA_CERT:
    client.tls_set(ca_certs=MQTT_CA_CERT)

client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

print("Simulateur IoT FORTEX démarré")
print(f"Broker MQTT : {MQTT_HOST}:{MQTT_PORT}")
print(f"Topic       : {MQTT_TOPIC}")

try:
    while True:
        data = {
            "temperature": round(random.uniform(20, 30), 2),
            "humidite": round(random.uniform(40, 70), 2),
            "niveau_gaz": round(random.uniform(50, 250), 2),
            "presence": random.choice([True, False]),
        }

        message = json.dumps(data)

        result = client.publish(MQTT_TOPIC, message, qos=1)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Message envoyé : {message}")
        else:
            print(f"Erreur MQTT : code {result.rc}")

        time.sleep(5)

except KeyboardInterrupt:
    print("Arrêt du simulateur.")

finally:
    client.loop_stop()
    client.disconnect()
