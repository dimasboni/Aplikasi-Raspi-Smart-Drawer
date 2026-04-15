import threading
import json
import flet as ft
import time
import asyncio 
import math
import sqlite3 # (Untuk keperluan admin ringan)
import os 
import random 
import shutil
import sys 
from PIL import Image as PILImage

# 1. IMPORT KONFIGURASI WARNA & UKURAN BUKU
from config import BG_COLOR, TEXT_COLOR, SUB_TEXT_COLOR, SHADOW_COLOR, BLUE_SENSOR, GREEN_SENSOR, PAGE_WIDTH, PAGE_HEIGHT, HEADER_HEIGHT, CONTENT_AREA_HEIGHT, settings

# 2. IMPORT OTAK DATABASE (GUDANG DATA)
from db_manager import get_tools_from_db, get_borrowed_tools, simpan_log, simpan_log_pengembalian

# 3. IMPORT OTAK SENSOR (MATA-MATA)
from sensor_manager import jalankan_sensor_background, status_sensor_realtime

# 4. IMPORT PABRIK DESAIN KOMPONEN (TUKANG KAYU)
from ui_komponen import create_filled_button, create_menu_card, create_tool_grid_item, build_standard_layout

# ==============================================================================
# --- MAIN PROGRAM FLET (RANGKA UTAMA) --
# Di sinilah semua file pembantu tadi "bertemu" dan saling ngobrol!
# ==============================================================================
def main(page: ft.Page):
    #FullScreen Mode, agar aplikasi tidak bisa di close sembarangan #mengaktifkan mode layar fullscreen 
    page.window.maximized = True
    page.window.frameless = True #menghilangkan border dan title bar pada jendela aplikasi 
    page.window.focused = True
    page.window.fullscreen = True #Memastikan aplikasi langsung aktif di depan
    page.window.resizeable = False  
    page.title = settings.get("cabinet_name", "Smart Drawer System") 
    page.bgcolor = BG_COLOR
    #page.window.width = PAGE_WIDTH
    #page.window.height = PAGE_HEIGHT
    #page.window.top = 0 
    #page.window.left = 0
    page.expand = True 
    page.padding = 0 
    page.spacing = 0
     
    #try: page.window.center()
    #except: page.window.center()
    
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER  

    # Nyalakan sensor di latar belakang senyap-senyap! (Import dari sensor_manager.py)
    jalankan_sensor_background()

    dialog_edit = ft.AlertDialog(title=ft.Text("Sistem Siap"))

    session_data = {"user_now": "Guest"}

    # ==========================================================================
    # --- HALAMAN ADMINISTRATOR (UI ADMIN) ---
    # ==========================================================================
    
    # Fungsi ini ditaruh di atas agar bisa dipanggil oleh fungsi lain di bawahnya
    def show_edit_tools_menu(e=None):
        page.clean()
        page.add(build_standard_layout(ft.Column([ft.Text("Edit Tools", size=32, weight="bold", color=TEXT_COLOR), ft.Container(height=20), ft.Row([create_menu_card("Add Tools", "Tambah", "tambah.png", "#E8F5E9", lambda _: show_add_tool_page()), create_menu_card("Manage", "Ubah / Hapus", "edit.png", "#E3F2FD", lambda _: show_manage_tools_page())], alignment="center", spacing=30)], horizontal_alignment="center", alignment="center"), back_func=show_admin_dashboard))

    def show_manage_tools_page(e=None, halaman_sekarang=1):
        page.clean()
        page.overlay.clear()

        dialog_edit = ft.AlertDialog(title=ft.Text("Memuat..."))
        dialog_browser = ft.AlertDialog(title=ft.Text("Telusuri File Perangkat", weight="bold", color="black"), bgcolor="white")
        page.overlay.extend([dialog_edit, dialog_browser])
        page.update()

        def buka_dialog_edit(nama_alat_lama, rfid_lama, gambar_lama):
            preview_img = ft.Container(content=ft.Image(src=f"/{gambar_lama}", width=150, height=150, fit="contain"))
            path_gambar_sekarang = [gambar_lama]

            current_path = [os.path.expanduser("~")] 
            file_list_view = ft.ListView(height=300, spacing=5)
            #Komponen teks drive atau lokasi 
            path_text = ft.Text(current_path[0], weight="bold", size=14, color="blue", expand=True)

            """
            Tombol untuk ke drive C atau D (untuk windows)
            dan
            Tombol untuk home/pi dan media (untuk raspi) 
            """
            if os.name == "nt":
                 tombol_drive = ft.Row([
                         path_text,
                         ft.ElevatedButton("💻 Drive C:", bgcolor=BG_COLOR, color=TEXT_COLOR, on_click=lambda _: navigate_browser("c:\\") ),
                         ft.ElevatedButton("💻 Drive D:", bgcolor=BG_COLOR, color=TEXT_COLOR, on_click= lambda _: navigate_browser("D:\\"))
                 ])
            else:
                #tampilan untuk linux/raspi 
                tombol_drive = ft.Row([
                    path_text,
                    ft.ElevatedButton("🏠 Root (/)", icon="folder", bgcolor=BG_COLOR, color=TEXT_COLOR, on_click=lambda _: navigate_browser("/")),
                    ft.ElevatedButton("🔌 USB/Media", icon="usb", bgcolor=BG_COLOR, color=TEXT_COLOR, on_click=lambda _: navigate_browser("/media"))
                ])
            
            def update_browser_ui():
                file_list_view.controls.clear()
                path_text.value = f"Lokasi: {current_path[0]}"

                parent_dir = os.path.dirname(current_path[0])
                if parent_dir != current_path[0]: 
                    file_list_view.controls.append(
                        ft.TextButton(".. (Kembali)", icon="arrow_upward", icon_color="#3B82F6", style=ft.ButtonStyle(color="black", alignment=ft.Alignment(-1, 0)), width=580, on_click=lambda _, p=parent_dir: navigate_browser(p))
                    )

                try:
                    items = os.listdir(current_path[0])
                    dirs = []; files = []
                    for item in items:
                        full_path = os.path.join(current_path[0], item)
                        if os.path.isdir(full_path): dirs.append(item)
                        elif item.lower().endswith(('.png', '.jpg', '.jpeg')): files.append(item)
                    dirs.sort(); files.sort()

                    for d in dirs: file_list_view.controls.append(ft.TextButton(d, icon="folder", icon_color="orange", style=ft.ButtonStyle(color="black", alignment=ft.Alignment(-1, 0)), width=580, on_click=lambda _, p=os.path.join(current_path[0], d): navigate_browser(p)))
                    import io
                    for f in files:
                        full_path = os.path.join(current_path[0], f)
                        thumb_name = f"_thumb_{f}"
                        thumb_path = os.path.join("assets", thumb_name)
                        try:
                            pil_img = PILImage.open(full_path)
                            pil_img.thumbnail((35, 35))
                            pil_img.save(thumb_path, format="PNG")
                        except:
                            thumb_name = None
                        if thumb_name:
                            thumb = ft.Image(src=f"/{thumb_name}", width=35, height=35, fit="contain")
                        else:
                            thumb = ft.Icon("image", color="#10B981")
                        file_list_view.controls.append(
                            ft.Row([
                                thumb,
                                ft.TextButton(f, style=ft.ButtonStyle(color="black", alignment=ft.Alignment(-1, 0)), width=530, on_click=lambda _, p=full_path: pilih_file_manual(p))
                            ], alignment="start", vertical_alignment="center", height=45)
                        )
                except Exception as e:
                    file_list_view.controls.append(ft.Text(f"Akses ditolak: {e}", color="red"))
                page.update()

            def navigate_browser(new_path): current_path[0] = new_path; update_browser_ui()
            def pilih_file_manual(filepath):
                nama_asli = os.path.basename(filepath)
                nama_baru = f"custom_{int(time.time())}_{nama_asli}"
                lokasi_simpan = os.path.join("assets", nama_baru)
                try:
                    shutil.copy(filepath, lokasi_simpan)
                    path_gambar_sekarang[0] = nama_baru
                    preview_img.content = ft.Image(src=f"/{nama_baru}", width=150, height=150, fit="contain")
                    dialog_browser.open = False
                    page.update()
                except Exception: pass

            dialog_browser.content = ft.Column([tombol_drive, ft.Divider(), file_list_view], width=600, tight=True)
            dialog_browser.actions = [ft.TextButton("Batal & Tutup Browser", style=ft.ButtonStyle(color="black"), on_click=lambda _: tutup_browser())]

            def buka_browser_manual(e): update_browser_ui(); dialog_browser.open = True; page.update()
            def tutup_browser(): dialog_browser.open = False; page.update()

            def putar_gambar(e):
                file_lama = path_gambar_sekarang[0]
                lokasi_lama = f"assets/{file_lama}"
                try:
                    with PILImage.open(lokasi_lama) as img:
                        img_rotated = img.rotate(-90, expand=True)
                        file_baru = f"{os.path.splitext(file_lama)[0].split('_')[0]}_{int(time.time())}_{random.randint(100, 999)}.png"
                        img_rotated.save(f"assets/{file_baru}")

                    preview_img.content = ft.Image(src=f"/{file_baru}", width=150, height=150, fit="contain", animate_opacity=200)
                    path_gambar_sekarang[0] = file_baru
                    page.update()
                except Exception: pass

            def batal_edit(e): dialog_edit.open = False; page.update()
            def eksekusi_simpan(e):
                file_terakhir = path_gambar_sekarang[0]
                if "_" in file_terakhir:
                    nama_asli = file_terakhir.split("_")[0] + os.path.splitext(file_terakhir)[1]
                    try: shutil.copy(os.path.join("assets", file_terakhir), os.path.join("assets", nama_asli)); path_gambar_sekarang[0] = nama_asli 
                    except: pass
                try: 
                    with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                        conn.execute("UPDATE tools SET name = ?, rfid_tag_uid = ?, img = ? WHERE name = ?", (input_nama.value, input_rfid.value, path_gambar_sekarang[0], nama_alat_lama))
                        conn.commit()
                        dialog_edit.open = False 
                        show_manage_tools_page(halaman_sekarang=halaman_sekarang)
                except: pass

            input_nama = ft.TextField(label="Nama Alat", value=nama_alat_lama)
            input_rfid = ft.TextField(label="RFID tag UID", value=rfid_lama)

            dialog_edit.title = ft.Text(f"Edit Alat: {nama_alat_lama}")
            dialog_edit.on_dismiss = lambda _: setattr(dialog_edit, 'open', False) or page.update()
            dialog_edit.content = ft.Column([
                input_nama, input_rfid, ft.Divider(), 
                ft.ElevatedButton("Pilih Gambar dari Perangkat", bgcolor="#E3F2FD", color="blue", on_click=buka_browser_manual),
                ft.Divider(),
                ft.Row([preview_img, ft.ElevatedButton("Putar 90°", icon="rotate_right", on_click=putar_gambar)], alignment="center", spacing=20)
            ], tight=True, spacing=15)
            
            dialog_edit.actions = [
                ft.TextButton("Batal", on_click=batal_edit),
                ft.ElevatedButton("Simpan Perubahan", bgcolor="blue", color="white", on_click=eksekusi_simpan)
            ] 
            dialog_edit.open = True; page.update()

        def hapus_alat_db(nama_alat):
            try :
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    conn.cursor().execute("DELETE FROM tools WHERE name = ?", (nama_alat,))
                    conn.commit()
                show_manage_tools_page(halaman_sekarang=halaman_sekarang)
            except: pass

        list_ui = ft.Column(spacing=10)
        item_per_halaman = 5
        offset = (halaman_sekarang - 1) * item_per_halaman
        try: 
            with sqlite3.connect("smartdrawer.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tools")
                total_alat = cursor.fetchone()[0]
                cursor.execute("SELECT name, mqtt_topic, rfid_tag_uid, img FROM tools LIMIT ? OFFSET ?", (item_per_halaman, offset))
                semua_alat = cursor.fetchall()
        except: semua_alat, total_alat = [], 0

        for baris in semua_alat:
            nama_alat, topik, rfid_alat, gambar_alat = baris[0], baris[1], baris[2], baris[3]
            kotak_alat = ft.Container(
                content=ft.Row([
                    ft.Container(content=ft.Text("⚙️", size=16), bgcolor=BLUE_SENSOR, padding=10, border_radius=8),
                    ft.Text(nama_alat, size=16, weight="bold", color=TEXT_COLOR, expand=True),
                    ft.Text(topik, color="grey", size=14),
                    ft.Container(content=ft.Text("✏️ Edit", size=14, color="blue", weight="bold"), padding=10, on_click=lambda _, n=nama_alat, r=rfid_alat, g=gambar_alat: buka_dialog_edit(n, r, g), ink=True),
                    ft.Container(content=ft.Text("🗑️ Hapus", size=14, color="red", weight="bold"), padding=10, on_click=lambda _, n=nama_alat: hapus_alat_db(n), ink=True)
                ], alignment="center"), bgcolor="#F9FAFB", padding=10, border_radius=10, border=ft.border.all(1, "#E5E7EB"), width=600
            )
            list_ui.controls.append(kotak_alat)
        
        sisa_alat = total_alat - (halaman_sekarang * item_per_halaman)
        baris_tombol_halaman = ft.Row([
            ft.ElevatedButton("⬅️ Prev", disabled=(halaman_sekarang == 1), on_click=lambda _: show_manage_tools_page(halaman_sekarang=halaman_sekarang - 1)),
            ft.Text(f"Halaman {halaman_sekarang}", weight="bold", size=16),
            ft.ElevatedButton("Next ➡️", disabled=not (sisa_alat > 0), on_click=lambda _, h=halaman_sekarang: show_manage_tools_page(halaman_sekarang=h + 1)),
        ], alignment=ft.MainAxisAlignment.CENTER)

        main_card = ft.Container(content=ft.Column([ft.Text("Daftar Alat di Sistem", size=24, weight="bold", color=TEXT_COLOR), ft.Container(height=10), list_ui, ft.Container(height=10), baris_tombol_halaman], horizontal_alignment="center"), width=700, bgcolor="white", padding=30, border_radius=20, shadow=ft.BoxShadow(blur_radius=20, color=SHADOW_COLOR))
        
        # PROSES BUNGKUS DARI PABRIK (ui_komponen.py)
        tampilan = build_standard_layout(ft.Column([main_card], horizontal_alignment="center", alignment="center"), back_func=show_edit_tools_menu)
        page.add(tampilan)

    def show_history_page(e=None):
        page.clean()
        try:
            with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(str(row[0]), color="black")), ft.DataCell(ft.Text(str(row[1]), weight="bold", color="black")), ft.DataCell(ft.Text(str(row[2]) if len(row)>2 and row[2] else "-", color="gray")), ft.DataCell(ft.Container(content=ft.Text(str(row[3]).upper(), color="white", weight="bold", size=12), bgcolor="#EF4444" if str(row[3]).upper()=="PINJAM" else "#10B981", padding=ft.padding.symmetric(horizontal=12, vertical=6), border_radius=15, alignment=ft.Alignment(0,0)))]) for row in conn.cursor().execute("SELECT nama_user, nama_alat, waktu, status FROM log_peminjaman ORDER BY id DESC LIMIT 15").fetchall()]
            table = ft.DataTable(columns=[ft.DataColumn(ft.Text("User", weight="bold", color="black")), ft.DataColumn(ft.Text("Alat", weight="bold", color="black")), ft.DataColumn(ft.Text("Waktu", weight="bold", color="black")), ft.DataColumn(ft.Text("Status", weight="bold", color="black"))], rows=rows, border=ft.border.all(1, "#E5E7EB"), border_radius=10, heading_row_color="#F3F4F6", vertical_lines=ft.border.BorderSide(1, "#F3F4F6"), horizontal_lines=ft.border.BorderSide(1, "#F3F4F6"), column_spacing=30)
            page.add(build_standard_layout(ft.Column([ft.Container(content=ft.Column([table], scroll=ft.ScrollMode.ALWAYS, height=350, horizontal_alignment="center"), bgcolor="white", padding=20, border_radius=15, shadow=ft.BoxShadow(blur_radius=20, color=SHADOW_COLOR))], horizontal_alignment="center", alignment="center"), back_func=show_admin_dashboard))
        except Exception as e: 
            print("Ada error di Database Riwayat:", e)

    # ==========================================================================
    # --- HALAMAN TAMBAH ALAT (UI ADMIN) ---
    # ==========================================================================
    def show_add_tool_page(e=None):
        page.clean()

        # 1. SIAPKAN VARIABEL PENYIMPAN STATE
        path_gambar_baru = ["tambah.png"]  
        current_path = [os.path.expanduser("~")]
        sedang_scan = [False]

        # 2. KOMPONEN PREVIEW GAMBAR
        preview_img = ft.Container(
            content=ft.Image(src=f"/{path_gambar_baru[0]}", width=120, height=120, fit="contain"),
            width=120, height=120
        )

        # 3. KOMPONEN FILE BROWSER (Belum di-add ke overlay)
        dialog_tambah_browser = ft.AlertDialog(
            title=ft.Text("Pilih Gambar", weight="bold", color="black"),
            bgcolor="white"
        )
        
        file_list_view = ft.ListView(height=300, spacing=5)
        path_text = ft.Text(current_path[0], weight="bold", size=14, color="blue", expand=True)

        # 4. FUNGSI PENDUKUNG BROWSER
        def navigate_browser(new_path):
            current_path[0] = new_path
            update_browser_ui()

        tombol_drive = ft.Row([
            path_text,
            ft.ElevatedButton("💻 Drive C:", bgcolor=BG_COLOR, color=TEXT_COLOR, on_click=lambda _: navigate_browser("c:\\")),
            ft.ElevatedButton("💻 Drive D:", bgcolor=BG_COLOR, color=TEXT_COLOR, on_click=lambda _: navigate_browser("D:\\"))
        ])

        def update_browser_ui():
            file_list_view.controls.clear()
            path_text.value = f"Lokasi: {current_path[0]}"

            parent_dir = os.path.dirname(current_path[0])
            if parent_dir != current_path[0]:
                file_list_view.controls.append(
                    ft.TextButton("⬆️.. (Kembali)", icon_color="#3B82F6",
                                  style=ft.ButtonStyle(color="black", alignment=ft.Alignment(-1, 0)),
                                  width=580, on_click=lambda _, p=parent_dir: navigate_browser(p))
                )
            try:
                items = os.listdir(current_path[0])
                dirs, files = [], []
                for item in items:
                    full_path = os.path.join(current_path[0], item)
                    if os.path.isdir(full_path):
                        dirs.append(item)
                    elif item.lower().endswith(('.png', '.jpg', '.jpeg')):
                        files.append(item)
                dirs.sort(); files.sort()

                for d in dirs:
                    file_list_view.controls.append(
                        ft.TextButton(f"📁{d}",
                                      style=ft.ButtonStyle(color="black", alignment=ft.Alignment(-1, 0)),
                                      width=580, on_click=lambda _, p=os.path.join(current_path[0], d): navigate_browser(p))
                    )
                for f in files:
                    full_path = os.path.join(current_path[0], f)
                    thumb_name = f"_thumb_{f}"
                    thumb_path = os.path.join("assets", thumb_name)
                    try: 
                        #buka gambar aslinya 
                        pil_img = PILImage.open(full_path)
                        #kecilkan jadi ukuran icon (35x35) 
                        pil_img.thumbnail((35, 35))
                        #simpan di folder assets 
                        pil_img.save(thumb_path, format="PNG")
                    except: 
                        #Kalau gagal kosongkan namanya 
                        thumb_name = None 
                    
                    if thumb_name:
                        thumb = ft.Image(src=f"/{thumb_name}", width=35, height=35, fit="contain")
                    else: 
                        thumb = ft.Text("🖼️", size=16)

                    file_list_view.controls.append(
                        ft.Row([
                            thumb,
                            ft.TextButton(f, style=ft.ButtonStyle(color="black", alignment=ft.Alignment(-1, 0)),
                                          width=530, on_click=lambda _, p=full_path: pilih_gambar(p))
                        ], alignment="start", vertical_alignment="center", height=45)
                    )
            except Exception as err:
                file_list_view.controls.append(ft.Text(f"Akses ditolak: {err}", color="red"))
            page.update()

        def pilih_gambar(filepath):
            nama_asli = os.path.basename(filepath)
            nama_baru = f"tool_{int(time.time())}_{nama_asli}"
            lokasi_simpan = os.path.join("assets", nama_baru)
            try:
                shutil.copy(filepath, lokasi_simpan)
                path_gambar_baru[0] = nama_baru
                preview_img.content = ft.Image(src=f"/{nama_baru}", width=120, height=120, fit="contain")
                dialog_tambah_browser.open = False
                page.update()
            except Exception:
                pass

        dialog_tambah_browser.content = ft.Column([tombol_drive, ft.Divider(), file_list_view], width=600, tight=True)
        dialog_tambah_browser.actions = [
            ft.TextButton("Batal & Tutup", style=ft.ButtonStyle(color="black"), on_click=lambda _: tutup_browser_tambah())
        ]

        def buka_browser_tambah(e):
            update_browser_ui()
            dialog_tambah_browser.open = True
            page.update()

        def tutup_browser_tambah():
            dialog_tambah_browser.open = False
            page.update()

        #====================
        #Fungsi Rotasi Gambar
        #==================== 
        def putar_gambar_tambah(e):
            file_sekarang = path_gambar_baru[0]

            #Jangan putar icon bawaan 
            if file_sekarang == "tambah.png":
                notif_text.value = "❌ Pilih Gambar Terlebih Dahulu"
                page.update()
                return
            
            lokasi_file = f"assets/{file_sekarang}"
            try: 
                with PILImage.open(lokasi_file) as img: 
                    #cek tombol mana yang di klik 
                    if e.control.icon == "kiri":
                        img_rotated = img.rotate(90, expand=True)
                    else: 
                        img_rotated = img.rotate(-90, expand=True)

                    #simpan sebagai file baru 
                    file_baru =f"tool_{int(time.time())}_{random.randint(100,999)}.png"
                    img_rotated.save(f"assets/{file_baru}")

            #update tampilan di layar 
                preview_img.content = ft.image(src=f"/{file_baru}", width=120, height=120, fit="contain")
                path_gambar_baru[0] = file_baru 
                page.update()
            except Exception as err:
                print(f"Error rotasi:{err}")

        # 5. INPUT FIELD FORM
        input_nama   = ft.TextField(label="Nama Alat", width=350, border_color=BLUE_SENSOR, border_radius=10, color=TEXT_COLOR)
        input_rfid   = ft.TextField(label="UID Tag RFID", width=200, border_color=BLUE_SENSOR, border_radius=10, read_only=True, color=TEXT_COLOR)
        
        dd_laci = ft.Dropdown(
            label="Lokasi Laci (page)", width=350, border_color=BLUE_SENSOR, border_radius=10, color=TEXT_COLOR,
            options=[ft.dropdown.Option("1", "Laci 1"), ft.dropdown.Option("2", "Laci 2")]
        )

        dd_pin = ft.Dropdown(
            label="Posisi Pin Sensor (mqtt_topic)", width=350, border_color=BLUE_SENSOR, border_radius=10, color=TEXT_COLOR,
            options=[ft.dropdown.Option(f"P{str(i).zfill(2)}") for i in range(16)]
        )

        notif_text = ft.Text("", color="red", size=14, weight="bold")

        #--- Memunculkan Pop Up untuk scan RFID ketika tombol Scan Tag ditekan ---
        input_popup_scan = ft.TextField(label="Tempelkan Tag RFID...", width=300, border_color=BLUE_SENSOR, color="black", autofocus=True)

        def proses_popup_scan(e):
            uid = str(input_popup_scan.value).strip()
            if uid:
                #pindahkan hasilnya ke kotak RFID Utama
                input_rfid.value = uid
                input_rfid.border_color = "#10B981" #menjadi hijau kalau sukses
                dialog_scan.open = False #pop up di tutup 
                page.update()

        input_popup_scan.on_submit = proses_popup_scan

        #desain pop-up scan rfid pada mode scan 
        dialog_scan= ft.AlertDialog(
            title=ft.Text("Scan Tag RFID", weight="bold", color="white"),
            content=ft.Column([
                ft.Text("Kursor sudah otomatis aktif dibawah ini. \nSilakan scan tag atau ketik manual lalu Enter", color="grey"),
                ft.Container(height=10),
                input_popup_scan
            ], tight=True),
            actions=[ft.TextButton("Cancel", style=ft.ButtonStyle(color="red"), on_click=lambda _:tutup_dialog_scan())]
        )

        #Daftarkan pop up ke halaman agar bisa dipanggil
        page.overlay.append(dialog_scan)
        
        def tutup_dialog_scan():
            dialog_scan.open = False
            page.update()

        def mulai_scan_rfid(e):
            input_popup_scan.value = "" 
            dialog_scan.open = True
            page.update()

            import threading
            threading.Thread(target=lambda:[time.sleep(0.5), input_rfid.focus(), page.update()]).start()
            
        def proses_rfid(e):
            uid = str(e.control.value).strip()
            if uid:
                input_rfid.border_color = "#10B981"
                page.update()

        input_rfid.on_submit = proses_rfid

        def simpan_alat_baru(e):
            if not input_nama.value.strip(): notif_text.value = "❌ Nama alat tidak boleh kosong!"; page.update(); return
            if not input_rfid.value.strip(): notif_text.value = "❌ Harap scan Tag RFID terlebih dahulu!"; page.update(); return
            if not dd_laci.value: notif_text.value = "❌ Pilih lokasi laci!"; page.update(); return
            if not dd_pin.value: notif_text.value = "❌ Pilih posisi pin sensor!"; page.update(); return
        
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    conn.execute(
                        "INSERT INTO tools (name, rfid_tag_uid, img, total, page, mqtt_topic, rot) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (input_nama.value.strip(), input_rfid.value.strip(), path_gambar_baru[0], 1, int(dd_laci.value), dd_pin.value, 0)
                    )
                    conn.commit()
                notif_text.value = "✅ Alat berhasil ditambahkan!"
                notif_text.color = "#10B981"
                page.update()
                time.sleep(1.0)
                show_edit_tools_menu() 
            except sqlite3.IntegrityError:
                notif_text.value = "❌ Nama alat sudah ada di database!"; page.update()
            except Exception as err:
                notif_text.value = f"❌ Gagal menyimpan: {err}"; page.update()

        # 6. SUSUN TAMPILAN FORM KARTU
        kolom_kiri = ft.Column([
            dd_laci,
            dd_pin,
            ft.Row([
                input_rfid,
                ft.ElevatedButton("Scan Tag 💳", style=ft.ButtonStyle(bgcolor="#E3F2FD", color=BLUE_SENSOR), on_click=mulai_scan_rfid)
            ], spacing=10),
        ], spacing=15)

        kolom_kanan = ft.Column([
            input_nama,
            ft.Container(height=10),
            ft.Column([
                ft.Row([
                    ft.ElevatedButton("↺ Putar Kiri", data="kiri", on_click=putar_gambar_tambah, color=BLUE_SENSOR, bgcolor="#E3F2FD"),
                    ft.ElevatedButton("Putar Kanan ↻", data="kanan", on_click=putar_gambar_tambah, color=BLUE_SENSOR, bgcolor="#E3F2FD")], alignment="center", spacing=20),
                preview_img,
                ft.ElevatedButton("📁 Pilih Gambar", icon="folder_open", bgcolor="#E3F2FD", color="blue", on_click=buka_browser_tambah)
                ],horizontal_alignment="center", spacing=15)
        ], spacing=15)

        #Kartu utama yang menampung kiri dan kanan 
        form_card = ft.Container(
            content=ft.Column([
                ft.Text("Mendaftarkan Alat Baru", size=24, weight="bold", color=TEXT_COLOR),
                ft.Divider(color="#E5E7EB"), #garis titpis untuk pemisah 
                #Menjajarkan kolom kiri dan kanan secara horizontal
                ft.Row([
                    kolom_kiri, kolom_kanan], alignment="center", vertical_alignment="start", spacing=40),
                notif_text,
                create_filled_button("Simpan Data Alat", GREEN_SENSOR, simpan_alat_baru, width=750, height=45)
            ], horizontal_alignment="center", spacing=10),
            width=850, bgcolor="white", padding=25, border_radius=20,
            shadow=ft.BoxShadow(blur_radius=20, color=SHADOW_COLOR)
        )

        # 7. EKSEKUSI PENAMPILAN KE LAYAR (Ini mencegah layar blank)
        page.overlay.append(dialog_tambah_browser)
        page.add(build_standard_layout(
            ft.Column([form_card], horizontal_alignment="center", alignment="center"),
            back_func=show_edit_tools_menu
        ))

    def show_admin_dashboard(e=None):
        page.clean()
        page.add(build_standard_layout(ft.Column([ft.Text("Admin Dashboard", size=36, weight="bold", color=TEXT_COLOR), ft.Container(height=30), ft.Row([create_menu_card("Cek History", "Riwayat", "history.png", "#F3E5F5", lambda _: show_history_page()), create_menu_card("Edit Tools", "Stok", "build.png", "#FFF3E0", lambda _: show_edit_tools_menu())], alignment="center", spacing=30), ft.Container(height=30), create_filled_button("Logout", "#F44336", lambda _: show_home(), width=300, height=50)], horizontal_alignment="center", alignment="center")))  
    
    def show_login_admin(e=None, tujuan=None):
        page.clean()

        if tujuan is None: 
            tujuan = show_admin_dashboard 

        username_field = ft.TextField(width=340, hint_text="Masukkan username", color="black", filled=True, bgcolor="#F3F4F6", border_radius=8, content_padding=15, border_color="transparent")
        password_field = ft.TextField(width=340, hint_text="Masukkan password", color="black", password=True, can_reveal_password=True, filled=True, bgcolor="#F3F4F6", border_radius=8, content_padding=15, border_color="transparent")

        #label teks error 
        teks_error = ft.Text("", color="red", size=14, weight="bold")
        def do_login(e):
            teks_error.value = ""
            page.update()
            
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    if conn.cursor().execute("SELECT * FROM admins WHERE username = ? AND password = ?", (username_field.value, password_field.value)).fetchone(): tujuan()
                    else: 
                        teks_error.value = "❌ Username atau password salah!"
                        page.update()
            except Exception as err: 
                print(f"ERROR SAAT LOGIN: {err}")
                page.update()
        login_btn = create_filled_button("Login", "#1F2937", do_login, width=340, height=50)
        page.add(build_standard_layout(ft.Column([ft.Container(content=ft.Column([ft.Container(content=ft.Image(src="/login.png", width=60, height=60), bgcolor="#E3F2FD", padding=20, border_radius=50), ft.Text("Admin Login", size=24, weight="bold", color=TEXT_COLOR), ft.Container(height=5), ft.Column([ft.Text("Username", weight="bold", color="black"), username_field, ft.Text("Password", weight="bold", color="black"), password_field, teks_error], spacing=5), ft.Container(height=10), login_btn], horizontal_alignment="center", spacing=15), width=450, bgcolor="white", padding=40, border_radius=20, shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR), alignment=ft.Alignment(0, 0))], horizontal_alignment="center", alignment="center"), back_func=show_home))

    # ==========================================================================
    # --- HALAMAN USER (UI USER) ---
    # ==========================================================================
    def show_all_done_kembali():
        page.clean()
        success_card = ft.Container(content=ft.Column([ft.Text("🎉", size=80), ft.Text("Pengembalian Berhasil!", size=28, weight="bold", color="#3B82F6"), ft.Text("Semua alat telah masuk ke dalam laci.", size=16, color="black"), ft.Container(height=10), ft.ProgressRing(width=25, height=25, color="#3B82F6", stroke_width=3), ft.Text("Menutup sesi otomatis...", size=12, color="grey")], alignment="center", horizontal_alignment="center", spacing=5), width=450, padding=40, bgcolor="white", border_radius=20, shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR), alignment=ft.Alignment(0,0))
        page.add(build_standard_layout(ft.Container(content=success_card, alignment=ft.Alignment(0,0))))
        async def auto(): await asyncio.sleep(4.0); show_home()
        page.run_task(auto)

    def show_all_done(tool_name):
        page.clean()
        success_card = ft.Container(content=ft.Column([ft.Text("✅", size=80), ft.Text("Peminjaman Sukses!", size=28, weight="bold", color=GREEN_SENSOR), ft.Text(f"Alat {tool_name} berhasil dipinjam.", size=16, color="black"), ft.Container(height=10), ft.ProgressRing(width=25, height=25, color=GREEN_SENSOR, stroke_width=3), ft.Text("Kembali ke layar utama...", size=12, color="grey")], alignment="center", horizontal_alignment="center", spacing=5), width=450, padding=40, bgcolor="white", border_radius=20, shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR), alignment=ft.Alignment(0,0))
        page.add(build_standard_layout(ft.Container(content=success_card, alignment=ft.Alignment(0,0))))
        async def auto(): await asyncio.sleep(4.0); show_home()
        page.run_task(auto)

    def show_visual_sensor_kembali(scanned_tools, index):
        if index >= len(scanned_tools): show_all_done_kembali(); return
        page.clean()
        current_tool = scanned_tools[index]
        indicator = ft.Container(content=ft.Text("📥", size=50), width=120, height=120, bgcolor="orange", border_radius=60, alignment=ft.Alignment(0, 0), animate=300)
        sensor_box = ft.Container(content=indicator, width=800, height=350, bgcolor="#FFF3E0", border_radius=20, alignment=ft.Alignment(0, 0), shadow=ft.BoxShadow(blur_radius=15, color=SHADOW_COLOR), animate=300)
        status_txt = ft.Text(f"MENUNGGU SENSOR IR...\nSilakan taruh {current_tool} ke posisinya ({index+1}/{len(scanned_tools)})", size=18, color="black", weight="bold", text_align="center")
        
        async def pantau_sensor_ditaruh():
            while status_sensor_realtime.get(current_tool, 0) == 0: await asyncio.sleep(0.5) 
            indicator.bgcolor = GREEN_SENSOR; sensor_box.bgcolor = "#E8F5E9"
            status_txt.value = f"{current_tool} Berhasil Ditaruh!"; status_txt.color = GREEN_SENSOR; page.update()
            simpan_log_pengembalian(session_data["user_now"], current_tool)
            await asyncio.sleep(2.0); show_visual_sensor_kembali(scanned_tools, index + 1)
            
        page.add(build_standard_layout(ft.Column([sensor_box, ft.Container(height=10), status_txt], alignment="center", horizontal_alignment="center")))
        page.run_task(pantau_sensor_ditaruh)

    def show_konfirmasi_kembali(scanned_tools):
        page.clean()
        list_ui = ft.Column([ft.Text(f"📦 {t}", size=18, color="black", weight="bold") for t in scanned_tools], scroll=ft.ScrollMode.AUTO)
        content = ft.Column([ft.Text("Yakin kembalikan alat berikut?", size=24, weight="bold", color="black"), ft.Container(height=10), ft.Container(content=list_ui, height=200), ft.Container(height=20), create_filled_button("Lanjut Buka Laci", "green", lambda _: show_visual_sensor_kembali(scanned_tools, 0), width=400, height=50)], horizontal_alignment="center", alignment="center")
        page.add(build_standard_layout(content, back_func=lambda _: show_scan_kembali(get_borrowed_tools(session_data["user_now"]))))

    def show_scan_kembali(borrowed_tools):
        page.clean()
        scanned_items = []
        input_tag = ft.TextField(autofocus=True, width=1, height=1, border=ft.InputBorder.NONE, color="transparent", bgcolor="transparent", cursor_color="transparent", on_blur=lambda e: input_tag.focus())
        status_text = ft.Text("Siap Membaca Tag...", size=16, color=BLUE_SENSOR, weight="bold")
        scanned_list_ui = ft.ListView(spacing=10, height=180)
        btn_confirm = create_filled_button("Selesai & Konfirmasi", "#10B981", lambda _: show_konfirmasi_kembali(scanned_items), width=600, height=50, disabled=True)
        
        def update_ui():
            scanned_list_ui.controls.clear()
            for item in scanned_items: scanned_list_ui.controls.append(ft.Container(content=ft.Row([ft.Text("✅", size=18), ft.Text(item, weight="bold", color=TEXT_COLOR, expand=True), ft.Container(content=ft.Text("Terverifikasi", size=10, color="white"), bgcolor="#10B981", padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=10)]), bgcolor="#F0FDF4", padding=15, border_radius=10, border=ft.border.all(1, "#BBF7D0"), width=580))
            btn_confirm.disabled = len(scanned_items) == 0; page.update()
            
        def proses_scan(e):
            uid_tag = str(e.control.value).strip(); e.control.value = ""; page.update()
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    res = conn.cursor().execute("SELECT name FROM tools WHERE TRIM(CAST(rfid_tag_uid AS TEXT)) = ?", (uid_tag,)).fetchone()
                if res:
                    if res[0] in borrowed_tools:
                        if res[0] not in scanned_items: scanned_items.append(res[0]); status_text.value = f"Berhasil: {res[0]}"; status_text.color = "#10B981"; update_ui()
                        else: status_text.value = f"Sudah di-scan: {res[0]}"; status_text.color = "orange"
                    else: status_text.value = f"Bukan pinjaman Anda: {res[0]}"; status_text.color = "red"
                else: status_text.value = "Tag Tidak Dikenal!"; status_text.color = "red"
            except: pass
            page.update(); input_tag.focus()
            
        input_tag.on_submit = proses_scan
        top_card = ft.Container(content=ft.Row([ft.Container(content=ft.Image(src="/scanrfid.png", width=60, height=60), padding=10, bgcolor="#EFF6FF", border_radius=15), ft.Column([ft.Text("Area Scan Aktif", size=20, weight="bold", color=TEXT_COLOR), status_text], spacing=2)], alignment="center", spacing=20), bgcolor="white", padding=20, border_radius=15, width=600, border=ft.border.all(2, BLUE_SENSOR), shadow=ft.BoxShadow(blur_radius=15, color=SHADOW_COLOR), on_click=lambda _: input_tag.focus())
        content = ft.Column([top_card, ft.Container(height=10), ft.Text("Alat Terverifikasi:", weight="bold", color="grey"), ft.Container(content=scanned_list_ui, height=180), btn_confirm, input_tag], horizontal_alignment="center", alignment="center")
        page.add(build_standard_layout(content, back_func=show_list_pinjaman_user))
        import threading; threading.Thread(target=lambda: [time.sleep(0.5), input_tag.focus(), page.update()]).start()

    def show_list_pinjaman_user():
        page.clean()
        
        # Opeper Data ke File Pembantu (db_manager.py)
        borrowed = get_borrowed_tools(session_data["user_now"])
        
        state = {"page": 0}
        items_per_page = 4
        list_container = ft.Column(spacing=10, horizontal_alignment="center") 
        
        def update_list():
            list_container.controls.clear()
            start_idx = state["page"] * items_per_page
            end_idx = start_idx + items_per_page
            current_items = borrowed[start_idx:end_idx]
            if not borrowed: list_container.controls.append(ft.Container(content=ft.Text("Tidak ada alat yang dipinjam.", color="red", size=16, weight="bold", text_align="center"), alignment=ft.Alignment(0, 0), height=150))
            else:
                for i, alat in enumerate(current_items): 
                    list_container.controls.append(ft.Container(content=ft.Row([ft.Container(content=ft.Text(str(start_idx + i + 1), color="white", weight="bold"), bgcolor="#3B82F6", width=30, height=30, border_radius=15, alignment=ft.Alignment(0,0)), ft.Text(alat, size=16, weight="bold", color="black", expand=True), ft.Container(content=ft.Text("Qty: 1", color="white", size=12, weight="bold"), bgcolor="#111827", padding=ft.padding.symmetric(horizontal=12, vertical=6), border_radius=15)]), bgcolor="#F3F4F6", padding=10, border_radius=10, width=450))
            btn_prev.disabled = state["page"] == 0; btn_next_page.disabled = end_idx >= len(borrowed); page.update()
            
        def change_page(delta): state["page"] += delta; update_list()
        btn_prev = ft.ElevatedButton("< Prev", on_click=lambda e: change_page(-1), disabled=True, color="black", bgcolor="#E2E8F0")
        btn_next_page = ft.ElevatedButton("Next >", on_click=lambda e: change_page(1), disabled=True, color="black", bgcolor="#E2E8F0")
        btn_action = create_filled_button("Lanjut scan alat", "#1F2937", lambda _: show_scan_kembali(borrowed) if borrowed else None, width=450, height=50, disabled=not bool(borrowed))
        main_card = ft.Container(content=ft.Column([ft.Text("Daftar Alat yang Dipinjam", size=24, weight="bold", color="black"), ft.Container(height=15), ft.Container(content=list_container, height=240, alignment=ft.Alignment(0,-1)), ft.Row([btn_prev, btn_next_page], alignment="center", spacing=20), ft.Container(height=10), btn_action], horizontal_alignment="center", alignment="center"), width=600, bgcolor="white", padding=30, border_radius=20, shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR), alignment=ft.Alignment(0, 0))
        update_list()
        page.add(build_standard_layout(ft.Column([main_card], horizontal_alignment="center", alignment="center"), back_func=show_menu_user))

    def show_scan_tag_alat(tool_name):
        page.clean()
        state = {"aktif": True}
        input_tag = ft.TextField(autofocus=True, width=1, height=1, border=ft.InputBorder.NONE, color="transparent", bgcolor="transparent", cursor_color="transparent", on_blur=lambda e: input_tag.focus() if state.get("aktif") else None)
        def keluar_halaman(tujuan_func): state["aktif"] = False; input_tag.disabled = True; page.update(); tujuan_func()
        
        def proses_scan_tag(e):
            if not state["aktif"]: return
            uid_tag = str(e.control.value).strip(); input_tag.disabled = True
            visual_card.border = ft.border.all(3, "#F59E0B"); status_text.value = "Mencocokkan Data..."; status_text.color = "#F59E0B"; page.update()
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    tag_data = conn.cursor().execute("SELECT name FROM tools WHERE TRIM(CAST(rfid_tag_uid AS TEXT)) = ?", (uid_tag,)).fetchone()
                if tag_data:
                    nama_di_db = tag_data[0]
                    if nama_di_db.lower() == tool_name.lower():
                        state["aktif"] = False; visual_card.border = ft.border.all(3, GREEN_SENSOR); status_text.value = "Verifikasi Sukses!"; status_text.color = GREEN_SENSOR; page.update(); 
                        
                        # Simpan ke log db_manager
                        simpan_log(session_data["user_now"], nama_di_db, "PINJAM"); 
                        
                        time.sleep(0.5); keluar_halaman(lambda: show_all_done(nama_di_db))
                    else:
                        visual_card.border = ft.border.all(3, "red"); status_text.value = f"SALAH ALAT!\nTerdeteksi: {nama_di_db}"; status_text.color = "red"; page.update(); time.sleep(1.5); visual_card.border = ft.border.all(2, BLUE_SENSOR); status_text.value = f"Scan Tag RFID pada {tool_name}"; status_text.color = SUB_TEXT_COLOR; e.control.value = ""; input_tag.disabled = False; e.control.focus(); page.update()
                else:
                    visual_card.border = ft.border.all(3, "red"); status_text.value = "Tag Tidak Dikenal!"; status_text.color = "red"; page.update(); time.sleep(1.5); visual_card.border = ft.border.all(2, BLUE_SENSOR); status_text.value = f"Scan Tag RFID pada {tool_name}"; status_text.color = SUB_TEXT_COLOR; e.control.value = ""; input_tag.disabled = False; e.control.focus(); page.update()
            except: pass
            
        input_tag.on_submit = proses_scan_tag
        async def bom_waktu_tag():
            await asyncio.sleep(10.0) 
            if state["aktif"]: state["aktif"] = False; visual_card.border = ft.border.all(3, "orange"); status_text.value = "Waktu Habis! Transaksi Batal."; status_text.color = "orange"; page.update(); await asyncio.sleep(1.0); keluar_halaman(show_home)
            
        status_text = ft.Text(f"Scan Tag RFID pada {tool_name}", size=16, color=SUB_TEXT_COLOR, text_align="center")
        visual_card = ft.Container(content=ft.Column([ft.Container(content=ft.Image(src="/scanrfid.png", width=120, height=120), padding=20, bgcolor="#F8FAFC", border_radius=60), ft.Text("Verifikasi Alat", size=24, weight="bold", color=TEXT_COLOR), status_text, ft.Container(height=10), ft.ProgressRing(width=25, height=25, color=BLUE_SENSOR, stroke_width=3)], horizontal_alignment="center", alignment="center"), width=450, padding=40, bgcolor="white", border_radius=20, border=ft.border.all(2, BLUE_SENSOR), shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR), on_click=lambda _: input_tag.focus() if state["aktif"] else None)
        page.add(build_standard_layout(ft.Column([visual_card, input_tag], horizontal_alignment="center", alignment="center"), back_func=lambda e: keluar_halaman(show_home)))
        import threading; threading.Thread(target=lambda: [time.sleep(0.5), input_tag.focus(), page.update()]).start()
        page.run_task(bom_waktu_tag)

    def show_visual_sensor_flow(tool_name, slot_num):
        page.clean()
        indicator_circle = ft.Container(content=ft.Text(str(slot_num), size=60, weight="bold", color="white"), width=120, height=120, bgcolor=BLUE_SENSOR, border_radius=60, alignment=ft.Alignment(0, 0), animate=300)
        sensor_box = ft.Container(content=indicator_circle, width=800, height=350, bgcolor="#EBF3FF", border_radius=20, alignment=ft.Alignment(0, 0), shadow=ft.BoxShadow(blur_radius=15, color=SHADOW_COLOR), animate=300)
        status_txt = ft.Text("MENUNGGU SENSOR IR...\nSilakan ambil barang di laci...", size=18, color=SUB_TEXT_COLOR, text_align="center")
        
        async def pantau_sensor_diambil():
            while status_sensor_realtime.get(tool_name, 1) == 1: await asyncio.sleep(0.5)
            indicator_circle.bgcolor = GREEN_SENSOR; sensor_box.bgcolor = "#E8F5E9"; status_txt.value = "Barang Terdeteksi Diambil!"; status_txt.color = GREEN_SENSOR; page.update(); await asyncio.sleep(1.5); show_scan_tag_alat(tool_name)
            
        page.add(build_standard_layout(ft.Column([sensor_box, ft.Container(height=10), status_txt], alignment="center", horizontal_alignment="center")))
        page.run_task(pantau_sensor_diambil)

    def show_position_selection(name, data):
        page.clean()
        pos_grid = ft.GridView(expand=True, max_extent=70, spacing=10)
        for i in range(1, 2): pos_grid.controls.append(ft.Container(content=ft.Text(str(i), weight="bold", color=TEXT_COLOR), alignment=ft.Alignment(0, 0), bgcolor="white", border=ft.border.all(2, "#4CAF50"), border_radius=10, on_click=lambda e, idx=i: show_visual_sensor_flow(name, idx)))
        page.add(build_standard_layout(ft.Column([ft.Text(f"Posisi {name}", size=32, weight="bold", color=TEXT_COLOR), ft.Container(height=20), ft.Container(content=pos_grid, height=300, width=600)], horizontal_alignment="center", alignment="center"), back_func=show_peminjaman_page1))

    # --- PABRIK KOMPONEN: create_tool_grid_item digunakan di sini! ---
    def show_peminjaman_page1(e=None):
        page.clean()
        grid = ft.GridView(expand=True, runs_count=5, max_extent=180, child_aspect_ratio=0.85, spacing=20, run_spacing=20, padding=10)
        
        # Panggil data aslinya pakai db_manager
        alat_laci_1 = get_tools_from_db(1)
        for item in alat_laci_1: 
            grid.controls.append(create_tool_grid_item(item, show_position_selection))
            
        page.add(build_standard_layout(grid, back_func=show_menu_user, title_text="Pilih Alat Laci 1", action_button=create_filled_button("Laci 2", "#1F2937", lambda _: show_peminjaman_page2(), width=100)))

    def show_peminjaman_page2(e=None):
        page.clean()
        grid = ft.GridView(expand=True, runs_count=5, max_extent=180, child_aspect_ratio=0.85, spacing=20, run_spacing=20, padding=10)
        
        alat_laci_2 = get_tools_from_db(2)
        for item in alat_laci_2: 
            grid.controls.append(create_tool_grid_item(item, show_position_selection))
            
        page.add(build_standard_layout(grid, back_func=show_menu_user, title_text="Pilih Alat Laci 2", action_button=create_filled_button("Laci 1", "#1F2937", lambda _: show_peminjaman_page1(), width=100)))

    def show_rfid_page(title_text, next_destination_func, back_destination_func, tipe_akses="user"):
        page.clean()
        state = {"aktif": True}
        input_rfid = ft.TextField(autofocus=True, width=1, height=1, border=ft.InputBorder.NONE, color="transparent", bgcolor="transparent", cursor_color="transparent", on_blur=lambda e: input_rfid.focus() if state.get("aktif") else None)
        def keluar_halaman(tujuan_func): state["aktif"] = False; input_rfid.disabled = True; page.update(); tujuan_func() 
        
        async def proses_scan_usb(e, simu_uid=None):
            if not state["aktif"]: return 
            state["aktif"] = False; uid_kartu = simu_uid if simu_uid else str(e.control.value).strip(); input_rfid.disabled = True
            visual_card.border = ft.border.all(3, "#F59E0B"); status_text.value = "Memeriksa ID..."; status_text.color = "#F59E0B"; page.update()
            try:
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    if tipe_akses == "admin": user_data = conn.cursor().execute("SELECT username FROM admins WHERE CAST(rfid_card_uid AS TEXT) = ?", (uid_kartu,)).fetchone()
                    else: user_data = conn.cursor().execute("SELECT nama FROM users WHERE CAST(rfid_card_uid AS TEXT) = ?", (uid_kartu,)).fetchone()
                if user_data:
                    nama_user = user_data[0]; session_data["user_now"] = nama_user 
                    visual_card.border = ft.border.all(3, GREEN_SENSOR); status_text.value = f"Akses Diberikan!\nHalo {nama_user}"; status_text.color = GREEN_SENSOR; page.update(); await asyncio.sleep(0.5); keluar_halaman(next_destination_func) 
                else:
                    visual_card.border = ft.border.all(3, "red"); status_text.value = "Akses Ditolak!\nKartu tidak sesuai hak akses."; status_text.color = "red"; page.update(); await asyncio.sleep(2.0); keluar_halaman(back_destination_func) 
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
            if state["aktif"]: state["aktif"] = False; status_text.value = "Waktu Habis!"; status_text.color = "orange"; page.update(); await asyncio.sleep(0.5); keluar_halaman(back_destination_func) 

        status_text = ft.Text("Silakan tempelkan ID Card Anda", size=16, color=SUB_TEXT_COLOR, text_align="center")
        visual_card = ft.Container(content=ft.Column([ft.Container(content=ft.Image(src="/scanrfid.png", width=120, height=120), padding=20, bgcolor="#F8FAFC", border_radius=60), ft.Text(title_text, size=24, weight="bold", color=TEXT_COLOR), status_text, ft.Container(height=10), ft.ProgressRing(width=25, height=25, color=BLUE_SENSOR, stroke_width=3), 
                                                      ft.Row([create_filled_button("Simulasi Admin", "blue", lambda kejadian_klik: page.run_task(proses_scan_usb, kejadian_klik, simu_uid="3676831940")), 
                                                              create_filled_button("Simulasi User", "green", lambda kejadian_klik:page.run_task (proses_scan_usb, kejadian_klik, simu_uid="2344461204"))], alignment="center", spacing=10)], horizontal_alignment="center", alignment="center"), width=450, padding=40, bgcolor="white", border_radius=20, border=ft.border.all(2, BLUE_SENSOR), shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR), on_click=lambda _: input_rfid.focus() if state["aktif"] else None)
        page.add(build_standard_layout(ft.Column([visual_card, input_rfid], horizontal_alignment="center", alignment="center"), back_func=lambda e: keluar_halaman(back_destination_func)))
        import threading; threading.Thread(target=lambda: [time.sleep(0.5), input_rfid.focus(), page.update()]).start()
        page.run_task(bom_waktu)

    def show_menu_user(e=None):
        page.clean()
        page.add(build_standard_layout(ft.Column([ft.Text("Menu User", size=36, weight="bold", color=TEXT_COLOR), ft.Container(height=30), ft.Row([create_menu_card("Peminjaman", "Pinjam alat", "pinjam.png", "#E8F5E9", lambda _: show_rfid_page("Scan Login Peminjaman", show_peminjaman_page1, show_menu_user)), create_menu_card("Pengembalian", "Kembalikan alat", "kembali.png", "#E3F2FD", lambda _: show_rfid_page("Scan Login Pengembalian", show_list_pinjaman_user, show_menu_user))], alignment="center", spacing=40)], horizontal_alignment="center", alignment="center"), back_func=show_home))

    def show_home(e=None):
        # 1. Pastikan overlay benar-benar bersih agar tidak menghalangi klik
        page.overlay.clear()
        page.clean()

        # 2. Fungsi Matikan (Gunakan os._exit agar langsung mati total)
        async def keluar_aplikasi():
            print("1. Menutup layar UI Flet...")
            await page.window.close()
            await asyncio.sleep(0.5) 
            print("2. Mematikan proses python...")
            os._exit(0) 

        # 3. Buat tombol pintu darurat (Gunakan ElevatedButton standar)
        btn_exit = ft.ElevatedButton(
            "MATIKAN SISTEM (EXIT)", 
            bgcolor="red", 
            color="white", 
            icon="power_settings_new",
            icon_color="white", 
            on_click=lambda _: show_login_admin(tujuan=lambda: page.run_task(keluar_aplikasi)),
            width=250,
            height=50,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )

        # 4. Masukkan ke dalam layout UTAMA
        # Pastikan tombol btn_exit ini masuk ke dalam Column daftar controls
        layout = build_standard_layout(
            ft.Column([
                ft.Container(content=ft.Text("Smart Drawer System", size=40, weight="bold", color=TEXT_COLOR), margin=ft.margin.only(top=-10)),
                ft.Row([
                    create_menu_card("Admin", "Kelola sistem", "admin.png", "#E3F2FD", lambda _: show_rfid_page("Scan Kartu Admin", show_login_admin, show_home, "admin")),
                    create_menu_card("User", "Pinjam alat", "user.png", "#E8F5E9", lambda _: show_menu_user())
                ], alignment="center", spacing=40),
                ft.Container(height=30),
                # PASANG TOMBOLNYA DI SINI
                btn_exit 
            ], horizontal_alignment="center", alignment=ft.MainAxisAlignment.START)
        )

        page.add(layout)
        page.update()

    show_home()

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
