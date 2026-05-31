"""
user_pages.py
=============
Berisi halaman-halaman yang diakses oleh User biasa:
  - show_menu_user          : Menu utama user (Peminjaman / Pengembalian)
  - show_peminjaman_page1   : Grid alat Laci 1
  - show_peminjaman_page2   : Grid alat Laci 2
  - show_list_pinjaman_user : Daftar alat yang sedang dipinjam user

Cara pemakaian:
    from pages.user_pages import register_user_pages
    register_user_pages(page, session_data, nav)
"""

import asyncio

import flet as ft

from config import BLUE_SENSOR, SUB_TEXT_COLOR, TEXT_COLOR, SHADOW_COLOR
from db_manager import get_tools_from_db, get_borrowed_tools
from ui_komponen import (
    create_filled_button,
    create_menu_card,
    create_tool_grid_item,
    build_standard_layout,
)


def register_user_pages(page: ft.Page, session_data: dict, nav: dict):
    """
    Mendaftarkan semua fungsi halaman user ke dalam dict 'nav'.
    nav keys yang ditambahkan:
        nav['show_menu_user']
        nav['show_peminjaman_page1']
        nav['show_peminjaman_page2']
        nav['show_list_pinjaman_user']
    """

    def show_menu_user(e=None):
        page.clean()
        page.add(
            build_standard_layout(
                title_text="MENU USER",
                content_control=ft.Column(
                    [
                        ft.Container(height=15),
                        ft.Row(
                            [
                                create_menu_card(
                                    "Peminjaman", "Pinjam alat", "pinjam.png", "#E8F5E9",
                                    lambda _: nav["show_rfid_page"](
                                        "Scan Login Peminjaman",
                                        show_peminjaman_page,
                                        show_menu_user,
                                    ),
                                ),
                                create_menu_card(
                                    "Pengembalian", "Kembalikan alat", "kembali.png", "#E3F2FD",
                                    lambda _: nav["show_rfid_page"](
                                        "Scan Login Pengembalian",
                                        show_list_pinjaman_user,
                                        show_menu_user,
                                    ),
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
                back_func=nav["show_home"],
            )
        )
    def show_peminjaman_page(e=None):
        page.clean()
        grid = ft.GridView(
            expand=True, max_extent=180,
            child_aspect_ratio=0.9, spacing=20, run_spacing=20, padding=ft.padding.only(left=10, right=10, top=10, bottom=80), 
        )
        def pilih_laci(e): 
            #Mengmabil nilai tombol yang baru saja dipilih 
            #(e.control.selected) isinya berbentuk himpunan yang akan diambil isinya dan dijadikan integer
            laci_terpilih = int(list(e.control.selected)[0])

            #menghapus semua gridview lama
            grid.controls.clear()

            #tarik data dari database 
            for item in get_tools_from_db(laci_terpilih):
                grid.controls.append(create_tool_grid_item(item, nav["show_position_selection"]))

            page.update()

        tombol_laci = ft.SegmentedButton(
            on_change=pilih_laci,
            selected_icon=ft.Icon(ft.Icons.CHECK_SHARP, size=18),
            selected=["1"],
            allow_multiple_selection=False,
            segments=[
                ft.Segment(
                    value="1",
                    label=ft.Text("Drawer 1", size=20, weight="bold"),
                ),
                ft.Segment(
                    value="2",
                    label=ft.Text("Drawer 2", size=20, weight="bold"),
                ),
                ft.Segment(
                    value="3",
                    label=ft.Text("Drawer 3", size=20, weight="bold")
                ),
                ft.Segment(
                    value="4",
                    label=ft.Text("Drawer 4", size=20, weight="bold")
                )
            ]
        )

        for item in get_tools_from_db(1):
            grid.controls.append(create_tool_grid_item(item, nav["show_position_selection"]))

        page.add(
            build_standard_layout(
                title_text="Choose Drawer & Tool",
                title_size=35,
                content_control=ft.Column([
                    tombol_laci, 
                    grid
                ],
                horizontal_alignment="center",
                spacing=20,
                expand=True,
                #scroll=ft.ScrollMode.ALWAYS,
                ),
            back_func=show_menu_user,
            )
        )

    def show_list_pinjaman_user(e=None):
        page.clean()
        nama_user = session_data.get("user_now", "Unknown")
        borrowed = get_borrowed_tools(nama_user)

        if not borrowed: 
            empty_card = ft.Container(
                content= ft.Column(
                    [
                        ft.Container(
                            content=ft.Image(src="/empty.png", width=80, height=80),
                            width=110, height=110, 
                            bgcolor="#EFF6FF",
                            border_radius=55,
                            alignment=ft.Alignment(0, 0),
                            border=ft.border.all(4, "#DBEAFE")
                        ),
                        
                        ft.Text("Your borrowing list is empty!", size=28, weight="bold", color=BLUE_SENSOR, text_align="center"),

                        ft.Container(
                             ft.Text(
                            f"{nama_user.upper()}", size=14, weight="bold", color="white"
                        ),
                        bgcolor="#1E293B",
                        padding=ft.padding.symmetric(horizontal=15, vertical=5),
                        border_radius=20
                        ),
                        ft.Container(height=10),
                        ft.Row(
                            [
                                ft.ProgressRing(width=25, height=25, color=BLUE_SENSOR, stroke_width=3),
                                ft.Text("Returning to Home...", size=12, color=SUB_TEXT_COLOR, italic=True),
                            ],
                            alignment="center",
                            spacing=15
                        )
                    ],
                    alignment="center",
                    horizontal_alignment="center",
                    spacing = 10
                ),
                width=520, 
                height=400, 
                padding=40, 
                bgcolor="white",
                border_radius=20, 
                shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR),
                alignment=ft.Alignment(0, 0),
                margin=ft.margin.only(top=-130)
            )
            page.add(build_standard_layout(ft.Container(content=empty_card, alignment=ft.Alignment(0, 0))))

            async def auto_back():
                await asyncio.sleep(4.0)
                nav["show_home"]()
            page.run_task(auto_back)
            return
        
        #JIKA ADA ALAT YANG DIPINJAM TAMPILKAN DAFTARNYA 

        state = {"page": 0}
        items_per_page = 4
        list_container = ft.Column(spacing=10, horizontal_alignment="center")

        btn_prev = ft.ElevatedButton(
            "< Prev", on_click=lambda e: change_page(-1),
            disabled=True, color="black", bgcolor="#E2E8F0",
        )
        btn_next_page = ft.ElevatedButton(
            "Next >", on_click=lambda e: change_page(1),
            disabled=True, color="black", bgcolor="#E2E8F0",
        )

        def update_list():
            list_container.controls.clear()
            start_idx = state["page"] * items_per_page
            end_idx = start_idx + items_per_page
            if not borrowed:
                list_container.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "Tidak ada alat yang dipinjam.",
                            color="red", size=16, weight="bold", text_align="center",
                        ),
                        alignment=ft.Alignment(0, 0), height=150,
                    )
                )
            else:
                for i, alat in enumerate(borrowed[start_idx:end_idx]):
                    list_container.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Container(
                                    content=ft.Text(str(start_idx + i + 1), color="white", weight="bold"),
                                    bgcolor="#3B82F6", width=30, height=30,
                                    border_radius=15, alignment=ft.Alignment(0, 0),
                                ),
                                ft.Text(alat, size=16, weight="bold", color="black", expand=True),
                                ft.Container(
                                    content=ft.Text("Qty: 1", color="white", size=12, weight="bold"),
                                    bgcolor="#111827",
                                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                                    border_radius=15,
                                ),
                            ]),
                            bgcolor="#F3F4F6", padding=10, border_radius=10, width=450,
                        )
                    )
            btn_prev.disabled = state["page"] == 0
            btn_next_page.disabled = end_idx >= len(borrowed)
            page.update()

        def change_page(delta):
            state["page"] += delta
            update_list()

        btn_action = create_filled_button(
            "Lanjut scan alat", "#1F2937",
            lambda _: nav["show_scan_kembali"](borrowed) if borrowed else None,
            width=450, height=50, disabled=not bool(borrowed),
        )
        main_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Daftar Alat yang Dipinjam", size=24, weight="bold", color="black"),
                    ft.Container(height=5),
                    ft.Container(content=list_container, height=240, alignment=ft.Alignment(0, -1)),
                    ft.Row([btn_prev, btn_next_page], alignment="center", spacing=20),
                    ft.Container(height=10),
                    btn_action,
                ],
                horizontal_alignment="center", alignment="center",
            ),
            width=600, bgcolor="white", padding=30, border_radius=20,
            shadow=ft.BoxShadow(blur_radius=30, color=SHADOW_COLOR),
            alignment=ft.Alignment(0, 0),
            margin=ft.margin.only(top=-150)
        )
        update_list()
        page.add(
            build_standard_layout(
                ft.Column([main_card], horizontal_alignment="center", alignment="center"),
                back_func=show_menu_user,
            )
        )

    nav["show_menu_user"] = show_menu_user
    nav["show_peminjaman_page"] = show_peminjaman_page
    nav["show_list_pinjaman_user"] = show_list_pinjaman_user
