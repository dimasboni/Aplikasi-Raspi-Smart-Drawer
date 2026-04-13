import sqlite3
import requests
import threading
from config import settings 

# --- KONFIGURASI API NIKO ---
ip_server_niko = settings.get("db_host", "10.195.71.208")
API_URL_NIKO =f"http://{ip_server_niko}/smartdrawer/api_terima.php"

# ==============================================================================
# FUNGSI-FUNGSI DATABASE (SQLITE3)
# Semua transaksi database kumpul di file ini!
# ==============================================================================

def update_stok_otomatis(tool_name, jumlah_stok):
    """Mengupdate stok alat di tabel tools saat sensor mendeteksi perubahan."""
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            conn.execute("UPDATE tools SET total = ? WHERE name = ?", (jumlah_stok, tool_name))
            conn.commit()
    except Exception as e:
        print(f"Error update stok sensor: {e}")

def get_tools_from_db(page_number):
    """Mengambil daftar alat berdasarkan halaman (Laci 1 / Laci 2)."""
    tools_list = []
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, img, total, rot FROM tools WHERE page = ?", (page_number,))
            rows = cursor.fetchall()
            for row in rows:
                tools_list.append({"name": row[0], "img": row[1], "total": row[2], "rot": row[3]})
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

def kirim_ke_server_niko(user_name, tool_name, status):
    """Mengirim log ke server API PHP NIKO menggunakan thread terpisah."""
    def tugas_kirim():
        paket_data = {"nama_user": user_name, "nama_alat": tool_name, "status": status}
        try:
            requests.post(API_URL_NIKO, json=paket_data, timeout=3)
        except Exception: 
            pass # Abaikan jika server error/mati
    
    # Menjalankan di background agar UI flet tidak macet menunggu balasan API
    threading.Thread(target=tugas_kirim).start()

def simpan_log(user_name, tool_name, status):
    """Mencatat aktivitas PINJAM ke database lokal dan mengirim via API."""
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            conn.execute("INSERT INTO log_peminjaman (nama_user, nama_alat, status) VALUES (?, ?, ?)", (user_name, tool_name, status))
            conn.commit()
        kirim_ke_server_niko(user_name, tool_name, status)
    except Exception as e:
        print(f"Error simpan log: {e}")

def simpan_log_pengembalian(user_name, tool_name):
    """Mencatat aktivitas KEMBALI ke database lokal dan mengirim via API."""
    try:
        with sqlite3.connect("smartdrawer.db", timeout=20) as conn:
            conn.execute("INSERT INTO log_peminjaman (nama_user, nama_alat, status) VALUES (?, ?, ?)", (user_name, tool_name, "KEMBALI"))
            conn.commit()
        kirim_ke_server_niko(user_name, tool_name, "KEMBALI")
    except Exception as e:
        print(f"Error simpan log pengembalian: {e}")
