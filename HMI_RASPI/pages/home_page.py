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
        async def keluar_aplikasi():
            print("1. Menutup layar UI Flet...")
            await page.window.close()
            await asyncio.sleep(0.5)
            print("2. Mematikan proses python...")
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
                alignment=ft.MainAxisAlignment.START,
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
