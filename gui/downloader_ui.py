# gui/downloader_ui.py
import tkinter as tk
from tkinter import ttk
from utils.helpers import make_card

def create_downloader_ui(container, app):
    """建立主輸入區（URL、Cookie、Folder、Download 按鈕）"""
    shadow, input_card = make_card(container)

    # URL row
    row1 = ttk.Frame(input_card); row1.pack(fill=tk.X, pady=(0,10))
    ttk.Label(row1, text="Video URL：", width=10).pack(side=tk.LEFT)
    app.url_var = tk.StringVar()
    app.url_entry = ttk.Entry(row1, textvariable=app.url_var)
    app.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    app.url_entry.focus_set()

    # Cookies + outdir
    row2 = ttk.Frame(input_card); row2.pack(fill=tk.X, pady=(0,10))
    ttk.Label(row2, text="Cookies：", width=10).pack(side=tk.LEFT)

    app.cookie_var = tk.StringVar(value=app.saved_cookie)
    ttk.Entry(row2, textvariable=app.cookie_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
    app.btn_cookie = ttk.Button(row2, text="Choose File", command=app._pick_cookie)
    app.btn_cookie.pack(side=tk.LEFT, padx=(6,2))
    ttk.Button(row2, text="Clear", command=app._clear_cookie).pack(side=tk.LEFT, padx=(2,16))
    app.cookie_button_ref = app.btn_cookie

    ttk.Label(row2, text="Output Folder：").pack(side=tk.LEFT)
    app.outdir_var = tk.StringVar(value=app.output_dir)
    ttk.Entry(row2, textvariable=app.outdir_var, width=34).pack(side=tk.LEFT)
    app.btn_choose_folder = ttk.Button(row2, text="Choose Folder", command=app._pick_outdir)
    app.btn_choose_folder.pack(side=tk.LEFT, padx=(8,0))

    # Download / Stop
    row3 = ttk.Frame(input_card); row3.pack(fill=tk.X, pady=(4,0))
    app.btn_download = ttk.Button(row3, text="Download MP4",
                                  command=app.on_download, style="Accent.TButton")
    app.btn_download.pack(side=tk.LEFT)
    app.btn_stop = ttk.Button(row3, text="Stop",
                              command=app.on_stop, state=tk.DISABLED)
    app.btn_stop.pack(side=tk.LEFT, padx=(8,0))
    ttk.Button(row3, text="Open Download Folder", command=app._open_outdir)\
        .pack(side=tk.RIGHT)

    return input_card
