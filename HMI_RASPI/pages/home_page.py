"""
home_page.py
============
Berisi halaman utama (Home / Splash Screen) aplikasi:
  - show_home : Tampilan awal dengan pilihan Admin / User

Cara pemakaian:
    from pages.home_page import register_home_page
    register_home_page(page, session_data, nav)
"""

import asyncio
import os

import flet as ft

from config import TEXT_COLOR
from ui_komponen import create_filled_button, create_menu_card, build_standard_layout
from hardware_manager import bersihkan_gpio

def register_home_page(page: ft.Page, session_data: dict, nav: dict):
    """
    Mendaftarkan fungsi show_home ke dalam dict 'nav'.
    nav keys yang ditambahkan:
        nav['show_home']
    """

    def show_home(e=None):
        # Bersihkan overlay & layar
        page.overlay.clear()
        page.clean()

        # Fungsi keluar aplikasi
        async def keluar_aplikasi(e=None):
            # 1. AMANKAN HARDWARE
            print("1. Membersihkan pin perangkat keras...")
            bersihkan_gpio()

            # 2. BANGKITKAN TASKBAR
            print("2. Menyalakan taskbar raspi kembali...")
            os.system("/usr/bin/lwrespawn /usr/bin/wf-panel-pi &")

            # 3. BUKA GEMBOK & TUTUP LAYAR (TANPA KATA 'AWAIT'!)
            print("3. Membuka gembok dan menutup layar Flet...")
            page.window.prevent_close = False
            page.update()
            
            # 🔥 INI KUNCINYA: Jangan pakai await di sini!
            page.window.close() 

            # Beri jeda sedikit agar sistem OS sempat merender penutupan jendela
            await asyncio.sleep(0.5)

            # 4. MATIKAN PYTHON
            print("4. Mematikan proses Python...")
            os._exit(0)

        def pemicu_exit(e):
            # memanggil login admin dulu sebelum benar-benar keluar
            nav["show_login_admin"](
                tujuan=lambda: page.run_task(keluar_aplikasi),
                teks_judul="Exit Application",
                teks_button="EXIT",
                button_color="red",
                
            )

        layout = build_standard_layout(
            title_text="SMART DRAWER",
            content_control=ft.Column(
                [
                    ft.Container(height=15),
                    ft.Row(
                        [
                            create_menu_card(
                                "Admin",
                                "Kelola sistem",
                                "admin.png",
                                "#D1EAF0",
                                lambda _: nav["show_rfid_page"](
                                    "Scan Kartu Admin",
                                    nav["show_login_admin"],
                                    show_home,
                                    "admin",
                                ),
                            ),
                            create_menu_card(
                                "User",
                                "Pinjam alat",
                                "user.png",
                                "#D6F5D6",
                                lambda _: nav["show_menu_user"](),
                            ),
                        ],
                        alignment="center",
                        spacing=40,
                    ),
                ],
                horizontal_alignment="center",
                alignment="center",
                margin=ft.margin.only(top=-100)
            ),
            action_button=ft.PopupMenuButton(
                icon=ft.Icons.EXIT_TO_APP_SHARP,
                icon_color="red",
                icon_size=50,
                items=[
                    ft.PopupMenuItem(
                        content=ft.Text("Exit Application", color="red"),
                        on_click=pemicu_exit,
                    )
                ],
            ),
        )

        page.add(layout)
        page.update()

    nav["show_home"] = show_home
