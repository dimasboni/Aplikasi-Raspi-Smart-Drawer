"""
flow_pages.py
=============
Berisi alur transaksi (flow) yang melibatkan RFID dan Sensor IR:
  - show_rfid_page               : Halaman scan RFID card user/admin
  - show_position_selection      : Pilih posisi slot alat
  - show_visual_sensor_flow      : Tunggu sensor IR saat AMBIL alat
  - show_scan_tag_alat           : Scan tag RFID alat saat peminjaman
  - show_all_done                : Konfirmasi peminjaman berhasil
  - show_scan_kembali            : Scan tag RFID alat saat pengembalian
  - show_konfirmasi_kembali      : Konfirmasi daftar alat yang dikembalikan
  - show_visual_sensor_kembali   : Tunggu sensor IR saat TARUH alat
  - show_all_done_kembali        : Konfirmasi pengembalian berhasil

Cara pemakaian:
    from pages.flow_pages import register_flow_pages
    register_flow_pages(page, session_data, nav)
"""

import asyncio
import time
import threading
import sqlite3

import flet as ft

from config import (
    TEXT_COLOR,
    SUB_TEXT_COLOR,
    SHADOW_COLOR,
    BLUE_SENSOR,
    GREEN_SENSOR,
)
from db_manager import simpan_log, simpan_log_pengembalian, get_borrowed_tools
from sensor_manager import status_sensor_realtime
from ui_komponen import create_filled_button, build_standard_layout


