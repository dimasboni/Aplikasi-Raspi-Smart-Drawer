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

import flet as ft

from config import TEXT_COLOR, SHADOW_COLOR
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
                ft.Column(
                    [
                        ft.Text("Menu User", size=36, weight="bold", color=TEXT_COLOR),
                        ft.Container(height=30),
                        ft.Row(
                            [
                                create_menu_card(
                                    "Peminjaman", "Pinjam alat", "pinjam.png", "#E8F5E9",
                                    lambda _: nav["show_rfid_page"](
                                        "Scan Login Peminjaman",
                                        show_peminjaman_page1,
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
                ),
                back_func=nav["show_home"],
            )
        )

    def show_peminjaman_page1(e=None):
        page.clean()
        grid = ft.GridView(
            expand=True, runs_count=5, max_extent=180,
            child_aspect_ratio=0.85, spacing=20, run_spacing=20, padding=10,
        )
        for item in get_tools_from_db(1):
            grid.controls.append(create_tool_grid_item(item, nav["show_position_selection"]))
        page.add(
            build_standard_layout(
                grid, back_func=show_menu_user, title_text="Pilih Alat Laci 1",
                action_button=create_filled_button(
                    "Laci 2", "#1F2937", lambda _: show_peminjaman_page2(), width=100
                ),
            )
        )

    def show_peminjaman_page2(e=None):
        page.clean()
        grid = ft.GridView(
            expand=True, runs_count=5, max_extent=180,
            child_aspect_ratio=0.85, spacing=20, run_spacing=20, padding=10,
        )
        for item in get_tools_from_db(2):
            grid.controls.append(create_tool_grid_item(item, nav["show_position_selection"]))
        page.add(
            build_standard_layout(
                grid, back_func=show_menu_user, title_text="Pilih Alat Laci 2",
                action_button=create_filled_button(
                    "Laci 1", "#1F2937", lambda _: show_peminjaman_page1(), width=100
                ),
            )
        )

    def show_list_pinjaman_user(e=None):
        page.clean()
        borrowed = get_borrowed_tools(session_data["user_now"])
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
        )
        update_list()
        page.add(
            build_standard_layout(
                ft.Column([main_card], horizontal_alignment="center", alignment="center"),
                back_func=show_menu_user,
            )
        )

    nav["show_menu_user"] = show_menu_user
    nav["show_peminjaman_page1"] = show_peminjaman_page1
    nav["show_peminjaman_page2"] = show_peminjaman_page2
    nav["show_list_pinjaman_user"] = show_list_pinjaman_user
