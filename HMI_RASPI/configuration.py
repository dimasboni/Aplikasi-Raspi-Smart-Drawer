import flet as ft
import json
import os

# Path ke file config.json
CONFIG_PATH = "config.json"

def load_config():
    """Membaca data dari config.json"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {} # Return kosong kalau file nggak ada

def save_config(data):
    """Menyimpan data kembali ke config.json"""
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)

def main(page: ft.Page):
    page.title = "Smart Drawer Config Editor"
    page.window.width = 600
    page.window.height = 700
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 30

    # 1. Load data saat aplikasi pertama kali dibuka
    config_data = load_config()

    # 2. Siapkan Komponen Input (diisi dengan data saat ini)
    txt_mqtt_broker = ft.TextField(label="MQTT Broker IP", value=config_data.get("mqqt_broker", ""))
    txt_mqtt_port = ft.TextField(label="MQTT Port", value=str(config_data.get("mqqt_port", "")))
    txt_db_host = ft.TextField(label="Database Host (API IP)", value=config_data.get("db_host", ""))
    txt_cabinet_name = ft.TextField(label="Cabinet Name", value=config_data.get("cabinet_name", ""))
    txt_lab_name = ft.TextField(label="Lab Name", value=config_data.get("lab_name", ""))

    # Mengambil kapasitas laci (Ambil dari dict JSON)
    drawer_caps = config_data.get("drawer_capacity", {"1": 16, "2": 16, "3": 16, "4": 16})
    txt_laci_1 = ft.TextField(label="Kapasitas Laci 1", value=str(drawer_caps.get("1", "")), width=125)
    txt_laci_2 = ft.TextField(label="Kapasitas Laci 2", value=str(drawer_caps.get("2", "")), width=125)
    txt_laci_3 = ft.TextField(label="Kapasitas Laci 3", value=str(drawer_caps.get("3", "")), width=125)
    txt_laci_4 = ft.TextField(label="Kapasitas Laci 4", value=str(drawer_caps.get("4", "")), width=125)

    # 3. Fungsi Eksekusi Simpan
    def on_save(e):
        try:
            # Update dictionary dengan nilai baru dari inputan UI
            config_data["mqqt_broker"] = txt_mqtt_broker.value
            config_data["mqqt_port"] = int(txt_mqtt_port.value)
            config_data["db_host"] = txt_db_host.value
            config_data["cabinet_name"] = txt_cabinet_name.value
            config_data["lab_name"] = txt_lab_name.value

            # Update Dictionary kapasitas laci
            config_data["drawer_capacity"] = {
                "1": int(txt_laci_1.value),
                "2": int(txt_laci_2.value),
                "3": int(txt_laci_3.value),
                "4": int(txt_laci_4.value)
            }

            # Timpa file lama dengan fungsi save_config
            save_config(config_data)
            
            # Kasih notifikasi hijau kalau sukses
            page.snack_bar = ft.SnackBar(ft.Text("✅ Konfigurasi berhasil disimpan!"), bgcolor="green")
            page.snack_bar.open = True
            page.update()
        except ValueError:
            # Kasih notifikasi merah kalau salah masukin huruf di kolom angka
            page.snack_bar = ft.SnackBar(ft.Text("❌ Gagal! Pastikan Port dan Kapasitas diisi dengan angka."), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    btn_save = ft.ElevatedButton("Simpan Konfigurasi", on_click=on_save, bgcolor="#3B82F6", color="white", width=200, height=50)

    # 4. Tampilkan semua ke layar
    page.add(
        ft.Text("⚙️ Setup Sistem Smart Drawer", size=28, weight="bold"),
        ft.Text("Sesuaikan alamat IP server dan data kabinet di bawah ini.", color="grey"),
        ft.Divider(),
        txt_mqtt_broker,
        txt_mqtt_port,
        txt_db_host,
        txt_cabinet_name,
        txt_lab_name,
        ft.Container(height=10),
        ft.Text("Kapasitas Sensor per Laci:", weight="bold"),
        ft.Row([txt_laci_1, txt_laci_2, txt_laci_3, txt_laci_4]),
        ft.Container(height=20),
        btn_save
    )

# Jalankan via CMD seperti biasa: python config_editor.py
if __name__ == "__main__":
    ft.app(target=main)