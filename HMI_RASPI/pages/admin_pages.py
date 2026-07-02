"""
admin_pages.py
==============
Berisi semua halaman yang hanya bisa diakses oleh Admin:
  - show_edit_tools_menu     : Menu pilih Tambah/Manage alat
  - show_manage_tools_page   : Daftar alat + edit/hapus (pagination)
  - show_history_page        : Riwayat peminjaman dari database
  - show_add_tool_page       : Form tambah alat baru
  - show_admin_dashboard     : Dashboard utama admin
  - show_login_admin         : Form login username+password admin

Cara pemakaian:
    from pages.admin_pages import register_admin_pages
    register_admin_pages(page, session_data, nav)

'nav' adalah dict yang berisi referensi ke semua fungsi navigasi halaman lain,
sehingga halaman di sini bisa berpindah ke halaman manapun tanpa import melingkar.
"""

import os
import time
import random
import shutil
import sqlite3
import asyncio
import requests
import base64
import threading 
import bcrypt

import flet as ft
from PIL import Image as PILImage
from hardware_manager import buka_laci_otomatis, bunyikan_buzzer_error, buzzer_off
from sensor_manager import status_sensor_realtime, target_expected

from config import (
    BG_COLOR,
    TEXT_COLOR,
    SHADOW_COLOR,
    BLUE_SENSOR,
    GREEN_SENSOR,
    DRAWER_CAPACITY,
    settings
)
from db_manager import simpan_log, simpan_log_pengembalian
from ui_komponen import (
    create_filled_button,
    create_menu_card,
    build_standard_layout,
)


