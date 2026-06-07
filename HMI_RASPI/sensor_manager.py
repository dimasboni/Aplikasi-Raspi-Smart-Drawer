import paho.mqtt.client as mqtt
from db_manager import update_stok_otomatis
from config import settings
from hardware_manager import bunyikan_buzzer_error 

status_sensor_realtime = {
    "SL6x150mm": 1, 
    "SL5x100mm": 1
}

# 🔥 KOTAK SURAT MATA ELANG
target_expected = {
    "laci": None,
    "pin": None,
    "action": None  
}

MQTT_BROKER = settings.get("mqqt_broker", "localhost")
MQTT_PORT = settings.get("mqqt_port", 1883)

def on_mqtt_connect(client, userdata, flags, rc):
    print(f"✅ Berhasil terhubung ke MQTT Broker! Status Code: {rc}")
    client.subscribe("SmartDrawer/Daftar")
    lab_name = settings.get("lab_name", "Lab_mikrokontroler")
    cabinet_name = settings.get("cabinet_name", "Smart Drawer-01")
    topik_khusus = f"{lab_name}/{cabinet_name}/#"
    client.subscribe(topik_khusus) 
    print(f"🎧 Flet Standby mendengarkan Wemos di topik: {topik_khusus}")

def on_mqtt_message(client, userdata, msg):
    topik_asli = msg.topic
    pesan = msg.payload.decode("utf-8").strip() 
    
    if topik_asli == "SmartDrawer/Daftar":
        print(f"👋 [AUTO-DISCOVERY] Wemos minta KTP: {pesan}")
        potongan_pesan = pesan.split(",")
        if len(potongan_pesan) == 2:
            id_kabinet_wemos = potongan_pesan[0]
            nomor_laci_wemos = potongan_pesan[1]
            id_kabinet_di_python = settings.get("cabinet_id", "SD-01") 
            if id_kabinet_wemos == id_kabinet_di_python:
                lab_name = settings.get("lab_name", "Lab_mikrokontroler")
                cabinet_name = settings.get("cabinet_name", "Smart Drawer-01")
                balasan_array = f"{lab_name},{cabinet_name}"
                topik_balasan = f"SmartDrawer/Config/{id_kabinet_wemos}/Laci_{nomor_laci_wemos}"
                client.publish(topik_balasan, balasan_array)
            else:
                print(f"🛑 [AUTO-DISCOVERY] Menolak Wemos penyusup dari {id_kabinet_wemos}!")
        return 

    print(f"🚨 [RADAR] Paket Diterima! Topik: '{topik_asli}' | Pesan: '{pesan}'")
    potongan = topik_asli.split("/")
    if len(potongan) < 4:
        return 
    
    lab_sensor = potongan[-4].strip()       
    kabinet_sensor = potongan[-3].strip()   
    laci_sensor = int(potongan[-2]) 
    pin_sensor = potongan[-1].strip()       

    nama_lab_kita = settings.get("lab_name", "Lab_mikrokontroler").strip()
    nama_kabinet_kita = settings.get("cabinet_name", "Smart Drawer-01").strip()

    if lab_sensor != nama_lab_kita or kabinet_sensor != nama_kabinet_kita:
        return
    
    kunci_unik = f"{laci_sensor}_{pin_sensor}"
    val = int(pesan)
    status_sensor_realtime[kunci_unik] = val 

    # ====================================================
    # 🔥 DETEKSI SALAH LUBANG & AKTIFKAN BUZZER
    # ====================================================
    if target_expected["laci"] is not None:
        if laci_sensor == target_expected["laci"]:
            if pin_sensor != target_expected["pin"]:
                if target_expected["action"] == "AMBIL" and val == 0:
                    print(f"🚨 [BUZZER] SALAH AMBIL! Harusnya {target_expected['pin']}, dicabut di {pin_sensor}!")
                    bunyikan_buzzer_error(1.5)
                elif target_expected["action"] == "TARUH" and val == 1:
                    print(f"🚨 [BUZZER] SALAH TARUH! Harusnya {target_expected['pin']}, ditaruh di {pin_sensor}!")
                    bunyikan_buzzer_error(1.5)
    # ====================================================

    import sqlite3 
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            cursor = conn.cursor()
            res = cursor.execute("SELECT name FROM tools WHERE mqtt_topic = ? AND page = ?", (pin_sensor, laci_sensor)).fetchone()

        if res:
            nama_alat = res[0]
            update_stok_otomatis(pin_sensor, laci_sensor, val)
            status_str = "DITARUH (Stok 1)" if val == 1 else "DIANGKAT (Stok 0)"
            print(f"✅ [SUKSES MASUK FLET] {nama_alat} (Laci {laci_sensor}-{pin_sensor}) -> {status_str}")
        else:
            print(f"🛑 [DB KOSONG] Tidak ada nama alat di Laci {laci_sensor} posisi {pin_sensor}.")
            
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