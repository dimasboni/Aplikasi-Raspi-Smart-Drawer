import json 
import os

# --- KONFIGURASI WARNA TEMA ---
BG_COLOR = "#F3F6FF"
TEXT_COLOR = "#000000"
SUB_TEXT_COLOR = "#2D3748"
SHADOW_COLOR = "#20000000"

# --- WARNA KHUSUS ---
BLUE_SENSOR = "#4285F4"
GREEN_SENSOR = "#34A853" 

# --- UKURAN LAYAR STANDAR ---
PAGE_WIDTH = 1024
PAGE_HEIGHT = 600
HEADER_HEIGHT = 80
CONTENT_AREA_HEIGHT = 500


#IP API server untuk Database dan MQQT BROKER 
def load_settings():
    #mencari file config.json di folder yang sama dengan script 
    path = os.path.join(os.path.dirname(__file__), "config.json")

    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f) #tulisan json berubah jadi variabel python 
    return {
             "mqtt_broker": "10.195.71.120",
             "mqtt_port": 1883,
             "db_host": "10.195.71.208",
             "cabinet_name": "Smart Drawer System"
             }

#eksekusi sekali agar variabel load settings bisa digunakan 
settings = load_settings()

# Mengambil Kapasitas Laci dari Json 
RAW_CAPACITY = settings.get("drawer_capacity", {})

#m Konversi key teks "1" menjadi integer 1 
DRAWER_CAPACITY = {int(k): v for k, v in RAW_CAPACITY.items()}

#jika json belum ada isinya pakai default 16
if not DRAWER_CAPACITY: 
    DRAWER_CAPACITY = {1: 16, 2: 18, 3: 16, 4: 16}