def register_flow_pages(page: ft.Page, session_data: dict, nav: dict):
    """
    Mendaftarkan semua fungsi flow ke dalam dict 'nav'.
    nav keys yang ditambahkan:
        nav['show_rfid_page']
        nav['show_position_selection']
        nav['show_visual_sensor_flow']
        nav['show_scan_tag_alat']
        nav['show_all_done']
        nav['show_scan_kembali']
        nav['show_konfirmasi_kembali']
        nav['show_visual_sensor_kembali']
        nav['show_all_done_kembali']
    """

    # ------------------------------------------------------------------
    # SHOW ALL DONE (peminjaman sukses)
    # ------------------------------------------------------------------
    def show_all_done(tool_name):
        page.clean()
        success_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text("✅", size=80),
                    ft.Text("Peminjaman Sukses!", size=28, weight="bold", color=GREEN_SENSOR),
                    ft.Text(f"Alat {tool_name} berhasil dipinjam.", size=16, color="black"),
                    ft.Container(height=10),
                    ft.ProgressRing(width=25, height=25, color=GREEN_SENSOR, stroke_width=3),
                    ft.Text("Kembali ke layar utama...", size=12, color="grey"),
                ],
                alignment="center", horizontal_alignment="center", spacing=5,
            ),
            width=450, padding=40, bgcolor="white", border_radius=20,
            shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR),
            alignment=ft.Alignment(0, 0),
        )
        page.add(build_standard_layout(ft.Container(content=success_card, alignment=ft.Alignment(0, 0))))

        async def auto():
            await asyncio.sleep(4.0)
            nav["show_home"]()

        page.run_task(auto)

    # ------------------------------------------------------------------
    # SHOW ALL DONE KEMBALI (pengembalian sukses)
    # ------------------------------------------------------------------
    def show_all_done_kembali():
        page.clean()
        success_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text("🎉", size=80),
                    ft.Text("Pengembalian Berhasil!", size=28, weight="bold", color="#3B82F6"),
                    ft.Text("Semua alat telah masuk ke dalam laci.", size=16, color="black"),
                    ft.Container(height=10),
                    ft.ProgressRing(width=25, height=25, color="#3B82F6", stroke_width=3),
                    ft.Text("Menutup sesi otomatis...", size=12, color="grey"),
                ],
                alignment="center", horizontal_alignment="center", spacing=5,
            ),
            width=450, padding=40, bgcolor="white", border_radius=20,
            shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR),
            alignment=ft.Alignment(0, 0),
        )
        page.add(build_standard_layout(ft.Container(content=success_card, alignment=ft.Alignment(0, 0))))

        async def auto():
            await asyncio.sleep(4.0)
            nav["show_home"]()

        page.run_task(auto)

    # ------------------------------------------------------------------
    # SHOW VISUAL SENSOR KEMBALI (tunggu sensor saat taruh)
    # ------------------------------------------------------------------
    def show_visual_sensor_kembali(scanned_tools, index):
        if index >= len(scanned_tools):
            show_all_done_kembali()
            return
        page.clean()
        current_tool = scanned_tools[index]
        indicator = ft.Container(
            content=ft.Text("📥", size=50),
            width=120, height=120, bgcolor="orange",
            border_radius=60, alignment=ft.Alignment(0, 0), animate=300,
        )
        sensor_box = ft.Container(
            content=indicator, width=800, height=350,
            bgcolor="#FFF3E0", border_radius=20, alignment=ft.Alignment(0, 0),
            shadow=ft.BoxShadow(blur_radius=15, color=SHADOW_COLOR), animate=300,
        )
        status_txt = ft.Text(
            f"MENUNGGU SENSOR IR...\nSilakan taruh {current_tool} ke posisinya ({index+1}/{len(scanned_tools)})",
            size=18, color="black", weight="bold", text_align="center",
        )

        async def pantau_sensor_ditaruh():
            while status_sensor_realtime.get(current_tool, 0) == 0:
                await asyncio.sleep(0.5)
            indicator.bgcolor = GREEN_SENSOR
            sensor_box.bgcolor = "#E8F5E9"
            status_txt.value = f"{current_tool} Berhasil Ditaruh!"
            status_txt.color = GREEN_SENSOR
            page.update()
            simpan_log_pengembalian(session_data["user_now"], current_tool)
            await asyncio.sleep(2.0)
            show_visual_sensor_kembali(scanned_tools, index + 1)

        page.add(
            build_standard_layout(
                ft.Column([sensor_box, ft.Container(height=10), status_txt],
                          alignment="center", horizontal_alignment="center")
            )
        )
        page.run_task(pantau_sensor_ditaruh)

    # ------------------------------------------------------------------
    # SHOW KONFIRMASI KEMBALI
    # ------------------------------------------------------------------
    def show_konfirmasi_kembali(scanned_tools):
        page.clean()
        list_ui = ft.Column(
            [ft.Text(f"📦 {t}", size=18, color="black", weight="bold") for t in scanned_tools],
            scroll=ft.ScrollMode.AUTO,
        )
        content = ft.Column(
            [
                ft.Text("Yakin kembalikan alat berikut?", size=24, weight="bold", color="black"),
                ft.Container(height=10),
                ft.Container(content=list_ui, height=200),
                ft.Container(height=20),
                create_filled_button(
                    "Lanjut Buka Laci", "green",
                    lambda _: show_visual_sensor_kembali(scanned_tools, 0),
                    width=400, height=50,
                ),
            ],
            horizontal_alignment="center", alignment="center",
        )
        page.add(
            build_standard_layout(
                content,
                back_func=lambda _: show_scan_kembali(get_borrowed_tools(session_data["user_now"])),
            )
        )

    # ------------------------------------------------------------------
    # SHOW SCAN KEMBALI (scan RFID alat saat pengembalian)
    # ------------------------------------------------------------------
    def show_scan_kembali(borrowed_tools):
        page.clean()
        scanned_items = []
        input_tag = ft.TextField(
            autofocus=True, width=1, height=1, border=ft.InputBorder.NONE,
            color="transparent", bgcolor="transparent", cursor_color="transparent",
            on_blur=lambda e: input_tag.focus(),
        )
        status_text = ft.Text("Siap Membaca Tag...", size=16, color=BLUE_SENSOR, weight="bold")
        scanned_list_ui = ft.ListView(spacing=10, height=180)
        btn_confirm = create_filled_button(
            "Selesai & Konfirmasi", "#10B981",
            lambda _: show_konfirmasi_kembali(scanned_items),
            width=600, height=50, disabled=True,
        )

        def update_ui():
            scanned_list_ui.controls.clear()
            for item in scanned_items:
                scanned_list_ui.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("✅", size=18),
                            ft.Text(item, weight="bold", color=TEXT_COLOR, expand=True),
                            ft.Container(
                                content=ft.Text("Terverifikasi", size=10, color="white"),
                                bgcolor="#10B981",
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                border_radius=10,
                            ),
                        ]),
                        bgcolor="#F0FDF4", padding=15, border_radius=10,
                        border=ft.border.all(1, "#BBF7D0"), width=580,
                    )
                )
            btn_confirm.disabled = len(scanned_items) == 0
            page.update()

        def proses_scan(e):
            uid_tag = str(e.control.value).strip()
            e.control.value = ""
            page.update()
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    res = (
                        conn.cursor()
                        .execute(
                            "SELECT name FROM tools WHERE TRIM(CAST(rfid_tag_uid AS TEXT)) = ?",
                            (uid_tag,),
                        )
                        .fetchone()
                    )
                if res:
                    if res[0] in borrowed_tools:
                        if res[0] not in scanned_items:
                            scanned_items.append(res[0])
                            status_text.value = f"Berhasil: {res[0]}"
                            status_text.color = "#10B981"
                            update_ui()
                        else:
                            status_text.value = f"Sudah di-scan: {res[0]}"
                            status_text.color = "orange"
                    else:
                        status_text.value = f"Bukan pinjaman Anda: {res[0]}"
                        status_text.color = "red"
                else:
                    status_text.value = "Tag Tidak Dikenal!"
                    status_text.color = "red"
            except Exception:
                pass
            page.update()
            input_tag.focus()

        input_tag.on_submit = proses_scan
        top_card = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Image(src="/scanrfid.png", width=60, height=60),
                        padding=10, bgcolor="#EFF6FF", border_radius=15,
                    ),
                    ft.Column(
                        [
                            ft.Text("Area Scan Aktif", size=20, weight="bold", color=TEXT_COLOR),
                            status_text,
                        ],
                        spacing=2,
                    ),
                ],
                alignment="center", spacing=20,
            ),
            bgcolor="white", padding=20, border_radius=15, width=600,
            border=ft.border.all(2, BLUE_SENSOR),
            shadow=ft.BoxShadow(blur_radius=15, color=SHADOW_COLOR),
            on_click=lambda _: input_tag.focus(),
        )
        content = ft.Column(
            [
                top_card,
                ft.Container(height=10),
                ft.Text("Alat Terverifikasi:", weight="bold", color="grey"),
                ft.Container(content=scanned_list_ui, height=180),
                btn_confirm,
                input_tag,
            ],
            horizontal_alignment="center", alignment="center",
        )
        page.add(build_standard_layout(content, back_func=nav["show_list_pinjaman_user"]))
        threading.Thread(
            target=lambda: [time.sleep(0.5), input_tag.focus(), page.update()]
        ).start()

    # ------------------------------------------------------------------
    # SHOW SCAN TAG ALAT (verifikasi RFID alat saat peminjaman)
    # ------------------------------------------------------------------
    def show_scan_tag_alat(tool_name):
        page.clean()
        state = {"aktif": True}
        input_tag = ft.TextField(
            autofocus=True, width=1, height=1, border=ft.InputBorder.NONE,
            color="transparent", bgcolor="transparent", cursor_color="transparent",
            on_blur=lambda e: input_tag.focus() if state.get("aktif") else None,
        )

        def keluar_halaman(tujuan_func):
            state["aktif"] = False
            input_tag.disabled = True
            page.update()
            tujuan_func()

        def proses_scan_tag(e):
            if not state["aktif"]:
                return
            uid_tag = str(e.control.value).strip()
            input_tag.disabled = True
            visual_card.border = ft.border.all(3, "#F59E0B")
            status_text.value = "Mencocokkan Data..."
            status_text.color = "#F59E0B"
            page.update()
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    tag_data = (
                        conn.cursor()
                        .execute(
                            "SELECT name FROM tools WHERE TRIM(CAST(rfid_tag_uid AS TEXT)) = ?",
                            (uid_tag,),
                        )
                        .fetchone()
                    )
                if tag_data:
                    nama_di_db = tag_data[0]
                    if nama_di_db.lower() == tool_name.lower():
                        state["aktif"] = False
                        visual_card.border = ft.border.all(3, GREEN_SENSOR)
                        status_text.value = "Verifikasi Sukses!"
                        status_text.color = GREEN_SENSOR
                        page.update()
                        simpan_log(session_data["user_now"], nama_di_db, "PINJAM")
                        time.sleep(0.5)
                        keluar_halaman(lambda: show_all_done(nama_di_db))
                    else:
                        visual_card.border = ft.border.all(3, "red")
                        status_text.value = f"SALAH ALAT!\nTerdeteksi: {nama_di_db}"
                        status_text.color = "red"
                        page.update()
                        time.sleep(1.5)
                        visual_card.border = ft.border.all(2, BLUE_SENSOR)
                        status_text.value = f"Scan Tag RFID pada {tool_name}"
                        status_text.color = SUB_TEXT_COLOR
                        e.control.value = ""
                        input_tag.disabled = False
                        e.control.focus()
                        page.update()
                else:
                    visual_card.border = ft.border.all(3, "red")
                    status_text.value = "Tag Tidak Dikenal!"
                    status_text.color = "red"
                    page.update()
                    time.sleep(1.5)
                    visual_card.border = ft.border.all(2, BLUE_SENSOR)
                    status_text.value = f"Scan Tag RFID pada {tool_name}"
                    status_text.color = SUB_TEXT_COLOR
                    e.control.value = ""
                    input_tag.disabled = False
                    e.control.focus()
                    page.update()
            except Exception:
                pass

        input_tag.on_submit = proses_scan_tag

        async def bom_waktu_tag():
            await asyncio.sleep(10.0)
            if state["aktif"]:
                state["aktif"] = False
                visual_card.border = ft.border.all(3, "orange")
                status_text.value = "Waktu Habis! Transaksi Batal."
                status_text.color = "orange"
                page.update()
                await asyncio.sleep(1.0)
                keluar_halaman(nav["show_home"])

        status_text = ft.Text(
            f"Scan Tag RFID pada {tool_name}", size=16, color=SUB_TEXT_COLOR, text_align="center"
        )
        visual_card = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Image(src="/scanrfid.png", width=120, height=120),
                        padding=20, bgcolor="#F8FAFC", border_radius=60,
                    ),
                    ft.Text("Verifikasi Alat", size=24, weight="bold", color=TEXT_COLOR),
                    status_text,
                    ft.Container(height=10),
                    ft.ProgressRing(width=25, height=25, color=BLUE_SENSOR, stroke_width=3),
                ],
                horizontal_alignment="center", alignment="center",
            ),
            width=450, padding=40, bgcolor="white", border_radius=20,
            border=ft.border.all(2, BLUE_SENSOR),
            shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR),
            on_click=lambda _: input_tag.focus() if state["aktif"] else None,
        )
        page.add(
            build_standard_layout(
                ft.Column([visual_card, input_tag], horizontal_alignment="center", alignment="center"),
                back_func=lambda e: keluar_halaman(nav["show_home"]),
            )
        )
        threading.Thread(
            target=lambda: [time.sleep(0.5), input_tag.focus(), page.update()]
        ).start()
        page.run_task(bom_waktu_tag)

    # ------------------------------------------------------------------
    # SHOW VISUAL SENSOR FLOW (tunggu sensor IR saat AMBIL)
    # ------------------------------------------------------------------
    def show_visual_sensor_flow(tool_name, slot_num):
        page.clean()
        indicator_circle = ft.Container(
            content=ft.Text(str(slot_num), size=60, weight="bold", color="white"),
            width=120, height=120, bgcolor=BLUE_SENSOR,
            border_radius=60, alignment=ft.Alignment(0, 0), animate=300,
        )
        sensor_box = ft.Container(
            content=indicator_circle, width=800, height=350,
            bgcolor="#EBF3FF", border_radius=20, alignment=ft.Alignment(0, 0),
            shadow=ft.BoxShadow(blur_radius=15, color=SHADOW_COLOR), animate=300,
        )
        status_txt = ft.Text(
            "MENUNGGU SENSOR IR...\nSilakan ambil barang di laci...",
            size=18, color=SUB_TEXT_COLOR, text_align="center",
        )

        async def pantau_sensor_diambil():
            while status_sensor_realtime.get(tool_name, 1) == 1:
                await asyncio.sleep(0.5)
            indicator_circle.bgcolor = GREEN_SENSOR
            sensor_box.bgcolor = "#E8F5E9"
            status_txt.value = "Barang Terdeteksi Diambil!"
            status_txt.color = GREEN_SENSOR
            page.update()
            await asyncio.sleep(1.5)
            show_scan_tag_alat(tool_name)

        page.add(
            build_standard_layout(
                ft.Column([sensor_box, ft.Container(height=10), status_txt],
                          alignment="center", horizontal_alignment="center")
            )
        )
        page.run_task(pantau_sensor_diambil)

    # ------------------------------------------------------------------
    # SHOW POSITION SELECTION
    # ------------------------------------------------------------------
    def show_position_selection(name, data):
        page.clean()
        pos_grid = ft.GridView(expand=True, max_extent=70, spacing=10)
        for i in range(1, 2):
            pos_grid.controls.append(
                ft.Container(
                    content=ft.Text(str(i), weight="bold", color=TEXT_COLOR),
                    alignment=ft.Alignment(0, 0),
                    bgcolor="white",
                    border=ft.border.all(2, "#4CAF50"),
                    border_radius=10,
                    on_click=lambda e, idx=i: show_visual_sensor_flow(name, idx),
                )
            )
        page.add(
            build_standard_layout(
                ft.Column(
                    [
                        ft.Text(f"Posisi {name}", size=32, weight="bold", color=TEXT_COLOR),
                        ft.Container(height=20),
                        ft.Container(content=pos_grid, height=300, width=600),
                    ],
                    horizontal_alignment="center", alignment="center",
                ),
                back_func=nav["show_peminjaman_page1"],
            )
        )

    # ------------------------------------------------------------------
    # SHOW RFID PAGE (scan kartu user/admin)
    # ------------------------------------------------------------------
    def show_rfid_page(title_text, next_destination_func, back_destination_func, tipe_akses="user"):
        page.clean()
        state = {"aktif": True}
        input_rfid = ft.TextField(
            autofocus=True, width=1, height=1, border=ft.InputBorder.NONE,
            color="transparent", bgcolor="transparent", cursor_color="transparent",
            on_blur=lambda e: input_rfid.focus() if state.get("aktif") else None,
        )

        def keluar_halaman(tujuan_func):
            state["aktif"] = False
            input_rfid.disabled = True
            page.update()
            tujuan_func()

        async def proses_scan_usb(e, simu_uid=None):
            if not state["aktif"]:
                return
            state["aktif"] = False
            uid_kartu = simu_uid if simu_uid else str(e.control.value).strip()
            input_rfid.disabled = True
            visual_card.border = ft.border.all(3, "#F59E0B")
            status_text.value = "Memeriksa ID..."
            status_text.color = "#F59E0B"
            page.update()
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    if tipe_akses == "admin":
                        user_data = (
                            conn.cursor()
                            .execute(
                                "SELECT username FROM admins WHERE CAST(rfid_card_uid AS TEXT) = ?",
                                (uid_kartu,),
                            )
                            .fetchone()
                        )
                    else:
                        user_data = (
                            conn.cursor()
                            .execute(
                                "SELECT nama FROM users WHERE CAST(rfid_card_uid AS TEXT) = ?",
                                (uid_kartu,),
                            )
                            .fetchone()
                        )
                if user_data:
                    nama_user = user_data[0]
                    session_data["user_now"] = nama_user
                    visual_card.border = ft.border.all(3, GREEN_SENSOR)
                    status_text.value = f"Akses Diberikan!\nHalo {nama_user}"
                    status_text.color = GREEN_SENSOR
                    page.update()
                    await asyncio.sleep(0.5)
                    keluar_halaman(next_destination_func)
                else:
                    visual_card.border = ft.border.all(3, "red")
                    status_text.value = "Akses Ditolak!\nKartu tidak sesuai hak akses."
                    status_text.color = "red"
                    page.update()
                    await asyncio.sleep(2.0)
                    keluar_halaman(back_destination_func)
            except Exception as err:
                print(f"❌ ERROR DATABASE RFID: {err}")
                visual_card.border = ft.border.all(3, "red")
                status_text.value = f"Sistem error:\n{err}"
                status_text.color = "red"
                page.update()
                await asyncio.sleep(3.0)
                keluar_halaman(back_destination_func)

        input_rfid.on_submit = proses_scan_usb

        async def bom_waktu():
            await asyncio.sleep(5.0)
            if state["aktif"]:
                state["aktif"] = False
                status_text.value = "Waktu Habis!"
                status_text.color = "orange"
                page.update()
                await asyncio.sleep(0.5)
                keluar_halaman(back_destination_func)

        status_text = ft.Text(
            "Silakan tempelkan ID Card Anda", size=16, color=SUB_TEXT_COLOR, text_align="center"
        )
        visual_card = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Image(src="/scanrfid.png", width=120, height=120),
                        padding=20, bgcolor="#F8FAFC", border_radius=60,
                    ),
                    ft.Text(title_text, size=24, weight="bold", color=TEXT_COLOR),
                    status_text,
                    ft.Container(height=10),
                    ft.ProgressRing(width=25, height=25, color=BLUE_SENSOR, stroke_width=3),
                    ft.Row(
                        [
                            create_filled_button(
                                "Simulasi Admin", "blue",
                                lambda kejadian_klik: page.run_task(
                                    proses_scan_usb, kejadian_klik, simu_uid="3676831940"
                                ),
                            ),
                            create_filled_button(
                                "Simulasi User", "green",
                                lambda kejadian_klik: page.run_task(
                                    proses_scan_usb, kejadian_klik, simu_uid="2344461204"
                                ),
                            ),
                        ],
                        alignment="center", spacing=10,
                    ),
                ],
                horizontal_alignment="center", alignment="center",
            ),
            width=450, padding=40, bgcolor="white", border_radius=20, margin=ft.margin.only(top=-100),
            border=ft.border.all(2, BLUE_SENSOR),
            shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR),
            on_click=lambda _: input_rfid.focus() if state["aktif"] else None,
        )
        page.add(
            build_standard_layout(
                ft.Column([visual_card, input_rfid], horizontal_alignment="center", alignment="center"),
                back_func=lambda e: keluar_halaman(back_destination_func),
            )
        )
        threading.Thread(
            target=lambda: [time.sleep(0.5), input_rfid.focus(), page.update()]
        ).start()
        page.run_task(bom_waktu)

    # ------------------------------------------------------------------
    # Daftarkan ke nav
    # ------------------------------------------------------------------
    nav["show_rfid_page"] = show_rfid_page
    nav["show_position_selection"] = show_position_selection
    nav["show_visual_sensor_flow"] = show_visual_sensor_flow
    nav["show_scan_tag_alat"] = show_scan_tag_alat
    nav["show_all_done"] = show_all_done
    nav["show_scan_kembali"] = show_scan_kembali
    nav["show_konfirmasi_kembali"] = show_konfirmasi_kembali
    nav["show_visual_sensor_kembali"] = show_visual_sensor_kembali
    nav["show_all_done_kembali"] = show_all_done_kembali
