import paho.mqtt.client as mqtt

# Configuratie
BROKER = "192.168.0.100"      # IP of hostname van de MQTT broker
PORT = 1883               # Meestal 1883 voor MQTT zonder TLS
TOPIC = "#"               # '#' betekent: abonneer op ALLE topics

USERNAME = "loxberry"   # <-- Pas aan
PASSWORD = "loxberry"  # <-- Pas aan

# Callback: connectie gemaakt
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Verbonden met broker")
        client.subscribe(TOPIC)
        print(f"📡 Geabonneerd op alle topics ({TOPIC})")
    else:
        print(f"❌ Connectie mislukt, code: {rc}")

# Callback: bericht ontvangen
def on_message(client, userdata, msg):
    print(f"[{msg.topic}] {msg.payload.decode('utf-8')}")

# MQTT client aanmaken
client = mqtt.Client()

# Inloggegevens instellen
client.username_pw_set(USERNAME, PASSWORD)

# Callbacks koppelen
client.on_connect = on_connect
client.on_message = on_message

# Verbinden met broker
client.connect(BROKER, PORT, keepalive=60)

# Start loop (oneindig)
client.loop_forever()
