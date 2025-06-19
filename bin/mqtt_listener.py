import paho.mqtt.client as mqtt
from pymongo import MongoClient
import json

# MongoDB connectie
mongo = MongoClient("mongodb://mongodb:27017/")
db = mongo["attendance"]
collection = db["logs"]

# MQTT instellingen
MQTT_BROKER = "192.168.1.x"  # of 'loxberry.local'
MQTT_PORT = 1883
MQTT_TOPIC = "miniserver/timetracking"

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received: {payload}")
        collection.insert_one(payload)
    except Exception as e:
        print(f"Error: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
