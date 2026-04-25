"""
main.py
=======
Entry point utama aplikasi Smart Drawer System.

Tugas file ini HANYA:
  1. Inisialisasi halaman (ft.Page)
  2. Mendaftarkan semua modul halaman ke dalam 'nav' (navigation dict)
  3. Menjalankan show_home() sebagai halaman pertama

Semua logika UI ada di folder pages/:
  - pages/home_page.py    -> Halaman Utama (Home)
  - pages/admin_pages.py  -> Semua halaman Admin
  - pages/user_pages.py   -> Semua halaman User
  - pages/flow_pages.py   -> Alur transaksi (RFID & Sensor)

File pendukung lainnya:
  - config.py             -> Warna, ukuran, dan pengaturan
  - db_manager.py         -> Operasi database SQLite
  - sensor_manager.py     -> Pembacaan sensor IR background
  - ui_komponen.py        -> Komponen UI yang dapat digunakan ulang
"""

import flet as ft

# 1. IMPORT KONFIGURASI
from config import (
    BG_COLOR,
    PAGE_WIDTH,
    PAGE_HEIGHT,
    settings,
)

# 2. IMPORT SENSOR BACKGROUND
from sensor_manager import jalankan_sensor_background

# 3. IMPORT SEMUA MODUL HALAMAN
from pages.home_page import register_home_page
from pages.admin_pages import register_admin_pages
from pages.user_pages import register_user_pages
from pages.flow_pages import register_flow_pages


# ==============================================================================
# FUNGSI UTAMA FLET
# ==============================================================================
def main(page: ft.Page):
    # --- Pengaturan jendela ---
    page.window.maximized = True
    page.window.frameless = True       # Hilangkan border & title bar
    page.window.focused = True
    page.window.fullscreen = True      # Fullscreen agar tidak bisa ditutup sembarangan
    page.window.resizeable = False
    page.title = settings.get("cabinet_name", "Smart Drawer System")
    page.bgcolor = BG_COLOR
    page.expand = True
    page.padding = 0
    page.spacing = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # --- Nyalakan sensor di latar belakang ---
    #jalankan_sensor_background()

    # --- Data sesi bersama (dibagikan ke semua halaman) ---
    session_data = {"user_now": "Guest"}

    # --- Navigation dict: kumpulan referensi semua fungsi halaman ---
    # Dict ini kosong dulu, lalu diisi oleh masing-masing register_*
    # sehingga setiap modul bisa memanggil fungsi halaman lain
    nav = {}

    # --- Daftarkan semua modul (URUTAN PENTING! flow & user butuh nav['show_home']) ---
    register_home_page(page, session_data, nav)    # isi nav['show_home']
    register_admin_pages(page, session_data, nav)  # isi nav['show_admin_*'], nav['show_login_admin']
    register_user_pages(page, session_data, nav)   # isi nav['show_menu_user'], dll
    register_flow_pages(page, session_data, nav)   # isi nav['show_rfid_page'], dll

    # --- Mulai dari halaman utama ---
    nav["show_home"]()


# ==============================================================================
# ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
