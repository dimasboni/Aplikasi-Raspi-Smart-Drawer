import sqlite3
import requests
import threading
import time
from config import settings 

# --- KONFIGURASI API NIKO ---
#ip_server_niko = settings.get("db_host", "10.71.116.208")
#API_URL_NIKO =f"http://{ip_server_niko}/smartdrawer/api_terima.php"

ip_server_niko = settings.get("db_host", "127.0.0.1:8000")
IP_LARAVEL = f"{ip_server_niko}"
URL_CEK_KOIN = f"http://{IP_LARAVEL}/api/v1/cek-koin"
URL_LOG_PINJAM = f"http://{IP_LARAVEL}/api/v1/log-pinjam"

import urllib.parse # <-- Pastikan tambahkan ini di baris paling atas (di bawah import sqlite3)

def cek_koin_user(username):
    """Menembak API Laravel untuk mengecek sisa koin user"""
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn: 
            cursor = conn.cursor()
            cursor.execute("SELECT koin FROM users WHERE nama=?", (username,)) 
            row = cursor.fetchone()
            if row: 
                return row[0]
    except Exception as e:
        print(f"❌ Error API Cek Koin: {e}")
    return 0 

def potong_koin_lokal(username, jumlah=1):
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn: 
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET koin = koin - ? WHERE nama = ?", (jumlah, username))
            conn.commit()
    except Exception as e: 
        print(f"Error potong koin lokal: {e}")

# ==============================================================================
# FUNGSI-FUNGSI DATABASE (SQLITE3)
# Semua transaksi database kumpul di file ini!
# ==============================================================================

def update_stok_otomatis(topik_pin, nomer_laci, jumlah_stok):
    """Mengupdate stok satu alat spesifik di tabel tools berdasarkan posisi pin saat sensor mendeteksi perubahan."""
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            conn.execute("UPDATE tools SET total = ? WHERE mqtt_topic = ? AND page =?", (jumlah_stok, topik_pin, nomer_laci))
            conn.commit()
    except Exception as e:
        print(f"Error update stok sensor: {e}")

def get_tools_from_db(page_number):
    """Mengambil daftar alat berdasarkan halaman (Laci) dan menggabungkan alat yang sama."""
    tools_list = []
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, img, SUM(total), rot FROM tools WHERE page = ? GROUP BY name", (page_number,))
            rows = cursor.fetchall()
            for row in rows:
                tools_list.append({"name": row[0], "img": row[1], "total": row[2], "rot": row[3], "page": page_number})
    except Exception as e: 
        print(f"Error get tools: {e}")
    return tools_list

def get_borrowed_tools(username):
    """Mendapatkan daftar alat yang SEDANG dipinjam oleh user tertentu."""
    borrowed_list = []
    returned = set()
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            cursor = conn.cursor()
            # Cek log dari terbaru ke terlama
            cursor.execute("SELECT nama_alat, status FROM log_peminjaman WHERE nama_user = ? ORDER BY id DESC", (username,))
            for alat, status in cursor.fetchall():
                if status == "KEMBALI": 
                    returned.add(alat)
                elif status == "PINJAM" and alat not in returned:
                    if alat not in borrowed_list:
                        borrowed_list.append(alat)
    except Exception as e: 
        print(f"Error get borrowed tools: {e}")
    borrowed_list.reverse() 
    return borrowed_list

# ==============================================================================
# FUNGSI PENCATATAN LOG & PENGIRIMAN API
# ==============================================================================

def kirim_ke_server_niko(log_id, user_name, tool_name, status):
    """Mengirim log ke server API PHP NIKO menggunakan thread terpisah."""
    def tugas_kirim():
        paket_data = {"nama_user": user_name, "kode_alat": tool_name, "status": status}
        try:
            response = requests.post(URL_LOG_PINJAM, json=paket_data, timeout=10)
            if response.status_code == 200: 
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    conn.execute("UPDATE log_peminjaman SET status_sync = 1 WHERE id = ?", (log_id,))
                    conn.commit()
            # CCTV 2: Cek apa jawaban dari Laravel!
        except Exception as e: 
            pass
    
    threading.Thread(target=tugas_kirim).start()

def simpan_log(user_name, tool_name, status):
    """Mencatat aktivitas PINJAM ke database lokal dan mengirim via API."""
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO log_peminjaman (nama_user, nama_alat, status, status_sync) VALUES (?, ?, ?, 0)", (user_name, tool_name, status))
            log_id = cursor.lastrowid
            conn.commit()
        if status == "PINJAM":
            potong_koin_lokal(user_name)

        kirim_ke_server_niko(log_id, user_name, tool_name, status)
    except Exception as e:
        print(f"Error simpan log: {e}")

