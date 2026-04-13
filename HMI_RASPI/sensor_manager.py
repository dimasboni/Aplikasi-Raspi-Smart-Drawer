import paho.mqtt.client as mqtt
# Kita panggil alat dari database manager buatan kita sendiri!
from db_manager import update_stok_otomatis
from config import settings

status_sensor_realtime = {
    "SL6x150mm": 1, 
    "SL5x100mm": 1
}

# --- KONFIGURASI MQTT ---
MQTT_BROKER = settings.get("mqqt_broker", "10.195.71.120")
MQTT_PORT = settings.get("mqqt_port", 1883)

def on_mqtt_connect(client, userdata, flags, rc):
    print(f"✅ Berhasil terhubung ke MQTT Broker! Status Code: {rc}")
    client.subscribe("laci/#") 
    print("🎧 Flet Standby mendengarkan Wemos...")

def on_mqtt_message(client, userdata, msg):
    topik = msg.topic
    pesan = msg.payload.decode("utf-8")
    print(f"🚨 [RADAR SENSOR] Masuk! Topik: '{topik}' | Pesan: '{pesan}'")
    
    # Kita harus import sqlite disini sebentar untuk ngecek topik MQTT-nya punya alat apa
    import sqlite3 
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM tools WHERE mqtt_topic = ?", (topik,))
            res = cursor.fetchone()

        if res:
            nama_alat = res[0]
            val = int(pesan)
            if status_sensor_realtime.get(nama_alat) != val:
                status_sensor_realtime[nama_alat] = val
                
                # Nah, ini dia. Sensor meminta manajer database untuk update stok!
                update_stok_otomatis(nama_alat, val) 
                
                status_str = "DITARUH (Stok 1)" if val == 1 else "DIANGKAT (Stok 0)"
                print(f"✅ [SENSOR -> DB] {nama_alat} -> {status_str}")
    except Exception as e:
        print(f"❌ Error DB Flet: {e}")

def jalankan_sensor_background():
    """Fungsi ini dipanggil oleh main file untuk menyalakan sensor secara diam-diam"""
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start() 
        return True
    except Exception as e:
        print(f"❌ Gagal konek MQTT: {e}")
        return False
