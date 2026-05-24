import paho.mqtt.client as mqtt
from db_manager import update_stok_otomatis
from config import settings

status_sensor_realtime = {
    "SL6x150mm": 1, 
    "SL5x100mm": 1
}

# --- KONFIGURASI MQTT ---
MQTT_BROKER = settings.get("mqqt_broker", "localhost")
MQTT_PORT = settings.get("mqqt_port", 1883)

def on_mqtt_connect(client, userdata, flags, rc):
    print(f"✅ Berhasil terhubung ke MQTT Broker! Status Code: {rc}")

    # 1. BUKA KUPING FASE 1: Mendengarkan Wemos yang baru nyala (Minta Config)
    client.subscribe("SmartDrawer/Daftar")

    # 2. BUKA KUPING FASE 2: Mendengarkan Sensor Radar Biasa
    lab_name = settings.get("lab_name", "Lab_mikrokontroler")
    cabinet_name = settings.get("cabinet_name", "Smart Drawer-01")
    topik_khusus = f"{lab_name}/{cabinet_name}/#"

    client.subscribe(topik_khusus) 
    print(f"🎧 Flet Standby mendengarkan Wemos di topik: {topik_khusus}")

def on_mqtt_message(client, userdata, msg):
    topik_asli = msg.topic
    pesan = msg.payload.decode("utf-8").strip() # Bersihkan spasi gaib di pesan
    
    # =========================================================
    # 🔥 FASE 1: AUTO-DISCOVERY (MERESPON WEMOS BARU NYALA)
    # =========================================================
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
                print(f"📡 [AUTO-DISCOVERY] Mengirim Identitas [{balasan_array}] ke Laci {nomor_laci_wemos}")
            else:
                print(f"🛑 [AUTO-DISCOVERY] Menolak Wemos penyusup dari {id_kabinet_wemos}!")
        return 

    # =========================================================
    # ⚙️ FASE 2: RADAR SENSOR OPERASIONAL (OBENG DIAMBIL/DITARUH)
    # =========================================================
    print(f"🚨 [RADAR] Paket Diterima! Topik: '{topik_asli}' | Pesan: '{pesan}'")

    potongan = topik_asli.split("/")
    if len(potongan) < 4:
        return 
    
    # Gunakan .strip() untuk membunuh spasi gaib yang nyelip!
    lab_sensor = potongan[-4].strip()       
    kabinet_sensor = potongan[-3].strip()   
    laci_sensor = int(potongan[-2]) 
    pin_sensor = potongan[-1].strip()       

    nama_lab_kita = settings.get("lab_name", "Lab_mikrokontroler").strip()
    nama_kabinet_kita = settings.get("cabinet_name", "Smart Drawer-01").strip()

    # CCTV 1: Cek Nama Lab dan Kabinet
    if lab_sensor != nama_lab_kita or kabinet_sensor != nama_kabinet_kita:
        print(f"⚠️ [DITOLAK] Identitas Beda! Dari Sensor: '{lab_sensor}/{kabinet_sensor}' VS Di Config: '{nama_lab_kita}/{nama_kabinet_kita}'")
        return
    
    kunci_unik = f"{laci_sensor}_{pin_sensor}"
    
    import sqlite3 
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            cursor = conn.cursor()
            # CCTV 2: Mencari alat di Database
            cursor.execute("SELECT name FROM tools WHERE mqtt_topic = ? AND page = ?", (pin_sensor, laci_sensor))
            res = cursor.fetchone()

        if res:
            nama_alat = res[0]
            val = int(pesan)
            print(f"🔍 [CEK STATUS] Alat: {nama_alat} | Kunci: {kunci_unik} | Status Memory: {status_sensor_realtime.get(kunci_unik, 1)} | Sensor Wemos: {val}")
            
            # CCTV 3: Memeriksa Perubahan Angka Sensor
            if status_sensor_realtime.get(kunci_unik, 1) != val:
                status_sensor_realtime[kunci_unik] = val
                update_stok_otomatis(pin_sensor, laci_sensor, val) 
                
                status_str = "DITARUH (Stok 1)" if val == 1 else "DIANGKAT (Stok 0)"
                print(f"✅ [SUKSES MASUK FLET] {nama_alat} (Laci {laci_sensor}-{pin_sensor}) -> {status_str}")
            else:
                print(f"ℹ️ [DIABAIKAN] Status sensor tidak berubah (Tetap {val})")
        else:
            print(f"🛑 [DB KOSONG] Tidak ada nama alat yang terdaftar di Database untuk Laci {laci_sensor} posisi {pin_sensor}")
            
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