# gui/header.py
import tkinter as tk
from tkinter import ttk, messagebox

def create_header(parent, style, on_theme_change):
    """建立 Header（標題 + 主題切換）並回傳所有控制元件"""
    bg = style.colors.bg
    style.configure("Header.TFrame", background=bg)

    header = ttk.Frame(parent, borderwidth=0, relief="flat", style="Header.TFrame")
    header.pack(fill=tk.X, pady=(2, 0), padx=16)

    # 左邊：標題
    title_frame = ttk.Frame(header, style="Header.TFrame")
    title_frame.pack(side=tk.LEFT, anchor="w")

    title_label = ttk.Label(
        title_frame, text="x.com Audio Converter",
        font=("Segoe UI", 14, "bold")
    )
    title_label.pack(anchor="w")

    subtitle_label = ttk.Label(
        title_frame,
        text="Preview and progress shown; auto-clear on completion.",
        font=("Segoe UI", 9)
    )
    subtitle_label.pack(anchor="w")

    # 右邊：主題切換
    theme_frame = ttk.Frame(header, style="Header.TFrame")
    theme_frame.pack(side=tk.RIGHT, anchor="e", pady=(8, 0))

    theme_text_label = ttk.Label(theme_frame, text="Theme:")
    theme_text_label.pack(side=tk.LEFT, padx=(0, 6))

    themes = ["cosmo", "darkly", "flatly", "journal", "minty",
              "pulse", "superhero", "united", "morph"]
    theme_var = tk.StringVar(value=style.theme.name)

    theme_combo = ttk.Combobox(
        theme_frame,
        textvariable=theme_var,
        values=themes,
        state="readonly",
        width=12,
    )
    theme_combo.pack(side=tk.LEFT)

    def change_theme(event=None):
        try:
            style.theme_use(theme_var.get())
            on_theme_change()  # 通知主程式更新 Header 顏色
        except Exception as e:
            messagebox.showerror("Error", f"Failed to change theme:\n{e}")

    theme_combo.bind("<<ComboboxSelected>>", change_theme)

    # 回傳所有控制元件給主程式
    return {
        "frame": header,
        "title_frame": title_frame,
        "title_label": title_label,
        "subtitle_label": subtitle_label,
        "theme_frame": theme_frame,
        "theme_text_label": theme_text_label,
        "theme_var": theme_var,
        "theme_combo": theme_combo
    }