def simpan_log_pengembalian(user_name, tool_name):
    """Mencatat aktivitas KEMBALI ke database lokal dan mengirim via API."""
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO log_peminjaman (nama_user, nama_alat, status, status_sync) VALUES (?, ?, ?, 0)", (user_name, tool_name, "KEMBALI"))
            log_id = cursor.lastrowid
            conn.commit()

        kirim_ke_server_niko(log_id, user_name, tool_name, "KEMBALI")
    except Exception as e:
        print(f"Error simpan log pengembalian: {e}")


def get_tool_positions(tool_name, page_number): 
    # Mencari daftar koordinat/pin untuk alat tertentu di laci tertentu
    positions = []
    try: 
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn: 
            cursor = conn.cursor()
            cursor.execute("SELECT mqtt_topic FROM tools WHERE name = ? AND page = ?", (tool_name, page_number))
            rows = cursor.fetchall()
            for row in rows: 
                positions.append(row[0])
    except Exception as e: 
        print(f"Error get positions:{e}")
    return positions

# ==============================================================================
# FUNGSI AUTO-SYNC USER (LATAR BELAKANG)
# ==============================================================================
def autosync_user():
    """Fungsi ini akan terus berputar diam-diam mengecek database web setiap 3 menit"""
    while True:
        try:
            with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, nama_user, nama_alat, status FROM log_peminjaman WHERE status_sync = 0")
                pending_logs = cursor.fetchall()

                for log in pending_logs: 
                    log_id, u_name, t_name, status = log
                    paket = {"nama_user": u_name, "kode_alat": t_name, "status": status}
                    try: 
                        res = requests.post(URL_LOG_PINJAM, json=paket, timeout=10)
                        if res.status_code == 200:
                            conn.execute("UPDATE log_peminjaman SET status_sync = 1 WHERE id = ?", (log_id,))
                            print(f"RE-SYNC log tertunda {u_name}, berhasil di setor ke web!")
                    except: 
                        pass
                conn.commit()

            ip_server = settings.get("db_host", "127.0.0.1:8000")
            response = requests.get(f"http://{ip_server}/api/v1/semua-user", timeout=10)
            
            if response.status_code == 200:
                data_users = response.json()
                
                with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
                    kursor = conn.cursor()

                    for u in data_users:
                        nama = u.get("nama")
                        rfid = u.get("rfid_card_uid")
                        role = u.get("role", "user").lower()
                        koin_web = u.get("koin", 0)
                        
                        if nama and rfid:
                            if role == "user":
                                kursor.execute("SELECT id FROM users WHERE rfid_card_uid = ?", (rfid,))
                                if kursor.fetchone():
                                    kursor.execute("UPDATE users SET nama = ?, koin = ? WHERE rfid_card_uid = ?", (nama, koin_web, rfid))
                                else: 
                                    kursor.execute("INSERT INTO users (nama, rfid_card_uid, role, koin) VALUES (?, ?, ?, ?)", (nama, rfid, role, koin_web))
                            elif role == "admin":
                                password_web = u.get("password", "admin123")
                                kursor.execute("SELECT id FROM admins WHERE rfid_card_uid = ?", (rfid,))
                                if kursor.fetchone():
                                    kursor.execute("UPDATE admins SET username = ?, password = ? WHERE rfid_card_uid = ?", (nama, password_web, rfid))
                                else: 
                                    kursor.execute("INSERT INTO admins (username, password, rfid_card_uid) VALUES (?, ?, ?)", (nama, password_web, rfid))
                    conn.commit()
                print("✅ [AUTO-SYNC] Data User berhasil diperbarui dari Web Nico!")
            else:
                print(f"❌ [AUTO-SYNC] Server Nico menolak! Status: {response.status_code}")
                # HANYA cetak 200 karakter pertama agar Command Prompt tidak error/kepenuhan
                print(f"Isi penolakannya: {response.text[:200]}...")
        except Exception as err:
            print(f"⚠️ [AUTO-SYNC] Gagal koneksi ke server web: {err}")

        # Tunda selama 180 detik (3 menit) sebelum mengecek lagi
        time.sleep(180) 

def jalankan_autosync_background():
    """Memanggil robot_autosync_user ke dalam thread agar UI tidak freeze"""
    task = threading.Thread(target=autosync_user, daemon=True)
    task.start()