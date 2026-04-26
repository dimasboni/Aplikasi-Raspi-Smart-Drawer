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

import flet as ft
from PIL import Image as PILImage

from config import (
    BG_COLOR,
    TEXT_COLOR,
    SHADOW_COLOR,
    BLUE_SENSOR,
    GREEN_SENSOR,
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
    def show_edit_tools_menu(e=None):
        page.clean()
        page.add(
            build_standard_layout(
                title_text="EDIT TOOLS",
                content_control=ft.Column(
                    [
                        ft.Container(height=20),
                        ft.Row(
                            [
                                create_menu_card(
                                    "Add Tools",
                                    "Tambah",
                                    "tambah.png",
                                    "#E8F5E9",
                                    lambda _: show_add_tool_page(),
                                ),
                                create_menu_card(
                                    "Manage",
                                    "Ubah / Hapus",
                                    "edit.png",
                                    "#E3F2FD",
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
        page.overlay.extend([dialog_edit, dialog_browser])
        page.update()

        # ---- Sub-fungsi: buka dialog edit alat ----
        def buka_dialog_edit(nama_alat_lama, rfid_lama, gambar_lama):
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
                    dirs = []
                    files = []
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
                        thumb_name = f"_thumb_{f}"
                        thumb_path = os.path.join("assets", thumb_name)
                        try:
                            pil_img = PILImage.open(full_path)
                            pil_img.thumbnail((35, 35))
                            pil_img.save(thumb_path, format="PNG")
                        except Exception:
                            thumb_name = None

                        if thumb_name:
                            thumb = ft.Image(
                                src=f"/{thumb_name}", width=35, height=35, fit="contain"
                            )
                        else:
                            thumb = ft.Icon("image", color="#10B981")

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
                except Exception as e:
                    file_list_view.controls.append(
                        ft.Text(f"Akses ditolak: {e}", color="red")
                    )
                page.update()

            def navigate_browser(new_path):
                current_path[0] = new_path
                update_browser_ui()

            def pilih_file_manual(filepath):
                nama_asli = os.path.basename(filepath)
                nama_baru = f"custom_{int(time.time())}_{nama_asli}"
                lokasi_simpan = os.path.join("assets", nama_baru)
                try:
                    shutil.copy(filepath, lokasi_simpan)
                    path_gambar_sekarang[0] = nama_baru
                    preview_img.content = ft.Image(
                        src=f"/{nama_baru}", width=150, height=150, fit="contain"
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

            def putar_gambar(e):
                file_lama = path_gambar_sekarang[0]
                lokasi_lama = f"assets/{file_lama}"
                try:
                    with PILImage.open(lokasi_lama) as img:
                        img_rotated = img.rotate(-90, expand=True)
                        file_baru = (
                            f"{os.path.splitext(file_lama)[0].split('_')[0]}"
                            f"_{int(time.time())}_{random.randint(100, 999)}.png"
                        )
                        img_rotated.save(f"assets/{file_baru}")

                    preview_img.content = ft.Image(
                        src=f"/{file_baru}",
                        width=150,
                        height=150,
                        fit="contain",
                        animate_opacity=200,
                    )
                    path_gambar_sekarang[0] = file_baru
                    page.update()
                except Exception:
                    pass

            def batal_edit(e):
                dialog_edit.open = False
                page.update()

            def eksekusi_simpan(e):
                file_terakhir = path_gambar_sekarang[0]
                if "_" in file_terakhir:
                    nama_asli = (
                        file_terakhir.split("_")[0] + os.path.splitext(file_terakhir)[1]
                    )
                    try:
                        shutil.copy(
                            os.path.join("assets", file_terakhir),
                            os.path.join("assets", nama_asli),
                        )
                        path_gambar_sekarang[0] = nama_asli
                    except Exception:
                        pass
                try:
                    with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                        conn.execute(
                            "UPDATE tools SET name = ?, rfid_tag_uid = ?, img = ? WHERE name = ?",
                            (
                                input_nama.value,
                                input_rfid.value,
                                path_gambar_sekarang[0],
                                nama_alat_lama,
                            ),
                        )
                        conn.commit()
                        dialog_edit.open = False
                        show_manage_tools_page()
                except Exception:
                    pass

            input_nama = ft.TextField(label="Nama Alat", value=nama_alat_lama)
            input_rfid = ft.TextField(label="RFID tag UID", value=rfid_lama)

            dialog_edit.title = ft.Text(f"Edit Alat: {nama_alat_lama}")
            dialog_edit.on_dismiss = (
                lambda _: setattr(dialog_edit, "open", False) or page.update()
            )
            kolom_kiri_edit=ft.Column(
                [
                    input_nama,
                    input_rfid,
                ],
                width=250
            )
            kolom_edit_kanan=ft.Column(
                [
                    ft.ElevatedButton(
                        "Pilih Gambar dari Perangkat",
                        bgcolor="#E3F2FD",
                        color="blue",
                        on_click=buka_browser_manual,
                    ),
                    ft.Row(
                        [
                            preview_img,
                            ft.ElevatedButton(
                                "Putar 90°", icon="rotate_right", on_click=putar_gambar
                            ),
                        ],
                    )
                ],
                width=300
            )
            
            dialog_edit.content = ft.Row(
                [
                    kolom_kiri_edit, kolom_edit_kanan
                ],
                alignment="center",
                spacing=15


            #    [
            #        input_nama,
            #        input_rfid,
            #        ft.Divider(),
            #        ft.ElevatedButton(
            #            "Pilih Gambar dari Perangkat",
            #            bgcolor="#E3F2FD",
            #            color="blue",
            #            on_click=buka_browser_manual,
            #        ),
            #        ft.Divider(),
            #        ft.Row(
            #            [
            #                preview_img,
            #                ft.ElevatedButton(
            #                    "Putar 90°", icon="rotate_right", on_click=putar_gambar
            #                ),
            #            ],
            #            alignment="center",
            #            spacing=20,
            #        ),
            #    ],
            #    tight=True,
            #    spacing=15,
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
        def hapus_alat_db(nama_alat):
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    conn.cursor().execute(
                        "DELETE FROM tools WHERE name = ?", (nama_alat,)
                    )
                    conn.commit()
                show_manage_tools_page()
            except Exception:
                pass

        # ---- Buat daftar alat dengan pagination ----
        list_ui = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        try:
            with sqlite3.connect("smartdrawer.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name, mqtt_topic, rfid_tag_uid, img FROM tools",
                )
                semua_alat = cursor.fetchall()
        except Exception:
            semua_alat= []

        for baris in semua_alat:
            nama_alat, topik, rfid_alat, gambar_alat = (
                baris[0],
                baris[1],
                baris[2],
                baris[3],
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
                            on_click=lambda _, n=nama_alat, r=rfid_alat, g=gambar_alat: buka_dialog_edit(
                                n, r, g
                            ),
                            ink=True,
                        ),
                        ft.Container(
                            content=ft.Text(
                                "🗑️ Hapus", size=14, color="red", weight="bold"
                            ),
                            padding=10,
                            on_click=lambda _, n=nama_alat: hapus_alat_db(n),
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

        

        main_card = ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=10),
                    ft.Container(content=list_ui, height=300),
                ],
                horizontal_alignment="center",
            ),
            width=700,
            bgcolor="white",
            padding=30,
            border_radius=20,
            shadow=ft.BoxShadow(blur_radius=20, color=SHADOW_COLOR),
        )

        tampilan = build_standard_layout(
            title_text="List Tool on the System",
            content_control=ft.Column([main_card], horizontal_alignment="center", alignment="center", margin=ft.margin.only(top=-100)),
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
                            ft.DataCell(ft.Text(str(row[0]), color="black")),
                            ft.DataCell(
                                ft.Text(str(row[1]), weight="bold", color="black")
                            ),
                            ft.DataCell(
                                ft.Text(
                                    str(row[2]) if len(row) > 2 and row[2] else "-",
                                    color="gray",
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
                    ft.DataColumn(ft.Text("User", weight="bold", color="black")),
                    ft.DataColumn(ft.Text("Alat", weight="bold", color="black")),
                    ft.DataColumn(ft.Text("Waktu", weight="bold", color="black")),
                    ft.DataColumn(ft.Text("Status", weight="bold", color="black")),
                ],
                rows=rows,
                border=ft.border.all(1, "#E5E7EB"),
                border_radius=10,
                heading_row_color="#F3F4F6",
                vertical_lines=ft.border.BorderSide(1, "#F3F4F6"),
                horizontal_lines=ft.border.BorderSide(1, "#F3F4F6"),
                column_spacing=30,
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
                src=f"/{path_gambar_baru[0]}", width=120, height=120, fit="contain"
            ),
            width=120,
            height=120,
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
                    thumb_name = f"_thumb_{f}"
                    thumb_path = os.path.join("assets", thumb_name)
                    try:
                        pil_img = PILImage.open(full_path)
                        pil_img.thumbnail((35, 35))
                        pil_img.save(thumb_path, format="PNG")
                    except Exception:
                        thumb_name = None

                    if thumb_name:
                        thumb = ft.Image(
                            src=f"/{thumb_name}", width=35, height=35, fit="contain"
                        )
                    else:
                        thumb = ft.Text("🖼️", size=16)

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
            nama_asli = os.path.basename(filepath)
            nama_baru = f"tool_{int(time.time())}_{nama_asli}"
            lokasi_simpan = os.path.join("assets", nama_baru)
            try:
                shutil.copy(filepath, lokasi_simpan)
                path_gambar_baru[0] = nama_baru
                preview_img.content = ft.Image(
                    src=f"/{nama_baru}", width=120, height=120, fit="contain"
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

        # Fungsi rotasi gambar
        def putar_gambar_tambah(e):
            file_sekarang = path_gambar_baru[0]
            if file_sekarang == "tambah.png":
                notif_text.value = "❌ Pilih Gambar Terlebih Dahulu"
                page.update()
                return

            lokasi_file = f"assets/{file_sekarang}"
            try:
                with PILImage.open(lokasi_file) as img:
                    if e.control.data == "kiri":
                        img_rotated = img.rotate(90, expand=True)
                    else:
                        img_rotated = img.rotate(-90, expand=True)

                    file_baru = (
                        f"tool_{int(time.time())}_{random.randint(100, 999)}.png"
                    )
                    img_rotated.save(f"assets/{file_baru}")

                preview_img.content = ft.Image(
                    src=f"/{file_baru}", width=120, height=120, fit="contain"
                )
                path_gambar_baru[0] = file_baru
                page.update()
            except Exception as err:
                print(f"Error rotasi:{err}")

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
            width=200,
            border_color=BLUE_SENSOR,
            border_radius=10,
            read_only=True,
            color=TEXT_COLOR,
        )

        dd_laci = ft.Dropdown(
            label="Lokasi Laci (page)",
            width=350,
            border_color=BLUE_SENSOR,
            border_radius=10,
            color=TEXT_COLOR,
            options=[
                ft.dropdown.Option("1", "Laci 1"),
                ft.dropdown.Option("2", "Laci 2"),
            ],
        )

        dd_pin = ft.Dropdown(
            label="Posisi Pin Sensor (mqtt_topic)",
            width=350,
            border_color=BLUE_SENSOR,
            border_radius=10,
            color=TEXT_COLOR,
            options=[ft.dropdown.Option(f"P{str(i).zfill(2)}") for i in range(16)],
        )

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
            if not input_nama.value.strip():
                notif_text.value = "❌ Nama alat tidak boleh kosong!"
                page.update()
                return
            if not input_rfid.value.strip():
                notif_text.value = "❌ Harap scan Tag RFID terlebih dahulu!"
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

            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    conn.execute(
                        "INSERT INTO tools (name, rfid_tag_uid, img, total, page, mqtt_topic, rot) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            input_nama.value.strip(),
                            input_rfid.value.strip(),
                            path_gambar_baru[0],
                            1,
                            int(dd_laci.value),
                            dd_pin.value,
                            0,
                        ),
                    )
                    conn.commit()
                notif_text.value = "✅ Alat berhasil ditambahkan!"
                notif_text.color = "#10B981"
                page.update()
                time.sleep(1.0)
                show_edit_tools_menu()
            except sqlite3.IntegrityError:
                notif_text.value = "❌ Nama alat sudah ada di database!"
                page.update()
            except Exception as err:
                notif_text.value = f"❌ Gagal menyimpan: {err}"
                page.update()

        # Layout form
        kolom_kiri = ft.Column(
            [
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
            spacing=15,
        )

        kolom_kanan = ft.Column(
            [
                input_nama,
                ft.Container(height=10),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "↺ Putar Kiri",
                                    data="kiri",
                                    on_click=putar_gambar_tambah,
                                    color=BLUE_SENSOR,
                                    bgcolor="#E3F2FD",
                                ),
                                ft.ElevatedButton(
                                    "Putar Kanan ↻",
                                    data="kanan",
                                    on_click=putar_gambar_tambah,
                                    color=BLUE_SENSOR,
                                    bgcolor="#E3F2FD",
                                ),
                            ],
                            alignment="center",
                            spacing=20,
                        ),
                        preview_img,
                        ft.ElevatedButton(
                            "📁 Pilih Gambar",
                            icon="folder_open",
                            bgcolor="#E3F2FD",
                            color="blue",
                            on_click=buka_browser_tambah,
                        ),
                    ],
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
                            alignment="center",
                            vertical_alignment="start",
                            spacing=40,
                        ),
                        notif_text,
                        create_filled_button(
                            "Simpan Data Alat",
                            GREEN_SENSOR,
                            simpan_alat_baru,
                            width=750,
                            height=45,
                        ),
                    ],
                    horizontal_alignment="center",
                    spacing=10,
                ),
                width=850,
                bgcolor="white",
                padding=25,
                border_radius=20,
                shadow=ft.BoxShadow(blur_radius=20, color=SHADOW_COLOR),
            )
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
                    if (
                        conn.cursor()
                        .execute(
                            "SELECT * FROM admins WHERE username = ? AND password = ?",
                            (username_field.value, password_field.value),
                        )
                        .fetchone()
                    ):
                        page.on_keyboard_event = None
                        tujuan()
                    else:
                        teks_error.value = "❌ Username atau password salah!"
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