def register_admin_pages(page: ft.Page, session_data: dict, nav: dict):
    """
    Mendaftarkan semua fungsi halaman admin ke dalam dict 'nav'
    agar bisa dipanggil dari modul lain.

    Parameter:
        page         : objek ft.Page dari Flet
        session_data : dict bersama yang menyimpan info sesi (misal user_now)
        nav          : dict navigasi bersama, akan diisi dengan:
                         nav['show_admin_dashboard']
                         nav['show_edit_tools_menu']
                         nav['show_manage_tools_page']
                         nav['show_history_page']
                         nav['show_add_tool_page']
                         nav['show_login_admin']
    """

    # ------------------------------------------------------------------
    # SHOW EDIT TOOLS MENU
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # 1. MENU UTAMA EDIT TOOLS (Revisi: Hanya 2 Kartu)
    # ------------------------------------------------------------------
    def show_edit_tools_menu(e=None):
        page.clean()
        page.add(
            build_standard_layout(
                title_text="EDIT TOOLS",
                content_control=ft.Column(
                    [
                        ft.Column(height=15),
                        ft.Row(
                            [
                                create_menu_card(
                                    "Add Tools", "Tambah Alat", "tambah.png", "#E8F5E9",
                                    lambda _: show_add_method_menu(), # Mengarah ke menu cabang baru
                                ),
                                create_menu_card(
                                    "Manage", "Ubah / Hapus", "edit.png", "#E3F2FD",
                                    lambda _: show_manage_tools_page(),
                                ),
                            ],
                            alignment="center",
                            spacing=30,
                        ),
                    ],
                    horizontal_alignment="center",
                    alignment="center",
                    margin=ft.margin.only(top=-100),
                ),
                back_func=show_admin_dashboard,
            )
        )

    # ------------------------------------------------------------------
    # 2. SUB-MENU ADD TOOLS (Menu Cabang: Local vs Sync)
    # ------------------------------------------------------------------
    def show_add_method_menu(e=None):
        page.clean()
        page.add(
            build_standard_layout(
                title_text="ADD TOOL METHOD",
                content_control=ft.Column(
                    [
                        ft.Column(height=15),
                        ft.Row(
                            [
                                create_menu_card(
                                    "Local Add", "Tambah Manual", "tambah.png", "#FFF3E0",
                                    lambda _: show_add_tool_page(), # Mengarah ke form tambah lama
                                ),
                                create_menu_card(
                                    "Sync Web", "Tarik dari Web", "history.png", "#E1F5FE",
                                    lambda _: show_sync_web_page(), # Mengarah ke sinkronisasi
                                ),
                            ],
                            alignment="center",
                            spacing=30,
                        ),
                    ],
                    horizontal_alignment="center",
                    alignment="center",
                    margin=ft.margin.only(top=-100),
                ),
                back_func=show_edit_tools_menu, # Kembali ke menu utama Edit Tools
            )
        )
    # ------------------------------------------------------------------
    # SHOW MANAGE TOOLS PAGE  (dengan pagination)
    # ------------------------------------------------------------------
    def show_manage_tools_page(e=None):
        page.clean()
        page.overlay.clear()

        dialog_edit = ft.AlertDialog(title=ft.Text("Memuat..."))
        dialog_browser = ft.AlertDialog(
            title=ft.Text("Telusuri File Perangkat", weight="bold", color="black"),
            bgcolor="white",
        )
        dialog_hapus = ft.AlertDialog(
            title=ft.Text("Memuat..."), modal=True, bgcolor="white"
        )
        page.overlay.extend([dialog_edit, dialog_browser, dialog_hapus])
        page.update()

        async def tunda_lalu_refresh():
            await asyncio.sleep(0.4)
            show_manage_tools_page()
            page.update()

        # ---- Sub-fungsi: buka dialog edit alat ----
        def buka_dialog_edit(nama_alat_lama, rfid_lama, gambar_lama, kondisi_lama):
            preview_img = ft.Container(
                content=ft.Image(
                    src=f"/{gambar_lama}", width=150, height=150, fit="contain"
                )
            )
            path_gambar_sekarang = [gambar_lama]

            current_path = [os.path.expanduser("~")]
            file_list_view = ft.ListView(height=300, spacing=5)
            path_text = ft.Text(
                current_path[0], weight="bold", size=14, color="blue", expand=True
            )

            # Tombol navigasi drive (Windows vs Linux/Raspi)
            if os.name == "nt":
                tombol_drive = ft.Row(
                    [
                        path_text,
                        ft.ElevatedButton(
                            "💻 Drive C:",
                            bgcolor=BG_COLOR,
                            color=TEXT_COLOR,
                            on_click=lambda _: navigate_browser("c:\\"),
                        ),
                        ft.ElevatedButton(
                            "💻 Drive D:",
                            bgcolor=BG_COLOR,
                            color=TEXT_COLOR,
                            on_click=lambda _: navigate_browser("D:\\"),
                        ),
                    ]
                )
            else:
                tombol_drive = ft.Row(
                    [
                        path_text,
                        ft.ElevatedButton(
                            "🏠 Root (/)",
                            icon="folder",
                            bgcolor=BG_COLOR,
                            color=TEXT_COLOR,
                            on_click=lambda _: navigate_browser("/"),
                        ),
                        ft.ElevatedButton(
                            "🔌 USB/Media",
                            icon="usb",
                            bgcolor=BG_COLOR,
                            color=TEXT_COLOR,
                            on_click=lambda _: navigate_browser("/media"),
                        ),
                    ]
                )

            def update_browser_ui():
                file_list_view.controls.clear()
                path_text.value = f"Lokasi: {current_path[0]}"

                parent_dir = os.path.dirname(current_path[0])
                if parent_dir != current_path[0]:
                    file_list_view.controls.append(
                        ft.TextButton(
                            ".. (Kembali)",
                            icon="arrow_upward",
                            icon_color="#3B82F6",
                            style=ft.ButtonStyle(
                                color="black", alignment=ft.Alignment(-1, 0)
                            ),
                            width=580,
                            on_click=lambda _, p=parent_dir: navigate_browser(p),
                        )
                    )

                try:
                    items = os.listdir(current_path[0])

                except PermissionError:
                    file_list_view.controls.append(
                        ft.Text(
                            "Akses ditolak: Tidak memiliki izin untuk membuka folder ini.",
                            color="red",
                        )
                    )
                    page.update()
                    return
                except Exception as e:
                    file_list_view.controls.append(
                        ft.Text(f"Gagal membuka folder: {e}", color="red")
                    )
                    page.update()
                    return

                dirs = []
                files = []

                for item in items:
                    full_path = os.path.join(current_path[0], item)
                    try:
                        if os.path.isdir(full_path):
                            dirs.append(item)
                        elif item.lower().endswith((".png", ".jpg", ".jpeg")):
                            files.append(item)
                    except PermissionError:
                        pass
                    except Exception:
                        pass

                dirs.sort()
                files.sort()

                for d in dirs:
                    file_list_view.controls.append(
                        ft.TextButton(
                            d,
                            icon="folder",
                            icon_color="orange",
                            style=ft.ButtonStyle(
                                color="black", alignment=ft.Alignment(-1, 0)
                            ),
                            width=580,
                            on_click=lambda _, p=os.path.join(
                                current_path[0], d
                            ): navigate_browser(p),
                        )
                    )

                for f in files:
                    full_path = os.path.join(current_path[0], f)

                    try: 
                        thumb=ft.Image(
                            src=full_path, width=35, height=35, fit="contain"
                        )
                    except Exception:
                        thumb = ft.Icon(ft.icons.BUILD, color="#10B981")

                    file_list_view.controls.append(
                        ft.Row(
                            [
                                thumb,
                                ft.TextButton(
                                    f,
                                    style=ft.ButtonStyle(
                                        color="black", alignment=ft.Alignment(-1, 0)
                                    ),
                                    width=530,
                                    on_click=lambda _, p=full_path: pilih_file_manual(
                                        p
                                    ),
                                ),
                            ],
                            alignment="start",
                            vertical_alignment="center",
                            height=45,
                        )
                    )
                page.update()

            def navigate_browser(new_path):
                current_path[0] = new_path
                update_browser_ui()

            def pilih_file_manual(filepath):
                path_gambar_sekarang[0] = filepath
                try:
                    preview_img.content = ft.Image(
                        src=filepath, width=150, height=150, fit="contain"
                    )
                    dialog_browser.open = False
                    page.update()
                except Exception:
                    pass

            dialog_browser.content = ft.Column(
                [tombol_drive, ft.Divider(), file_list_view], width=600, tight=True
            )
            dialog_browser.actions = [
                ft.TextButton(
                    "Batal & Tutup Browser",
                    style=ft.ButtonStyle(color="black"),
                    on_click=lambda _: tutup_browser(),
                )
            ]

            def buka_browser_manual(e):
                update_browser_ui()
                dialog_browser.open = True
                page.update()

            def tutup_browser():
                dialog_browser.open = False
                page.update()

            def batal_edit(e):
                dialog_edit.open = False
                page.update()

            def eksekusi_simpan(e):
                try: 
                    filepath_asli = path_gambar_sekarang[0]
                    nama_asli = os.path.basename(filepath_asli)
                    nama_final = nama_asli 
                    lokasi_simpan_baru = None
                    if os.path.isabs(filepath_asli):
                        lokasi_simpan = os.path.join("assets", nama_asli)
                        
                        if os.path.abspath(filepath_asli) != os.path.abspath(lokasi_simpan):
                            
                            #DETEKTOR TABRAKAN NAMA
                            if os.path.exists(lokasi_simpan):
                                nama_file, ext = os.path.splitext(nama_asli)
                                counter = 1
                                while os.path.exists(os.path.join("assets", f"{nama_file}_{counter}{ext}")):
                                    counter += 1
                                nama_final = f"{nama_file}_{counter}{ext}"
                                lokasi_simpan = os.path.join("assets", nama_final)

                            shutil.copy(filepath_asli, lokasi_simpan)
                            lokasi_simpan_baru = lokasi_simpan #Menandai bahwa gambar di-Update

                    with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                        conn.execute(
                            "UPDATE tools SET name = ?, rfid_tag_uid = ?, img = ?, kondisi = ? WHERE rfid_tag_uid = ?",
                            (
                                input_nama.value,
                                input_rfid.value,
                                nama_final, 
                                dd_kondisi_edit.value, 
                                rfid_lama, 
                            ),
                        )
                        conn.commit()

                        #Sinkronisasi API NIKO (update gambar)
                        def kirim_api_update():
                            try: 
                                ip_server = settings.get("db_host", "127.0.0.1:8000")
                                # Menggunakan nama_alat_lama dari parameter fungsi sebagai ID pencarian
                                url_update = f"http://{ip_server}/api/v1/edit-alat/{nama_alat_lama}"
                                
                                payload = {
                                    "nama_alat": input_nama.value.strip(),
                                    "uid_tag_rfid": input_rfid.value.strip(),
                                    "kondisi": dd_kondisi_edit.value
                                }

                                if lokasi_simpan_baru: 
                                    with open(lokasi_simpan_baru, "rb") as f:
                                        payload["gambar_base64"] = base64.b64encode(f.read()).decode("utf-8")

                                requests.post(url_update, json=payload, headers={"Accept": "application/json"}, timeout=10)
                                print(f"Sukses update API: {input_nama.value.strip()}")
                            except Exception as e: 
                                print(f"Gagal update API: {e}")
                                
                        threading.Thread(target=kirim_api_update, daemon=True).start()
                        # --------------------------------------------------------

                        dialog_edit.open = False
                        page.run_task(tunda_lalu_refresh)

                except Exception as err:
                    pass

            input_nama = ft.TextField(label="Nama Alat", value=nama_alat_lama)
            input_rfid = ft.TextField(label="RFID tag UID", value=rfid_lama)

            dd_kondisi_edit = ft.Dropdown(
                label="Kondisi Alat",
                value=kondisi_lama if kondisi_lama else "baik", 
                options=[
                    ft.dropdown.Option(key="baik", text="Baik"),
                    ft.dropdown.Option(key="kurang baik", text="Kurang Baik"),
                    ft.dropdown.Option(key="rusak", text="Rusak"),
                ],
            )

            dialog_edit.title = ft.Text(f"Edit Alat: {nama_alat_lama}")
            dialog_edit.on_dismiss = (
                lambda _: setattr(dialog_edit, "open", False) or page.update()
            )
            kolom_kiri_edit = ft.Column(
                [
                    input_nama,
                    input_rfid,
                    dd_kondisi_edit
                ],
                width=250,
                height=300,
            )
            kolom_edit_kanan = ft.Column(
                [
                    ft.ElevatedButton( 
                        "Pilih Gambar dari Perangkat",
                        bgcolor="#E3F2FD",
                        color="blue",
                        on_click=buka_browser_manual,
                    ),
                    preview_img,
                ],
                width=300,
                height=230,
                horizontal_alignment="center",
                spacing=15,
            )

            dialog_edit.content = ft.Row(
                [kolom_kiri_edit, kolom_edit_kanan],
                width=600,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )

            dialog_edit.actions = [
                ft.TextButton("Batal", on_click=batal_edit),
                ft.ElevatedButton(
                    "Simpan Perubahan",
                    bgcolor="blue",
                    color="white",
                    on_click=eksekusi_simpan,
                ),
            ]
            dialog_edit.open = True
            page.update()

        # ---- Sub-fungsi: hapus alat dari database ----
        def hapus_alat_db(rfid_target, nama_alat):
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    conn.cursor().execute(
                        "DELETE FROM tools WHERE rfid_tag_uid = ?", (rfid_target,)
                    )
                    conn.commit()

                # ---- Fungsi Sinkronisasi API NICO (HAPUS)----
                def kirim_api_hapus():
                    try: 
                        ip_server = settings.get("db_host", "127.0.0.1:8000")
                        url_hapus = f"http://{ip_server}/api/v1/hapus-alat/{nama_alat}"
                        requests.delete(url_hapus, timeout=10)
                        print(f"Sukses hapus API: {nama_alat}")
                    except Exception as e: 
                        print(f"gagal menghapus api:{e}")
                threading.Thread(target=kirim_api_hapus, daemon=True).start()

            except Exception:
                pass

        def konfirmasi_hapus(nama_alat, rfid_target):
            def tutup_dialog(e):
                dialog_hapus.open = False
                page.update()

            def jalankan_hapus(e):
                dialog_hapus.open = False
                page.update()
                hapus_alat_db(rfid_target, nama_alat)
                page.run_task(tunda_lalu_refresh)

            dialog_hapus.title = ft.Text(
                "Konfirmasi Otorisasi", weight="bold", color="black"
            )
            dialog_hapus.content = ft.Text(
                f"Apakah anda yakin ingin menghapus'{nama_alat}' dari sistem ?",
                color="black",
            )

            dialog_hapus.actions = [
                ft.ElevatedButton(
                    "Cancel", on_click=tutup_dialog, style=ft.ButtonStyle(color="grey")
                ),
                ft.ElevatedButton(
                    "Delete", on_click=jalankan_hapus, bgcolor="red", color="white"
                ),
            ]
            dialog_hapus.open = True
            page.update()

        # ---- Buat daftar alat dengan scroll ----
        list_ui = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

        def muat_daftar_alat(kata_kunci="", laci="1"):
            list_ui.controls.clear() 
            try:
                with sqlite3.connect("smartdrawer.db") as conn:
                    cursor = conn.cursor()
                    if kata_kunci:
                        cursor.execute(
                            "SELECT name, mqtt_topic, rfid_tag_uid, img, kondisi FROM tools WHERE name LIKE ? AND page = ? ORDER BY mqtt_topic ASC",
                            (f"%{kata_kunci}%", laci)
                        )
                    else:
                        cursor.execute(
                            "SELECT name, mqtt_topic, rfid_tag_uid, img, kondisi FROM tools WHERE page =? ORDER BY mqtt_topic ASC",
                            (laci,)
                        )
                    semua_alat = cursor.fetchall()
            except Exception:
                semua_alat = []

            for baris in semua_alat:
                nama_alat, topik, rfid_alat, gambar_alat, kondisi_alat = (
                    baris[0],
                    baris[1],
                    baris[2],
                    baris[3],
                    baris[4],
                )
                kotak_alat = ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Text("⚙️", size=16),
                                bgcolor=BLUE_SENSOR,
                                padding=10,
                                border_radius=8,
                            ),
                            ft.Text(
                                nama_alat,
                                size=16,
                                weight="bold",
                                color=TEXT_COLOR,
                                expand=True,
                            ),
                            ft.Text(topik, color="grey", size=14),
                            ft.Container(
                                content=ft.Text(
                                    "✏️ Edit", size=14, color="blue", weight="bold"
                                ),
                                padding=10,
                                on_click=lambda _, n=nama_alat, r=rfid_alat, g=gambar_alat, k=kondisi_alat: buka_dialog_edit(
                                    n, r, g, k
                                ),
                                ink=True,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    "🗑️ Delete", size=14, color="red", weight="bold"
                                ),
                                padding=10,
                                on_click=lambda _, n=nama_alat, r=rfid_alat: konfirmasi_hapus(n, r),
                                ink=True,
                            ),
                        ],
                        alignment="center",
                    ),
                    bgcolor="#F9FAFB",
                    padding=10,
                    border_radius=10,
                    border=ft.border.all(1, "#E5E7EB"),
                    width=600,
                )
                list_ui.controls.append(kotak_alat)
            page.update()
        
        tombol_laci = ft.SegmentedButton(
            on_change=lambda e: muat_daftar_alat(input_search.value, list(e.control.selected)[0]),
            selected_icon=ft.Icon(ft.Icons.CHECK_SHARP, size=16),
            selected=["1"], #untuk default langsung ke laci 1
            allow_multiple_selection=False,
            segments=[
                ft.Segment(value="1", label=ft.Text("Drawer 1", weight="bold")),
                ft.Segment(value="2", label=ft.Text("Drawer 2", weight="bold")),
                ft.Segment(value="3", label=ft.Text("Drawer 3", weight="bold")),
                ft.Segment(value="4", label=ft.Text("Drawer 4", weight="bold"))
            ]
        )

        input_search = ft.TextField(
            hint_text="Search Tool Here",
            width=600,
            border_color="blue",
            border_radius=10,
            color="black",
            on_change=lambda e: muat_daftar_alat(e.control.value, list(tombol_laci.selected)[0])
        )

        muat_daftar_alat(laci="1")

        main_card = ft.Container(
            content=ft.Column(
                [
                    input_search,
                    tombol_laci, 
                    ft.Container(content=list_ui, height=250),
                ],
                horizontal_alignment="center",
                spacing=15  
            ),
            width=700,
            bgcolor="white",
            padding=30,
            border_radius=20,
            shadow=ft.BoxShadow(blur_radius=20, color=SHADOW_COLOR),
            margin=ft.margin.only(top=20)
        )

        tampilan = build_standard_layout(
            title_text="List Tool on the System",
            content_control=ft.Column(
                [main_card],
                horizontal_alignment="center",
                alignment="center",
                margin=ft.margin.only(top=-100),
            ),
            back_func=show_edit_tools_menu,
        )
        page.add(tampilan)

    # ------------------------------------------------------------------
    # SHOW HISTORY PAGE
    # ------------------------------------------------------------------
    def show_history_page(e=None):
        page.clean()
        try:
            with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(row[0]), color="black", weight="bold", size=15)),
                            ft.DataCell(
                                ft.Text(str(row[1]), weight="bold", color="black", size=15)
                            ),
                            ft.DataCell(
                                ft.Text(
                                    str(row[2]) if len(row) > 2 and row[2] else "-",
                                    color="black",
                                )
                            ),
                            ft.DataCell(
                                ft.Container(
                                    content=ft.Text(
                                        str(row[3]).upper(),
                                        color="white",
                                        weight="bold",
                                        size=12,
                                    ),
                                    bgcolor=(
                                        "#EF4444"
                                        if str(row[3]).upper() == "PINJAM"
                                        else "#10B981"
                                    ),
                                    padding=ft.padding.symmetric(
                                        horizontal=12, vertical=6
                                    ),
                                    border_radius=15,
                                    alignment=ft.Alignment(0, 0),
                                )
                            ),
                        ]
                    )
                    for row in conn.cursor()
                    .execute(
                        "SELECT nama_user, nama_alat, waktu, status FROM log_peminjaman ORDER BY id DESC LIMIT 15"
                    )
                    .fetchall()
                ]
            table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("User", weight="bold", color="black", size=20)),
                    ft.DataColumn(ft.Text("Alat", weight="bold", color="black", size=20)),
                    ft.DataColumn(ft.Text("Waktu", weight="bold", color="black", size=20)),
                    ft.DataColumn(ft.Text("Status", weight="bold", color="black", size=20)),
                ],
                rows=rows,
                border=ft.border.all(1, "#E5E7EB"),
                border_radius=10,
                heading_row_color="#F3F4F6",
                vertical_lines=ft.border.BorderSide(1, "#F3F4F6"),
                horizontal_lines=ft.border.BorderSide(1, "#F3F4F6"),
                column_spacing=100,
            )
            page.add(
                build_standard_layout(
                    title_text="HISTORY",
                    content_control=ft.Column(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [table],
                                    scroll=ft.ScrollMode.ALWAYS,
                                    height=350,
                                    width=850,
                                    horizontal_alignment="center",
                                ),
                                bgcolor="white",
                                padding=20,
                                border_radius=15,
                                shadow=ft.BoxShadow(blur_radius=20, color=SHADOW_COLOR),
                            )
                        ],
                        horizontal_alignment="center",
                        alignment="center",
                        margin=ft.margin.only(top=-100),
                    ),
                    back_func=show_admin_dashboard,
                )
            )
        except Exception as e:
            print("Ada error di Database Riwayat:", e)

    # ------------------------------------------------------------------
    # SHOW ADD TOOL PAGE
    # ------------------------------------------------------------------
    def show_add_tool_page(e=None):
        page.clean()

        # State
        path_gambar_baru = ["tambah.png"]
        current_path = [os.path.expanduser("~")]

        # Preview Gambar
        preview_img = ft.Container(
            content=ft.Image(
                src=f"/{path_gambar_baru[0]}", width=220, height=220, fit="contain"
            ),
            width=220,
            height=220,
        )

        # Dialog file browser
        dialog_tambah_browser = ft.AlertDialog(
            title=ft.Text("Pilih Gambar", weight="bold", color="black"), bgcolor="white"
        )

        file_list_view = ft.ListView(height=300, spacing=5)
        path_text = ft.Text(
            current_path[0], weight="bold", size=14, color="blue", expand=True
        )

        def navigate_browser(new_path):
            current_path[0] = new_path
            update_browser_ui()

        if os.name == "nt":
            tombol_drive = ft.Row(
                [
                    path_text,
                    ft.ElevatedButton(
                        "💻 Drive C:",
                        bgcolor=BG_COLOR,
                        color=TEXT_COLOR,
                        on_click=lambda _: navigate_browser("c:\\"),
                    ),
                    ft.ElevatedButton(
                        "💻 Drive D:",
                        bgcolor=BG_COLOR,
                        color=TEXT_COLOR,
                        on_click=lambda _: navigate_browser("D:\\"),
                    ),
                ]
            )
        else:
            tombol_drive = ft.Row(
                [
                    path_text,
                    ft.ElevatedButton(
                        "🏠 Root (/)",
                        icon="folder",
                        bgcolor=BG_COLOR,
                        color=TEXT_COLOR,
                        on_click=lambda _: navigate_browser("/"),
                    ),
                    ft.ElevatedButton(
                        "🔌 USB/Media",
                        icon="usb",
                        bgcolor=BG_COLOR,
                        color=TEXT_COLOR,
                        on_click=lambda _: navigate_browser("/media"),
                    ),
                ]
            )

        def update_browser_ui():
            file_list_view.controls.clear()
            path_text.value = f"Lokasi: {current_path[0]}"

            parent_dir = os.path.dirname(current_path[0])
            if parent_dir != current_path[0]:
                file_list_view.controls.append(
                    ft.TextButton(
                        "⬆️.. (Kembali)",
                        icon_color="#3B82F6",
                        style=ft.ButtonStyle(
                            color="black", alignment=ft.Alignment(-1, 0)
                        ),
                        width=580,
                        on_click=lambda _, p=parent_dir: navigate_browser(p),
                    )
                )
            try:
                items = os.listdir(current_path[0])
                dirs, files = [], []
                for item in items:
                    full_path = os.path.join(current_path[0], item)
                    if os.path.isdir(full_path):
                        dirs.append(item)
                    elif item.lower().endswith((".png", ".jpg", ".jpeg")):
                        files.append(item)
                dirs.sort()
                files.sort()

                for d in dirs:
                    file_list_view.controls.append(
                        ft.TextButton(
                            f"📁{d}",
                            style=ft.ButtonStyle(
                                color="black", alignment=ft.Alignment(-1, 0)
                            ),
                            width=580,
                            on_click=lambda _, p=os.path.join(
                                current_path[0], d
                            ): navigate_browser(p),
                        )
                    )
                for f in files:
                    full_path = os.path.join(current_path[0], f)

                    try: 
                        thumb=ft.Image(
                            src=full_path, width=35, height=35, fit="contain"
                        )
                    except Exception:
                        thumb = ft.Icon(ft.icons.BUILD, color="#10B981")

                    file_list_view.controls.append(
                        ft.Row(
                            [
                                thumb,
                                ft.TextButton(
                                    f,
                                    style=ft.ButtonStyle(
                                        color="black", alignment=ft.Alignment(-1, 0)
                                    ),
                                    width=530,
                                    on_click=lambda _, p=full_path: pilih_gambar(p),
                                ),
                            ],
                            alignment="start",
                            vertical_alignment="center",
                            height=45,
                        )
                    )
            except Exception as err:
                file_list_view.controls.append(
                    ft.Text(f"Akses ditolak: {err}", color="red")
                )
            page.update()

        def pilih_gambar(filepath):
            path_gambar_baru[0] = filepath
            try:
                preview_img.content = ft.Image(
                    src=filepath, width=220, height=220, fit="contain"
                )
                dialog_tambah_browser.open = False
                page.update()
            except Exception:
                pass

        dialog_tambah_browser.content = ft.Column(
            [tombol_drive, ft.Divider(), file_list_view], width=600, tight=True
        )
        dialog_tambah_browser.actions = [
            ft.TextButton(
                "Batal & Tutup",
                style=ft.ButtonStyle(color="black"),
                on_click=lambda _: tutup_browser_tambah(),
            )
        ]

        def buka_browser_tambah(e):
            update_browser_ui()
            dialog_tambah_browser.open = True
            page.update()

        def tutup_browser_tambah():
            dialog_tambah_browser.open = False
            page.update()

        # Input Fields
        input_nama = ft.TextField(
            label="Nama Alat",
            width=350,
            border_color=BLUE_SENSOR,
            border_radius=10,
            color=TEXT_COLOR,
        )
        input_rfid = ft.TextField(
            label="UID Tag RFID",
            width=210,
            border_color=BLUE_SENSOR,
            border_radius=10,
            read_only=True,
            color=TEXT_COLOR,
        )
        
        # 1. Pancingan Awal Laci 1
        from config import DRAWER_CAPACITY
        default_slot = DRAWER_CAPACITY.get(1, 16)

        # 2. Buat Dropdown PIN
        dd_pin = ft.Dropdown(
            label="Posisi Pin Sensor (mqtt_topic)",
            width=350,
            border_color=BLUE_SENSOR,
            border_radius=10,
            color=TEXT_COLOR,
            options=[ft.dropdown.Option(key=f"P{str(i).zfill(2)}", text=f"P{str(i).zfill(2)}") for i in range(1, default_slot + 1)],
        )

        # 3. Fungsi Pemikir (Kembali menggunakan .value dan .clear)
        def update_pin_options(e):
            if not dd_laci.value:
                return
                
            laci_terpilih = int(dd_laci.value)
            jumlah_slot = DRAWER_CAPACITY.get(laci_terpilih, 16)

            pin_terpakai = []
            try: 
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn: 
                    cursor = conn.cursor()
                    cursor.execute("SELECT mqtt_topic FROM tools WHERE page =?", (laci_terpilih,))
                    hasil = cursor.fetchall()
                    #hasilnya berupa list of tuples yang akan mengambil list posisi 
                    pin_terpakai = [str(baris[0]).strip() for baris in hasil if baris [0]]
            
            except Exception as err: 
                print(f"Position: {err} is not availaible")

            # Bersihkan dengan aman
            dd_pin.options.clear()
            
            # Isi ulang
            for i in range(1, jumlah_slot + 1):
                kode = f"P{str(i).zfill(2)}"
                if kode not in pin_terpakai:
                    dd_pin.options.append(ft.dropdown.Option(key=kode, text=kode))
            if len(dd_pin.options) == 0:
                dd_pin.options.append(ft.dropdown.Option(key="", text="Position is not available", disabled=True))

            dd_pin.value = None
            page.update()

        # 4. KEMBALI MENGGUNAKAN DROPDOWN LACI
        dd_laci = ft.Dropdown(
            label="Lokasi Laci (page)",
            width=350,
            border_color=BLUE_SENSOR,
            border_radius=10,
            color=TEXT_COLOR,
            value="1", # Set default ke Laci 1 agar nyambung dengan pancingan
            options=[
                ft.dropdown.Option(key="1", text="Laci 1"),
                ft.dropdown.Option(key="2", text="Laci 2"),
                ft.dropdown.Option(key="3", text="Laci 3"),
                ft.dropdown.Option(key="4", text="Laci 4"),
            ],
            on_select=update_pin_options,
        )
        update_pin_options(None)
        notif_text = ft.Text("", color="red", size=14, weight="bold")

        # Pop up scan RFID
        input_popup_scan = ft.TextField(
            label="Tempelkan Tag RFID...",
            width=300,
            border_color=BLUE_SENSOR,
            color="black",
            autofocus=True,
        )

        def proses_popup_scan(e):
            uid = str(input_popup_scan.value).strip()
            if uid:
                input_rfid.value = uid
                input_rfid.border_color = "#10B981"
                dialog_scan.open = False
                page.update()

        input_popup_scan.on_submit = proses_popup_scan

        dialog_scan = ft.AlertDialog(
            title=ft.Text("Scan Tag RFID", weight="bold", color="white"),
            content=ft.Column(
                [
                    ft.Text(
                        "Kursor sudah otomatis aktif dibawah ini. \nSilakan scan tag atau ketik manual lalu Enter",
                        color="grey",
                    ),
                    ft.Container(height=10),
                    input_popup_scan,
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton(
                    "Cancel",
                    style=ft.ButtonStyle(color="red"),
                    on_click=lambda _: tutup_dialog_scan(),
                )
            ],
        )

        page.overlay.append(dialog_scan)

        def tutup_dialog_scan():
            dialog_scan.open = False
            page.update()

        def mulai_scan_rfid(e):
            import threading

            input_popup_scan.value = ""
            dialog_scan.open = True
            page.update()
            threading.Thread(
                target=lambda: [time.sleep(0.5), input_rfid.focus(), page.update()]
            ).start()

        def proses_rfid(e):
            uid = str(e.control.value).strip()
            if uid:
                input_rfid.border_color = "#10B981"
                page.update()

        input_rfid.on_submit = proses_rfid

        def simpan_alat_baru(e):
            bunyikan_buzzer_error(0.5) #Bunyi buzzer error sebagai pancingan untuk segera meletakkan alat di sensor, bisa disesuaikan durasinya
            if not input_nama.value.strip():
                notif_text.value = "❌ Nama alat tidak boleh kosong!"
                page.update()
                return
            if not input_rfid.value.strip():
                notif_text.value = "❌ Harap scan Tag RFID terlebih dahulu!"
                page.update()
                return
            if  path_gambar_baru[0] == "tambah.png":
                notif_text.value = "❌ Pilih gambar alat!"
                page.update()
                return
            if not dd_laci.value:
                notif_text.value = "❌ Pilih lokasi laci!"
                page.update()
                return
            if not dd_pin.value:
                notif_text.value = "❌ Pilih posisi pin sensor!"
                page.update()
                return
            if not dd_kondisi.value: 
                notif_text.value = "❌ Choose Condition of the Tool!"
                page.update()
                return
            
            uid_tag = input_rfid.value.strip()
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    cursor = conn.cursor()
                    res = cursor.execute("SELECT name FROM tools WHERE rfid_tag_uid = ?", (uid_tag,)).fetchone()
                    if res:
                        notif_text.value = f"❌ Tag RFID sudah terdaftar untuk alat '{res[0]}'!"
                        notif_text.color = "red"
                        page.update()
                        return # 🔥 Stop eksekusi! Laci batal dibuka.
            except Exception as ex:
                print(f"Error cek duplikat RFID: {ex}")

            teks_laci_tambah = ft.Text(f"Drawer {dd_laci.value} Open", weight="bold", color="blue", size=18)
            teks_posisi_tambah = ft.Text(f"Please place the Tool in Position {dd_pin.value}")
            
            dialog_tunggu_sensor = ft.AlertDialog(
                modal=True,
                title=ft.Text("Waiting for Sensor....", weight="bold", color="black"),
                content=ft.Column(
                    [
                        ft.ProgressRing(),
                        ft.Container(height=10),
                        teks_laci_tambah,
                        teks_posisi_tambah,
                        ft.Text("System will save automatically when the tool is placed", color="grey", size=12, text_align="center")
                    ],
                    tight=True,
                    horizontal_alignment="center"
                )
            )

            page.overlay.append(dialog_tunggu_sensor)
            dialog_tunggu_sensor.open = True
            page.update()

            async def pantau_sensor_tambah():
                laci_terpilih = int(dd_laci.value)
                pin_terpilih = dd_pin.value
                kunci_unik = f"{laci_terpilih}_{pin_terpilih}"

                # 🔥 TITIP PESAN KE SENSOR MANAGER
                target_expected["laci"] = laci_terpilih
                target_expected["pin"] = pin_terpilih
                target_expected["action"] = "TARUH"

                buka_laci_otomatis(laci_terpilih)

                waktu_tunggu = 0 
                max_waktu = 15 

                while status_sensor_realtime.get(kunci_unik, 0) == 0:
                    if target_expected.get("lockdown"):
                        teks_laci_tambah.color = "red"
                        teks_posisi_tambah.value = f"Wrong position! Please pick up the tool from {target_expected.get('wrong_pin')}!"
                        teks_posisi_tambah.color = "red"
                        teks_posisi_tambah.weight = "bold"
                        page.update()
                        await asyncio.sleep(1)
                        continue
                    else:
                        teks_laci_tambah.color = "blue"
                        teks_posisi_tambah.value = f"Please place the Tool in Position {pin_terpilih}"
                        teks_posisi_tambah.color = TEXT_COLOR
                        teks_posisi_tambah.weight = "normal"
                        page.update()

                    await asyncio.sleep(1)
                    waktu_tunggu += 1 
                    if waktu_tunggu >= max_waktu:
                        break 
                
                # 🔥 RESET PESAN SETELAH SELESAI/TIMEOUT
                target_expected["laci"] = None
                target_expected["pin"] = None
                target_expected["action"] = None
                target_expected["lockdown"] =False
                target_expected["wrong_pin"] = None
                buzzer_off()

                #jika sukses mendeteksi 1 maka akan menyimpan ke database 
                if status_sensor_realtime.get(kunci_unik, 0) == 1:
                    try:
                        filepath_asli = path_gambar_baru[0]
                        nama_asli = os.path.basename(filepath_asli)
                        nama_final = nama_asli

                        if os.path.isabs(filepath_asli):
                            lokasi_simpan = os.path.join("assets", nama_asli)
                            
                            # Jika dari luar folder assets
                            if os.path.abspath(filepath_asli) != os.path.abspath(lokasi_simpan):
                                
                                #DETEKTOR TABRAKAN NAMA
                                if os.path.exists(lokasi_simpan):
                                    nama_file, ext = os.path.splitext(nama_asli)
                                    counter = 1
                                    # Looping cari nama yang belum dipakai
                                    while os.path.exists(os.path.join("assets", f"{nama_file}_{counter}{ext}")):
                                        counter += 1
                                    nama_final = f"{nama_file}_{counter}{ext}"
                                    lokasi_simpan = os.path.join("assets", nama_final)
                                
                                shutil.copy(filepath_asli, lokasi_simpan)

                        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                            conn.execute(
                                "INSERT INTO tools (name, rfid_tag_uid, img, total, page, mqtt_topic, rot, kondisi) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (
                                    input_nama.value.strip(),
                                    input_rfid.value.strip(),
                                    nama_final,
                                    1,
                                    laci_terpilih,
                                    pin_terpilih,
                                    0,
                                    dd_kondisi.value
                                ),
                            )
                            conn.commit()
                            # --- TAMBAHAN SINKRONISASI API NICO (TAMBAH ALAT) ---
                        def kirim_api_tambah():
                            try:
                                with open(lokasi_simpan, "rb") as f:
                                    gambar_b64 = base64.b64encode(f.read()).decode("utf-8")
                                
                                ip_server = settings.get("db_host", "127.0.0.1:8000")
                                url_tambah = f"http://{ip_server}/api/v1/tambah-alat"
                                
                                nama_input = input_nama.value.strip()
                                payload = {
                                    "kode_alat": nama_input,
                                    "nama_alat": nama_input,
                                    "stok": 1,
                                    "gambar_base64": gambar_b64,
                                    "kondisi": dd_kondisi.value,
                                    "uid_tag_rfid": input_rfid.value.strip(),
                                    "mqtt_topic": dd_pin.value,
                                    "laci_id": dd_laci.value
                                }
                                
                                print(f"Isi Payload = {payload}")
                                # Tembak API dan simpan jawabannya di variabel 'response'
                                response = requests.post(
                                    url_tambah, 
                                    json=payload, 
                                    headers={"Accept": "application/json"}, 
                                    timeout=10
                                )
                                
                                # Cek apakah Laravel membalas dengan status sukses (200 atau 201)
                                if response.status_code in [200, 201]:
                                    print(f"✅ Sukses Tambah API: {nama_input}")
                                else:
                                    # Jika Laravel error (misal 500), tampilkan pesannya!
                                    print(f"❌ API Menolak! Status: {response.status_code} | Jawaban: {response.text}")
                                    
                            except Exception as e:
                                print(f"❌ Gagal Terkoneksi (Server Mati/Jaringan Terputus): {e}")
                        
                        threading.Thread(target=kirim_api_tambah, daemon=True).start()
                        # ----------------------------------------------------
                        dialog_tunggu_sensor.open = False

                        notif_text.value = "✅ Alat berhasil ditambahkan!"
                        notif_text.color = "#10B981"
                        page.update()

                        await asyncio.sleep(1.0)
                        show_add_tool_page()

                    except sqlite3.IntegrityError:
                        dialog_tunggu_sensor.open = False
                        notif_text.value = "❌ RFID Tag already in use!"
                        notif_text.color = "red"
                        page.update()
                    except Exception as err:
                        notif_text.value = f"❌ Failed to Save: {err}"
                        notif_text.color = "red"
                        page.update()
                else: 
                    dialog_tunggu_sensor.open = False
                    notif_text.value = "Time out, tool not detected by sensor"
                    notif_text.color = "red"
                    page.update()
            page.run_task(pantau_sensor_tambah)

        #Penambahan untuk memilih kondisi alat pada tambah alat 
        dd_kondisi = ft.Dropdown(
            label="Tool Condition",
            width=350,
            border_color=BLUE_SENSOR,
            border_radius=10,
            color=TEXT_COLOR,
            options=[
                ft.dropdown.Option(key="baik", text="Baik"),
                ft.dropdown.Option(key="kurang baik", text="Kurang Baik"),
                ft.dropdown.Option(key="rusak", text="Rusak")
            ],
        )

        # Layout form
        kolom_kiri = ft.Column(
            [
                input_nama,
                dd_kondisi,
                dd_laci,
                dd_pin,
                ft.Row(
                    [
                        input_rfid,
                        ft.ElevatedButton(
                            "Scan Tag 💳",
                            style=ft.ButtonStyle(bgcolor="#E3F2FD", color=BLUE_SENSOR),
                            on_click=mulai_scan_rfid,
                        ),
                    ],
                    spacing=10,
                ),
            ],
            spacing=10,
        )

        kolom_kanan = ft.Column(
            [
                ft.Column(
                    [
                        preview_img,
                        ft.ElevatedButton(
                            "📁 Pilih Gambar",
                            icon="folder_open",
                            bgcolor="#E3F2FD",
                            color="blue",
                            on_click=buka_browser_tambah,
                            width=220, 
                        ),
                    ],
                    width=300, 
                    horizontal_alignment="center",
                    spacing=15,
                ),
            ],
            spacing=15,
        )

        form_card = build_standard_layout(
            title_text="ADD NEW TOOLS",
            content_control=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [kolom_kiri, kolom_kanan],
                            vertical_alignment="start",
                            width=700,
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Container(height=5),
                        notif_text,
                        create_filled_button(
                            "Simpan Data Alat",
                            GREEN_SENSOR,
                            simpan_alat_baru,
                            width=700,
                            height=45,
                        ),
                    ],
                    horizontal_alignment="center",
                    spacing=10,
                ),
                width=750,
                height=450,
                bgcolor="white",
                padding=ft.padding.only(left=25, right=25, top=50, bottom=25),
                border_radius=20,
                shadow=ft.BoxShadow(blur_radius=20, color=SHADOW_COLOR),
                margin=ft.margin.only(top=-60)
            ),
        )
        page.overlay.append(dialog_tambah_browser)
        page.add(
            build_standard_layout(
                ft.Column(
                    [form_card],
                    horizontal_alignment="center",
                    alignment="center",
                    margin=ft.margin.only(top=-100),
                ),
                back_func=show_edit_tools_menu,
            )
        )

    # ------------------------------------------------------------------
    # SHOW SYNC WEB PAGE (Antrean Sinkronisasi Alat Pending)
    # ------------------------------------------------------------------
    def show_sync_web_page(e=None):
        page.clean()
        page.overlay.clear()

        list_ui = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        notif_text = ft.Text("", color="red", size=14, weight="bold")
        
        # Komponen Pop-up Scan
        input_popup_scan = ft.TextField(label="Tempelkan Tag RFID...", autofocus=True)
        dialog_scan = ft.AlertDialog(
            title=ft.Text("Scan Tag RFID Baru", weight="bold", color="black"),
            content=ft.Column([ft.Text("Scan tag untuk alat ini:"), input_popup_scan, notif_text], tight=True),
        )
        
        # Komponen Pop-up Sensor
        teks_laci_tambah = ft.Text("", weight="bold", color="blue", size=18)
        teks_posisi_tambah = ft.Text("")
        dialog_tunggu_sensor = ft.AlertDialog(
            modal=True,
            title=ft.Text("Menunggu Sensor....", weight="bold", color="black"),
            content=ft.Column([ft.ProgressRing(), ft.Container(height=10), teks_laci_tambah, teks_posisi_tambah], tight=True, horizontal_alignment="center")
        )
        page.overlay.extend([dialog_scan, dialog_tunggu_sensor])

        # --- Fungsi Utama Menarik Data Web ---
        def muat_antrean_pending():
            list_ui.controls.clear()
            try:
                ip_server = settings.get("db_host", "127.0.0.1:8000")
                response = requests.get(f"http://{ip_server}/api/v1/alat-pending", timeout=10)
                alat_pending = response.json() if response.status_code == 200 else []
                
                if not alat_pending:
                    list_ui.controls.append(ft.Container(content=ft.Text("✅ Tidak ada antrean alat pending dari Web!", color="green", weight="bold"), padding=20))
                    page.update()
                    return
                
                alat_siap_masuk = [
                    alat for alat in alat_pending 
                    if alat.get('laci_id') and alat.get('mqtt_topic') is not None 
                ]

                if not alat_siap_masuk:
                    list_ui.controls.append(ft.Container(
                        content=ft.Text("Alat pending di web, laci/pin belum diatur!", color="orange", weight="bold"),
                        padding=20
                    ))

                # Sortir laci dari terkecil
                alat_pending.sort(key=lambda x: (int(x['laci_id']), x['mqtt_topic']))
                laci_terkecil_aktif = min([int(alat['laci_id']) for alat in alat_pending])

                for alat in alat_pending:
                    laci_alat = int(alat['laci_id'])
                    bisa_diproses = (laci_alat == laci_terkecil_aktif)
                    
                    kotak = ft.Container(
                        content=ft.Row([
                            ft.Container(content=ft.Text(f"Laci {laci_alat}", weight="bold"), width=60),
                            ft.Text(alat['mqtt_topic'], color="grey", width=50),
                            ft.Text(alat['kode_alat'], weight="bold", expand=True),
                            ft.ElevatedButton(
                                "Scan & Masukkan", 
                                bgcolor=BLUE_SENSOR if bisa_diproses else "grey",
                                color="white", disabled=not bisa_diproses,
                                on_click=lambda e, a=alat: mulai_scan_rfid(a)
                            )
                        ]),
                        padding=10, border=ft.border.all(1, "#E5E7EB"), border_radius=10,
                        bgcolor="white" if bisa_diproses else "#F3F4F6"
                    )
                    list_ui.controls.append(kotak)
            except Exception as e:
                list_ui.controls.append(ft.Text(f"Gagal koneksi ke server: {e}", color="red"))
            page.update()

        # --- Proses 1: Buka Pop-up Scan ---
        alat_terpilih = {}
        def mulai_scan_rfid(alat):
            alat_terpilih.clear()
            alat_terpilih.update(alat)
            input_popup_scan.value = ""
            notif_text.value = ""
            dialog_scan.open = True
            page.update()
            threading.Thread(target=lambda: [time.sleep(0.5), input_popup_scan.focus(), page.update()]).start()

        # --- Proses 2: RFID Ditangkap, Lanjut ke Sensor ---
        def proses_rfid_submit(e):
            uid = str(input_popup_scan.value).strip()
            if not uid: return
            
            # Cek duplikat RFID di SQLite
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    if conn.cursor().execute("SELECT name FROM tools WHERE rfid_tag_uid = ?", (uid,)).fetchone():
                        notif_text.value = "❌ Tag RFID ini sudah dipakai alat lain!"
                        page.update()
                        return
            except Exception: pass
            
            dialog_scan.open = False
            laci_target = int(alat_terpilih['laci_id'])
            pin_target = alat_terpilih['mqtt_topic']
            
            teks_laci_tambah.value = f"Laci {laci_target} Terbuka"
            teks_posisi_tambah.value = f"Taruh {alat_terpilih['kode_alat']} di Pin {pin_target}"
            dialog_tunggu_sensor.open = True
            page.update()
            
            page.run_task(pantau_sensor, laci_target, pin_target, uid)
            
        input_popup_scan.on_submit = proses_rfid_submit

        # --- Proses 3: Sensor IR & Simpan Data ---
        async def pantau_sensor(laci_target, pin_target, uid_tag):
            kunci_unik = f"{laci_target}_{pin_target}"
            target_expected["laci"] = laci_target
            target_expected["pin"] = pin_target
            target_expected["action"] = "TARUH"
            buka_laci_otomatis(laci_target)
            bunyikan_buzzer_error(1.0)
            
            waktu_tunggu = 0
            while status_sensor_realtime.get(kunci_unik, 0) == 0:
                if target_expected.get("lockdown"):
                    teks_laci_tambah.color = "red"
                    teks_posisi_tambah.value = "❌ Salah posisi pin!"
                else:
                    teks_laci_tambah.color = "blue"
                    teks_posisi_tambah.value = f"Taruh {alat_terpilih['kode_alat']} di Pin {pin_target}"
                page.update()
                await asyncio.sleep(1)
                waktu_tunggu += 1
                if waktu_tunggu >= 15: break
                
            # Reset target sensor
            target_expected.update({"laci": None, "pin": None, "action": None, "lockdown": False, "wrong_pin": None})
            buzzer_off()
            
            # Jika fisik terdeteksi masuk
            if status_sensor_realtime.get(kunci_unik, 0) == 1:
                try:
                    # 1. Simpan ke SQLite lokal
                    with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                        conn.execute(
                            "INSERT INTO tools (name, rfid_tag_uid, img, total, page, mqtt_topic, rot, kondisi) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (alat_terpilih['kode_alat'], uid_tag, alat_terpilih['foto'], 1, laci_target, pin_target, 0, alat_terpilih['kondisi'])
                        )
                        conn.commit()
                        
                    # 2. Kirim konfirmasi ke API Nico
                    def kirim_konfirmasi():
                        try:
                            ip_server = settings.get("db_host", "127.0.0.1:8000")
                            url = f"http://{ip_server}/api/v1/konfirmasi-pending/{alat_terpilih['kode_alat']}"
                            requests.post(url, json={"uid_tag_rfid": uid_tag}, timeout=10)
                        except Exception: pass
                    threading.Thread(target=kirim_konfirmasi, daemon=True).start()
                    
                    dialog_tunggu_sensor.open = False
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Alat sukses disinkronkan!"), bgcolor="green", open=True)
                    page.update()
                    await asyncio.sleep(1)
                    muat_antrean_pending() # Refresh ulang antrean
                except Exception as e:
                    dialog_tunggu_sensor.open = False
                    print(f"Error Database: {e}")
            else:
                dialog_tunggu_sensor.open = False
                page.snack_bar = ft.SnackBar(ft.Text("❌ Timeout: Sensor tidak mendeteksi alat."), bgcolor="red", open=True)
                page.update()

        muat_antrean_pending()

        main_card = ft.Container(
            content=ft.Column([ft.Text("Antrean Alat dari Website", size=24, weight="bold"), list_ui], horizontal_alignment="center", spacing=15),
            width=700, bgcolor="white", padding=30, border_radius=20, shadow=ft.BoxShadow(blur_radius=20, color=SHADOW_COLOR), margin=ft.margin.only(top=20)
        )

        page.add(build_standard_layout(title_text="SYNC WEB", content_control=main_card, back_func=show_edit_tools_menu))
    # ------------------------------------------------------------------
    # SHOW ADMIN DASHBOARD
    # ------------------------------------------------------------------
    def show_admin_dashboard(e=None):
        page.clean()
        page.add(
            build_standard_layout(
                title_text="Admin Dashboard",
                content_control=ft.Column(
                    [
                        ft.Container(height=15),
                        ft.Row(
                            [
                                create_menu_card(
                                    "Cek History",
                                    "Riwayat",
                                    "history.png",
                                    "#F3E5F5",
                                    lambda _: show_history_page(),
                                ),
                                create_menu_card(
                                    "Edit Tools",
                                    "Stok",
                                    "build.png",
                                    "#FFF3E0",
                                    lambda _: show_edit_tools_menu(),
                                ),
                            ],
                            alignment="center",
                            spacing=30,
                        ),
                    ],
                    horizontal_alignment="center",
                    alignment="center",
                    margin=ft.margin.only(top=-100),
                ),
                action_button=ft.PopupMenuButton(
                    icon=ft.Icons.LOGOUT_OUTLINED,
                    icon_size=50,
                    icon_color="red",
                    items=[
                        ft.PopupMenuItem(
                            content=ft.Text("Logout", color="red"),
                            on_click=lambda _: nav["show_home"](),
                        )
                    ],
                ),
            )
        )

    # ------------------------------------------------------------------
    # SHOW LOGIN ADMIN
    # ------------------------------------------------------------------
    def show_login_admin(
        e=None,
        tujuan=None,
        teks_judul="Admin Login",
        teks_button="LOGIN",
        button_color="#1F2937",
        teks_size=20,
    ):
        page.clean()

        if tujuan is None:
            tujuan = show_admin_dashboard

        username_field = ft.TextField(
            width=340,
            text_size=20,
            hint_text="Masukkan username",
            color="black",
            filled=True,
            bgcolor="#F3F4F6",
            border_radius=8,
            content_padding=15,
            border_color="transparent",
            autofocus=True,
        )
        password_field = ft.TextField(
            width=340,
            text_size=20,
            hint_text="Masukkan password",
            color="black",
            password=True,
            can_reveal_password=True,
            filled=True,
            bgcolor="#F3F4F6",
            border_radius=8,
            content_padding=15,
            border_color="transparent",
        )

        teks_error = ft.Text("", color="red", size=14, weight="bold")

        def do_login(e=None):
            teks_error.value = ""
            page.update()
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    user_record = conn.cursor().execute(
                        "SELECT password FROM admins WHERE username = ?", (username_field.value,)
                    ).fetchone()
                    if user_record: 
                        db_password = user_record[0]
                        input_password = password_field.value
                        if db_password.startswith("$2"):
                            db_password = db_password.replace("$2y$", "$2b$")

                            if bcrypt.checkpw(input_password.encode('utf-8'), db_password.encode('utf-8')):
                                page.on_keyboard_event = None
                                tujuan()
                            else: 
                                teks_error.value = "Password or Username is Wrong"
                                page.update()
                        else:
                            if input_password == db_password: 
                                page.on_keyboard_event = None
                                tujuan()
                            else:
                                teks_error.value = "Password or Username is Wrong"
                                page.update()
                    else: 
                        teks_error.value = "Password or Username is Wrong"
                        page.update()
            except Exception as err:
                print(f"ERROR SAAT LOGIN: {err}")
                page.update()

        def enter_login(e: ft.KeyboardEvent):
            if e.key == "Enter" or e.key == "Numpad Enter":
                do_login()

        page.on_keyboard_event = enter_login

        def batal_login(e):
            page.on_keyboard_event = None
            nav["show_home"]()

        login_btn = create_filled_button(
            teks_button,
            button_color,
            do_login,
            width=340,
            height=65,
            text_size=teks_size,
        )
        page.add(
            build_standard_layout(
                content_control=ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(
                                content=ft.Image(src="/login.png", width=60, height=60),
                                bgcolor="#E3F2FD",
                                padding=20,
                                border_radius=50,
                            ),
                            ft.Text(
                                teks_judul, size=24, weight="bold", color=TEXT_COLOR
                            ),
                            ft.Column(
                                [
                                    ft.Text("Username", weight="bold", color="black"),
                                    username_field,
                                    ft.Text("Password", weight="bold", color="black"),
                                    password_field,
                                    teks_error,
                                ],
                                spacing=5,
                            ),
                            login_btn,
                        ],
                        horizontal_alignment="center",
                        spacing=15,
                    ),
                    width=450,
                    height=480,
                    bgcolor="white",
                    padding=20,
                    border_radius=20,
                    shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR),
                    margin=ft.margin.only(top=-130),
                ),
                back_func=batal_login,
            )
        )

    # ------------------------------------------------------------------
    # Daftarkan semua fungsi ke nav dict
    # ------------------------------------------------------------------
    nav["show_admin_dashboard"] = show_admin_dashboard
    nav["show_edit_tools_menu"] = show_edit_tools_menu
    nav["show_manage_tools_page"] = show_manage_tools_page
    nav["show_history_page"] = show_history_page
    nav["show_add_tool_page"] = show_add_tool_page
    nav["show_login_admin"] = show_login_admin
    nav["show_sync_web_page"] = show_sync_web_page
