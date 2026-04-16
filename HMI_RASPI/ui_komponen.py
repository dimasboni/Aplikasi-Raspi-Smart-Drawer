import flet as ft
import math

# Kita import setingan warna dari config.py
from config import BG_COLOR, TEXT_COLOR, SUB_TEXT_COLOR, SHADOW_COLOR, PAGE_WIDTH, HEADER_HEIGHT, CONTENT_AREA_HEIGHT

# Bantuan hitungan rotasi gambar
def get_rotation_angle(degrees): 
    return degrees * (math.pi / 180)

# ==============================================================================
# PABRIK KOMPONEN (TUKANG KAYU)
# File ini ibarat pabrik komponen. Kita pesan "Buatin tombol dong", 
# nanti dia akan mengembalikan (return) tombol yang sudah jadi.
# ==============================================================================

def create_filled_button(text_str, bg_color, on_click_func, width=None, height=None, disabled=False):
    """Mencetak tombol standar dengan teks putih tebal"""
    return ft.FilledButton(
        content=ft.Text(text_str, weight="bold", color="white"), 
        style=ft.ButtonStyle(bgcolor=bg_color, shape=ft.RoundedRectangleBorder(radius=8)), 
        on_click=on_click_func, 
        width=width, 
        height=height,
        disabled=disabled
    )

def create_menu_card(title, subtitle, img, bg_icon, on_click):
    """Mencetak kartu menu kotak (seperti menu User/Admin di layar utama)"""
    return ft.Container(
        content=ft.Column([
            ft.Container(content=ft.Image(src=f"/{img}", width=60, height=60), bgcolor=bg_icon, padding=20, border_radius=50),
            ft.Text(title, size=22, weight="bold", color=TEXT_COLOR),
            ft.Text(subtitle, size=14, color=SUB_TEXT_COLOR, weight="bold"),
        ], alignment="center", horizontal_alignment="center", spacing=10),
        width=400, 
        height=350, 
        bgcolor="white", 
        border_radius=20, 
        shadow=ft.BoxShadow(blur_radius=25, color=SHADOW_COLOR), 
        on_click=on_click, 
        ink=True
    )

def create_tool_grid_item(item_data, on_click):
    """Mencetak kartu kecil berisi gambar alat (tool) untuk ditampilkan di laci rak"""
    rotation_deg = item_data.get("rot", 0)
    stok = item_data.get("total", 0) 
    is_empty = stok <= 0        
    
    return ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Image(src=f"/{item_data['img']}", height=90, fit="contain"), 
                rotate=ft.Rotate(angle=get_rotation_angle(rotation_deg), alignment=ft.Alignment(0,0)), 
                opacity=0.2 if is_empty else 1.0
            ),
            ft.Text(item_data['name'], size=14, weight="bold", color="#B0BEC5" if is_empty else TEXT_COLOR, text_align="center", max_lines=2),
            ft.Text("HABIS" if is_empty else f"Stok: {stok}", size=12, weight="bold", color="red" if is_empty else "green"),
        ], alignment="center", horizontal_alignment="center", spacing=5),
        bgcolor="#F5F5F5" if is_empty else "white", 
        border_radius=15, 
        padding=10, 
        border=ft.border.all(1, "#DDDDDD"),
        on_click=lambda e: on_click(item_data['name'], item_data) if not is_empty else None, 
        disabled=is_empty, 
        ink=not is_empty, 
        alignment=ft.Alignment(0, 0)
    )

def build_standard_layout(content_control, back_func=None, title_text="", action_button=None):
    """Mencetak Layout/Rangka Atap dan Halaman (Punya tombol back/kembali di pojok)"""
    header_row = ft.Row([
        ft.Container(content=ft.Text("⬅️ Kembali", size=18, weight="bold", color=TEXT_COLOR), on_click=back_func, padding=10, border_radius=10, ink=True) if back_func else ft.Container(width=100),
        ft.Container(content=ft.Text(title_text, size=28, weight="bold", color=TEXT_COLOR, text_align="center"), alignment=ft.Alignment(0, 0), expand=True),
        action_button if action_button else ft.Container(width=100) 
    ], alignment="spaceBetween", vertical_alignment="center", width=PAGE_WIDTH - 60)

    return ft.Column([
        ft.Container(height=10), 
        ft.Container(content=header_row, width=PAGE_WIDTH, height=HEADER_HEIGHT, padding=ft.padding.symmetric(horizontal=30)),
        ft.Container(content=content_control, width=PAGE_WIDTH, height=CONTENT_AREA_HEIGHT, alignment=ft.Alignment(0, 0), padding=ft.padding.symmetric(horizontal=30))
    ], horizontal_alignment="center", spacing=0)
