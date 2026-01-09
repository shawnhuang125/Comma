import os, sys, io, threading, queue, traceback, shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import requests, yt_dlp

# 匯入共用工具模組
from utils.config_manager import load_config, save_config
from utils.dialogs import custom_yesno, ask_overwrite_or_rename
from utils.helpers import make_card, get_resource_path
from utils.style import setup_style


APP_TITLE = "Universal Media Downloader"

# GUI APPLICATION初始化與運行
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.temp_files = []  # 記錄正在下載的暫存檔 (.part)
        self.title(APP_TITLE)
        # 必須放在最前面，因為後面的 Icon 和 FFmpeg 檢查可能都會用到它
        self.config_data = load_config()

        # === [修改] 檢查 FFmpeg (優先使用打包好的檔案) ===
        self.ffmpeg_ok = False
        self.ffmpeg_status = tk.StringVar(value="Checking bundled FFmpeg...")

        # 1. 取得資源路徑 (支援開發環境與打包後的環境)
        target_ffmpeg = get_resource_path("ffmpeg.exe")

        if os.path.exists(target_ffmpeg):
            self.ffmpeg_ok = True
            self.ffmpeg_status.set(f"Ready (Bundled): {target_ffmpeg}")
            
            # 關鍵：將 ffmpeg 所在資料夾加入環境變數 PATH
            # 這樣 yt-dlp 執行時就能直接呼叫到 ffmpeg
            ffmpeg_dir = os.path.dirname(target_ffmpeg)
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
            print(f"✅ Bundled FFmpeg found: {target_ffmpeg}")
        else:
            # 2. 如果開發環境還沒放 exe，嘗試找電腦系統內建的 (備用)
            ffmpeg_sys = shutil.which("ffmpeg")
            if ffmpeg_sys:
                self.ffmpeg_ok = True
                self.ffmpeg_status.set(f"Ready (System): {ffmpeg_sys}")
            else:
                self.ffmpeg_status.set("Error: FFmpeg not found.")
                print("❌ Critical: No FFmpeg found.")


        # 設定程式圖示（使用 PNG）
        # === 設定程式圖示（從 config.json 載入） ===
        try:
            # 1. 預設使用打包在內部的圖片 (使用 get_resource_path 確保打包後找得到)
            # 注意：這裡假設你的圖片放在專案根目錄下的 assets 資料夾
            icon_path = get_resource_path(os.path.join("assets", "repost.png"))
            
            # 2. (選用) 如果你想支援 Config 自訂圖示，可以加這段覆蓋
            custom_icon = self.config_data.get("icon_path")
            if custom_icon and os.path.exists(custom_icon):
                icon_path = custom_icon

            # 3. 執行載入
            if os.path.exists(icon_path):
                icon_img = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, icon_img)
                self._icon_img = icon_img 
                print(f"✅ Loaded icon from: {icon_path}")
            else:
                print(f"⚠️ Icon not found at: {icon_path}")

        except Exception as e:
            print(f"⚠️ Failed to load icon: {e}")

        self.minsize(780, 480)

        import ttkbootstrap as tb
        self.style = setup_style(self)
        self.themed_frame = tb.Frame(self)  # 讓 ttkbootstrap 接管
        self.themed_frame.pack(fill=tk.BOTH, expand=True)

        # 狀態初始化
        self.msgq = queue.Queue()
        self.stop_flag = False
        self.thumbnail_tk = None
        self.last_filename = None
        self.output_dir = ""
        # 載入 cookie 記錄
        self.config_data = load_config()
        self.saved_cookie = self.config_data.get("cookie_path", "")
        setup_style(self)
        self._build_ui()
        self.after(80, self._drain_queue)
        # 視窗關閉時自動保存 config.json
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _update_header_colors(self):
        """當主題切換時，自動更新 Header 顏色"""
        bg = self.style.colors.bg
        fg = self.style.colors.fg
        sub_fg = self.style.colors.secondary

        # frame 背景
        self.style.configure("Header.TFrame", background=bg)
        self.header.configure(style="Header.TFrame")
        self.title_frame.configure(style="Header.TFrame")
        self.theme_frame.configure(style="Header.TFrame")

        # 文字色
        self.title_label.configure(background=bg, foreground=fg)
        self.subtitle_label.configure(background=bg, foreground=sub_fg)
        self.theme_text_label.configure(background=bg, foreground=fg)

    def _build_ui(self):
        # === Header ===
        bg = self.style.colors.bg
        self.style.configure("Header.TFrame", background=bg)

        self.header = ttk.Frame(self, borderwidth=0, relief="flat", style="Header.TFrame")
        self.header.pack(fill=tk.X, pady=(2, 0), padx=16)

        self.title_frame = ttk.Frame(self.header, style="Header.TFrame")
        self.title_frame.pack(side=tk.LEFT, anchor="w")

        self.title_label = ttk.Label(
            self.title_frame, text="Multi-Platform Media Converter",
            font=("Segoe UI", 14, "bold")
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ttk.Label(
            self.title_frame,
            text="Supports X.com, YouTube, and more. Preview and progress shown.",
            font=("Segoe UI", 9)
        )
        self.subtitle_label.pack(anchor="w")

        self.theme_frame = ttk.Frame(self.header, style="Header.TFrame")
        self.theme_frame.pack(side=tk.RIGHT, anchor="e", pady=(8, 0))

        self.theme_text_label = ttk.Label(self.theme_frame, text="Theme:")
        self.theme_text_label.pack(side=tk.LEFT, padx=(0, 6))

        themes = ["cosmo", "darkly", "flatly", "journal", "minty",
                "pulse", "superhero", "united", "morph"]
        self.theme_var = tk.StringVar(value=self.style.theme.name)

        theme_combo = ttk.Combobox(
            self.theme_frame,
            textvariable=self.theme_var,
            values=themes,
            state="readonly",
            width=12,
        )
        theme_combo.pack(side=tk.LEFT)

        def change_theme(event=None):
            try:
                self.style.theme_use(self.theme_var.get())
                self._update_header_colors()        # 主題切換時更新顏色
            except Exception as e:
                messagebox.showerror("Error", f"Failed to change theme:\n{e}")

        theme_combo.bind("<<ComboboxSelected>>", change_theme)

        # 先依目前主題套一次色
        self._update_header_colors()


        # Container
        container = ttk.Frame(self, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        # ===== Input card =====
        self.input_shadow, input_card = make_card(container)

        # URL row
        row1 = ttk.Frame(input_card); row1.pack(fill=tk.X, pady=(0,10))
        ttk.Label(row1, text="Video URL：", width=10, style="CardTitle.TLabel").pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(row1, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.url_entry.focus_set()

        # Cookies + outdir
        row2 = ttk.Frame(input_card); row2.pack(fill=tk.X, pady=(0,10))
        ttk.Label(row2, text="Cookies：", width=10).pack(side=tk.LEFT)

        self.cookie_var = tk.StringVar(value=self.saved_cookie)
        ttk.Entry(row2, textvariable=self.cookie_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.btn_cookie = ttk.Button(row2, text="Choose File", command=self._pick_cookie)
        self.btn_cookie.pack(side=tk.LEFT, padx=(6,2))
        ttk.Button(row2, text="Clear", command=self._clear_cookie).pack(side=tk.LEFT, padx=(2,16))
        # 為 tweet 錯誤提示氣泡準備定位
        self.cookie_button_ref = self.btn_cookie

        ttk.Label(row2, text="Output Folder：").pack(side=tk.LEFT)
        self.outdir_var = tk.StringVar(value=self.output_dir)
        ttk.Entry(row2, textvariable=self.outdir_var, width=34).pack(side=tk.LEFT)
        self.btn_choose_folder = ttk.Button(row2, text="Choose Folder", command=self._pick_outdir)
        self.btn_choose_folder.pack(side=tk.LEFT, padx=(8,0))

        row3 = ttk.Frame(input_card); row3.pack(fill=tk.X, pady=(4,0))
        # 下載MP4按鈕
        self.btn_download = ttk.Button(row3, text="Download MP4",
                               command=lambda: self.on_download(as_mp3=False), 
                               style="Accent.TButton")
        #停止按鈕
        self.btn_download.pack(side=tk.LEFT)

        # Download MP3 按鈕 (指定 as_mp3=True)
        self.btn_download_mp3 = ttk.Button(row3, text="Download MP3",
                                        command=lambda: self.on_download(as_mp3=True), 
                                        style="Accent.TButton")
        self.btn_download_mp3.pack(side=tk.LEFT, padx=(8,0))

        self.btn_stop = ttk.Button(row3, text="Stop",
                                   command=self.on_stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=(8,0))
        #開啟下載資料夾
        ttk.Button(row3, text="Open Download Folder", command=self._open_outdir)\
            .pack(side=tk.RIGHT)

        ttk.Separator(container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8,8))

        # ===== Dynamic card (only visible during download) =====
        self.dynamic_shadow, dynamic_card = make_card(container)

        # Top: preview + meta
        top = ttk.Frame(dynamic_card); top.pack(fill=tk.X, pady=(0,8))
        self.preview_canvas = tk.Canvas(
            top, width=340, height=190, bg="#111",
            highlightthickness=1, highlightbackground="#3a3a3a"
        )
        self.preview_canvas.pack(side=tk.LEFT)

        meta = ttk.Frame(top); meta.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14,0))
        self.title_var = tk.StringVar(value="")
        self.uploader_var = tk.StringVar(value="")
        self.duration_var = tk.StringVar(value="")
        ttk.Label(meta, textvariable=self.title_var, style="CardTitle.TLabel",
                  wraplength=350, justify=tk.LEFT).pack(anchor="w")
        ttk.Label(meta, textvariable=self.uploader_var, style="Dim.TLabel")\
            .pack(anchor="w", pady=(6,0))
        ttk.Label(meta, textvariable=self.duration_var, style="Dim.TLabel")\
            .pack(anchor="w", pady=(2,0))

        ttk.Separator(dynamic_card, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        self.progress = ttk.Progressbar(dynamic_card, orient="horizontal", mode="determinate")
        self.progress.pack(fill=tk.X); self.progress["value"] = 0

        meta2 = ttk.Frame(dynamic_card); meta2.pack(fill=tk.X)
        self.percent_var = tk.StringVar(value="")
        self.speed_var = tk.StringVar(value="")
        self.eta_var = tk.StringVar(value="")
        self.file_var = tk.StringVar(value="")
        ttk.Label(meta2, textvariable=self.percent_var, width=6, style="Dim.TLabel").pack(side=tk.LEFT)
        ttk.Label(meta2, textvariable=self.speed_var, style="Dim.TLabel").pack(side=tk.LEFT, padx=(8,0))
        ttk.Label(meta2, textvariable=self.eta_var, style="Dim.TLabel").pack(side=tk.LEFT, padx=(12,0))
        ttk.Label(meta2, textvariable=self.file_var, style="Dim.TLabel").pack(side=tk.LEFT, padx=(12,0))

        # 初始隱藏 dynamic
        self._set_dynamic_visible(False)

    # ------- show/hide dynamic by shadow frame -------
    def _set_dynamic_visible(self, visible: bool):
        if visible:
            self.dynamic_shadow.pack(fill=tk.X)
        else:
            self.dynamic_shadow.pack_forget()

    # ---------------- Events ----------------

    def _pick_outdir(self):
        p = filedialog.askdirectory(title="choose output folder", initialdir=self.outdir_var.get())
        if p: self.outdir_var.set(p)

    def _open_outdir(self):
        d = self.outdir_var.get()
        try:
            if sys.platform.startswith("win"):
                os.startfile(d)
            elif sys.platform == "darwin":
                os.system(f'open "{d}"')
            else:
                os.system(f'xdg-open "{d}"')
        except Exception as e:
            messagebox.showerror("error", f"can not open output folder：{e}")

    def on_stop(self):
        """使用者按下 Stop 時，中斷下載並清理暫存檔"""
        self.stop_flag = True
        self.btn_stop.configure(state=tk.DISABLED)

        removed = []
        for f in list(self.temp_files):
            try:
                for ext in ["", ".part", ".ytdl", ".temp", ".temp.mp4",".f*"]:
                    temp_path = f + ext
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        removed.append(os.path.basename(temp_path))
            except Exception as e:
                print(f"Failed to delete temp file {f}: {e}")
        self.temp_files.clear()

        if removed:
            messagebox.showinfo("Download Stopped",
                                f"Download stopped.\nDeleted temp files:\n\n" + "\n".join(removed))
        else:
            messagebox.showinfo("Download Stopped", "Download stopped. No temp files found.")

    def on_download(self, as_mp3=False):
        if not self.ffmpeg_ok:
            # 若已有提示則先刪除
            if hasattr(self, "ffmpeg_hint") and self.ffmpeg_hint.winfo_exists():
                self.ffmpeg_hint.destroy()

            if not self.ffmpeg_ok:
                messagebox.showerror(
                    "Error", 
                    "FFmpeg component is missing.\n\n"
                    "The application cannot find 'ffmpeg.exe'. Please ensure the application is installed correctly."
                )
                return

        # 檢查 URL
        url = (self.url_var.get() or "").strip()
        if not url:
            messagebox.showwarning("Prompt:", "Please enter the video URL first.")
            return

        # 檢查輸出資料夾
        outdir = (self.outdir_var.get() or "").strip()
        if not outdir:
            # 若已有提示則先刪除
            if hasattr(self, "outdir_hint") and self.outdir_hint.winfo_exists():
                self.outdir_hint.destroy()

            # 找到「Choose Folder」按鈕
            # 用 row2 最後一個子元件即為「Choose Folder」按鈕
            choose_btn = None
            for child in self.children.values():
                pass  # 不要動這裡，後面處理
            # 我們在 _build_ui 裡 pack() 時是這樣命名的，所以可以直接抓：
            choose_btn = self.btn_choose_folder if hasattr(self, "btn_choose_folder") else None
            if not choose_btn:
                # 如果你還沒綁定 btn_choose_folder，請補上這行到 _build_ui 的地方 ↓
                # self.btn_choose_folder = ttk.Button(row2, text="Choose Folder", command=self._pick_outdir)
                # self.btn_choose_folder.pack(side=tk.LEFT, padx=(8,0))
                # 然後這裡會自動抓到
                return

            bx = choose_btn.winfo_rootx()
            by = choose_btn.winfo_rooty()
            bw = choose_btn.winfo_width()

            # 建立氣泡框
            self.outdir_hint = tk.Toplevel(self)
            self.outdir_hint.overrideredirect(True)
            self.outdir_hint.attributes("-topmost", True)
            self.outdir_hint.configure(bg="#fdf2f2", padx=8, pady=6)

            msg = ttk.Label(
                self.outdir_hint,
                text="⚠️ Please select an output folder",
                background="#fdf2f2",
                foreground="#c9302c",
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
            )
            msg.pack()
            msg.bind("<Button-1>", lambda e: (self._pick_outdir(), self.outdir_hint.destroy()))

            # 顯示在按鈕正上方
            self.outdir_hint.update_idletasks()
            hint_w = self.outdir_hint.winfo_width()
            hint_h = self.outdir_hint.winfo_height()
            self.outdir_hint.geometry(
                f"{hint_w}x{hint_h}+{bx + bw//2 - hint_w//2}+{by - hint_h - 10}"
            )

            # 自動消失
            self.outdir_hint.after(3000, self.outdir_hint.destroy)
            self.bell()
            return

        os.makedirs(outdir, exist_ok=True)

        # 檢查是否已有同名影片
        try:
            # 根據點擊模式切換檢查的副檔名
            current_ext = "mp3" if as_mp3 else "mp4"
            
            info_opts = {
                "quiet": True,
                "no_warnings": True,
                "cookiefile": self.cookie_var.get().strip() or None,
                "noplaylist": True,
                "outtmpl": f"%(title)s.{current_ext}", # 修改這裡
                "paths": {"home": outdir},
            }

            with yt_dlp.YoutubeDL(info_opts) as y:
                info = y.extract_info(url, download=False)
                expected_name = y.prepare_filename(info)

            # 定義基礎模板，稍後可能會被修改 (如果使用者選擇 Rename)
            final_outtmpl = os.path.join(outdir, "%(title)s.%(ext)s")

            if os.path.exists(expected_name):
                # 呼叫新的對話視窗，接收 (動作, 後綴)
                action, suffix = ask_overwrite_or_rename(self, expected_name)

                if action == "cancel":
                    return  # 取消下載
                
                elif action == "overwrite":
                    try:
                        os.remove(expected_name)
                    except Exception as e:
                        messagebox.showerror("Error", f"Cannot delete old file:\n{e}")
                        return
                
                elif action == "rename":
                    # 使用者選擇重新命名，修改檔名模板
                    # 例如:原本是 "%(title)s.%(ext)s" -> 變成 "%(title)s_1.%(ext)s"
                    final_outtmpl = os.path.join(outdir, f"%(title)s{suffix}.%(ext)s")
        except Exception as e:
            print(f"File pre-check failed: {e}")


        cookie_path = self.cookie_var.get().strip() or None

        # reset for a run
        self.stop_flag = False
        self.btn_download.configure(state=tk.DISABLED)
        self.btn_download_mp3.configure(state=tk.DISABLED) # 禁用 MP3 按鈕
        self.btn_stop.configure(state=tk.NORMAL)
        
        
        self._reset_dynamic_only()
        self._set_dynamic_visible(True)

        def worker(is_audio_only):
            final_path = None
            try:
                def progress_hook(d):
                    if self.stop_flag:
                        raise yt_dlp.utils.DownloadCancelled("User stopped")
                    status = d.get("status")
                    # 如果正在下載中
                    if status == "downloading":
                        filename = d.get("filename")
                        if filename:
                            # 記錄暫存檔名稱，以便 Stop 時刪除
                            if filename not in self.temp_files:
                                self.temp_files.append(filename)

                        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                        done = d.get("downloaded_bytes", 0)
                        percent = (done / total * 100.0) if total else 0.0
                        speed = d.get("speed")
                        speed_str = f"{self._hr_size(speed)}/s" if speed else "—"
                        eta = d.get("eta")
                        eta_str = self._hr_eta(eta)

                        self.msgq.put(("progress", {
                            "percent": percent,
                            "speed": speed_str,
                            "eta": eta_str,
                        }))

                        if filename:
                            self.last_filename = filename
                    
                    #下載完成
                    elif status == "finished":
                        self.msgq.put(("progress", {
                            "percent": 100.0,
                            "speed": "—",
                            "eta": "—",
                            "filename": os.path.basename(d.get("filename", self.last_filename or "")),
                        }))
                        # 清空暫存檔紀錄（因為已成功完成下載）
                        self.temp_files.clear()

                cookie_path = self.cookie_var.get().strip() or None
                # info (inside download flow)
                info_opts = {
                    "quiet": True, "no_warnings": True,
                    "cookiefile": cookie_path,
                    "noplaylist": True,
                }
                with yt_dlp.YoutubeDL(info_opts) as y:
                    info = y.extract_info(url, download=False)

                title = info.get("title") or "—"
                uploader = info.get("uploader") or info.get("channel") or "—"
                duration = info.get("duration")
                thumb = info.get("thumbnail")

                self.msgq.put(("meta", {
                    "title": info.get("title") or "—",
                    "uploader": info.get("uploader") or info.get("channel") or "—",
                    "duration": self._human_duration(info.get("duration"))
                }))

                if thumb:
                    try:
                        r = requests.get(thumb, timeout=10); r.raise_for_status()
                        img = Image.open(io.BytesIO(r.content)).convert("RGB")
                        self.msgq.put(("thumb", img))
                    except Exception:
                        self.msgq.put(("thumb", None))
                else:
                    self.msgq.put(("thumb", None))

                ffmpeg_path = get_resource_path("ffmpeg.exe") if self.ffmpeg_ok else shutil.which("ffmpeg")

                if is_audio_only:
                    ydl_opts = {
                        "ffmpeg_location": ffmpeg_path, # <--- 明確加入這行
                        "outtmpl": final_outtmpl.replace(".%(ext)s", ".mp3"), # 確保檔名後綴
                        "cookiefile": cookie_path,
                        "noplaylist": True,
                        "format": "bestaudio/best",
                        "progress_hooks": [progress_hook],
                        "postprocessors": [{
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }, {"key": "FFmpegMetadata"}],
                        "quiet": True, "no_warnings": True,
                    }
                else:
                    ydl_opts = {
                        "ffmpeg_location": ffmpeg_path,
                        "outtmpl": final_outtmpl,
                        "cookiefile": cookie_path,
                        "noplaylist": True,
                        # 1. 抓取最佳影音，不強硬鎖死編碼 (讓 X 的片段能順利合併)
                        "format": "bestvideo+bestaudio/best",
                        "progress_hooks": [progress_hook],
                        "postprocessors": [
                            {
                                "key": "FFmpegVideoConvertor",
                                "preferedformat": "mp4", # 確保最終轉成 mp4 容器
                            },
                            {"key": "FFmpegMetadata"},
                        ],
                        # 2. 關鍵修正：改用 -c copy 模式
                        # 這不會重新運算每一幀(Encoding)，而是直接把下載的數據封裝進 MP4
                        # 對於 X 這種片段多且速度慢的平台，這樣最穩定且快 10 倍
                        "postprocessor_args": {
                            "video_convertor": [
                                "-c", "copy", 
                                "-movflags", "faststart"
                            ]
                        },
                        "quiet": True,
                        "no_warnings": True,
                    }

                # 根據下載模式決定檢查的副檔名
                check_ext = "mp3" if as_mp3 else "mp4"
                info_opts["outtmpl"] = f"%(title)s.{check_ext}" # 修改檢查用的模板
                
                with yt_dlp.YoutubeDL(ydl_opts) as y:
                    y.process_info(info)
                    fn = y.prepare_filename(info)
                # 取得不含副檔名的基礎路徑，用來精準偵測最終產出的檔案
                base_path = os.path.splitext(fn)[0]

                if is_audio_only:
                    # 音訊模式：優先檢查是否成功產出 .mp3
                    potential_mp3 = base_path + ".mp3"
                    if os.path.exists(potential_mp3):
                        final_path = potential_mp3
                    else:
                        final_path = fn
                else:
                    # 影片模式：這是解決你問題的核心
                    # 優先序 1：檢查轉檔後的 .mp4 是否存在 (解決 webm/mp4 並存問題)
                    potential_mp4 = base_path + ".mp4"
                    if os.path.exists(potential_mp4):
                        final_path = potential_mp4
                    # 優先序 2：如果沒有 mp4，檢查原始預期檔名是否存在
                    elif os.path.exists(fn):
                        final_path = fn
                    else:
                        # 兜底：如果都沒找到，維持原檔名
                        final_path = fn

                # ✅ 關鍵：這行必須在 try 區塊的最末尾，確保不論如何都會發送 done 訊號
                self.msgq.put(("done", final_path))

            except yt_dlp.utils.DownloadCancelled:
                # 使用者取消下載，傳送 None 觸發 UI 重設但不彈通知
                self.msgq.put(("done", None))
            except Exception as e:
                # 發生錯誤，傳送錯誤資訊後觸發 UI 重設
                err_text = str(e)
                if "no video could be found in this tweet" in err_text.lower():
                    self.msgq.put(("no_tweet_video", err_text))
                else:
                    self.msgq.put(("error", f"download error：\n{err_text}"))
                
                # ✅ 錯誤發生也要傳送 done，UI 才會解除按鈕鎖定
                self.msgq.put(("done", None))
                traceback.print_exc()
        # 在啟動執行緒時，將 as_mp3 傳入 worker
        threading.Thread(target=lambda: worker(as_mp3), daemon=True).start()

        

    # 下載佇列
    def _drain_queue(self):
        try:
            while True:
                kind, payload = self.msgq.get_nowait()
                if kind == "meta":
                    self.title_var.set(f"title：{payload.get('title','—')}")
                    self.uploader_var.set(f"channel / uploader：{payload.get('uploader','—')}")
                    self.duration_var.set(f"length：{payload.get('duration','—')}")
                elif kind == "thumb":
                    self._set_thumb(payload)
                elif kind == "progress":
                    self.progress["value"] = payload.get("percent", 0.0)
                    self.percent_var.set(f"{payload.get('percent', 0.0):.1f}%")
                    self.speed_var.set(f"speed：{payload.get('speed','—')}")
                    self.eta_var.set(f"ETA：{payload.get('eta','—')}")
                    if payload.get("filename"):
                        self.file_var.set(f"filename：{payload['filename']}")
                elif kind == "done":
                    self.btn_download.configure(state=tk.NORMAL)
                    self.btn_download_mp3.configure(state=tk.NORMAL)
                    self.btn_stop.configure(state=tk.DISABLED)
                    if payload:
                        messagebox.showinfo("finished", f"download finished：\n{payload}")
                    self._reset_for_next()
                elif kind == "no_tweet_video":
                    # 若已有提示則先刪除
                    if hasattr(self, "cookie_hint") and self.cookie_hint.winfo_exists():
                        self.cookie_hint.destroy()

                    # 若 UI 剛重設，延遲整體顯示以免座標變成 0
                    def safe_show_cookie_hint():
                        try:
                            # 若按鈕不存在或介面被重設，直接跳過
                            if not hasattr(self, "cookie_button_ref"):
                                return
                            self.update_idletasks()

                            # 再建新提示框
                            self.cookie_hint = tk.Toplevel(self)
                            self.cookie_hint.overrideredirect(True)
                            self.cookie_hint.withdraw()  # ← 暫時隱藏，避免先出現在左上角
                            self.cookie_hint.attributes("-topmost", True)
                            self.cookie_hint.configure(bg="#fdf2f2", padx=10, pady=8)

                            msg = ttk.Label(
                                self.cookie_hint,
                                text="⬇ click here to choose cookie file",
                                background="#fdf2f2",
                                foreground="#c9302c",
                                font=("Segoe UI", 10, "bold"),
                                cursor="hand2",
                            )
                            msg.pack()
                            msg.bind("<Button-1>", lambda e: (self._pick_cookie(), self.cookie_hint.destroy()))

                            # 第二層延遲 — 等 Tk 完全布局完成後再定位
                            def position_hint():
                                try:
                                    self.update_idletasks()
                                    bx = self.cookie_button_ref.winfo_rootx()
                                    by = self.cookie_button_ref.winfo_rooty()
                                    bw = self.cookie_button_ref.winfo_width()
                                    hint_w = self.cookie_hint.winfo_width()
                                    hint_h = self.cookie_hint.winfo_height()
                                    x = bx + bw // 2 - hint_w // 2 + 60
                                    y = by - hint_h - 12
                                    self.cookie_hint.geometry(f"{hint_w}x{hint_h}+{x}+{y}")
                                    self.cookie_hint.deiconify()  # ✅ 完全定位後再顯示
                                    self.cookie_hint.lift()
                                    self.cookie_hint.after(4000, self.cookie_hint.destroy)
                                    self.bell()
                                except Exception as e:
                                    print("⚠️ Hint定位失敗:", e)

                            # 再延遲 800ms 等 layout 穩定
                            self.after(800, position_hint)

                        except Exception as e:
                            print("⚠️ safe_show_cookie_hint 例外:", e)

                    # 🔹 延遲 1.5 秒再呼叫整體氣泡建立
                    self.after(1500, safe_show_cookie_hint)
                elif kind == "error":
                    messagebox.showerror("error", payload)
                    self.btn_download.configure(state=tk.NORMAL)
                    self.btn_download_mp3.configure(state=tk.NORMAL)
                    self.btn_stop.configure(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.after(80, self._drain_queue)

    
    def _on_close(self):
        if messagebox.askokcancel("Exit", "Are you sure you want to close the program?"):
            save_config(self.config_data)
            self.destroy()


    # Reset helpers
    def _reset_dynamic_only(self):
        self.progress["value"] = 0
        self.percent_var.set(""); self.speed_var.set(""); self.eta_var.set("")
        self.file_var.set(""); self.title_var.set(""); self.uploader_var.set(""); self.duration_var.set("")
        self._clear_thumb()

    def _reset_for_next(self):
        self.stop_flag = False; self.last_filename = None
        self.url_var.set(""); #self.cookie_var.set("")
        self._reset_dynamic_only()
        self._set_dynamic_visible(False)
        self.url_entry.focus_set()
    
    
    def _pick_cookie(self):
        """選擇 cookie.txt 並記錄路徑到 config.json"""
        p = filedialog.askopenfilename(
            title="choose cookies.txt",
            filetypes=[("Netscape cookies.txt", "*.txt"), ("All files", "*.*")]
        )
        if not p:
            return
        self.cookie_var.set(p)
        # ✅ 將 cookie 路徑寫入共用設定
        self.config_data["cookie_path"] = p
        save_config(self.config_data)
        messagebox.showinfo("Success", f"Cookie file path saved:\n{p}")

    def _clear_cookie(self):
        self.cookie_var.set("")
        if "cookie_path" in self.config_data:
            del self.config_data["cookie_path"]
            save_config(self.config_data)
        messagebox.showinfo("Cleaned", "Cookie path cleared.")

    # Small helpers
    def _clear_thumb(self):
        self.preview_canvas.delete("all"); self.thumbnail_tk = None

    def _set_thumb(self, img: Image.Image | None):
        self._clear_thumb()
        if img is None: return
        target_w, target_h = 340, 190
        im = img.copy(); im.thumbnail((target_w, target_h), Image.LANCZOS)
        self.thumbnail_tk = ImageTk.PhotoImage(im)
        x = (target_w - im.width)//2; y = (target_h - im.height)//2
        self.preview_canvas.create_image(x, y, anchor="nw", image=self.thumbnail_tk)

    def _human_duration(self, seconds):
        if seconds is None: return "—"
        s = int(seconds); h, rem = divmod(s, 3600); m, s = divmod(rem, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

    def _hr_size(self, num):
        try: num = float(num)
        except Exception: return "-"
        for unit in ["B","KB","MB","GB","TB"]:
            if num < 1024: return f"{num:.1f} {unit}"
            num /= 1024.0
        return f"{num:.1f} PB"

    def _hr_eta(self, eta):
        if eta is None: return "—"
        try: s = int(eta)
        except Exception: return "—"
        h, rem = divmod(s, 3600); m, s = divmod(rem, 60)
        if h: return f"{h:d}h {m:02d}m {s:02d}s"
        if m: return f"{m:d}m {s:02d}s"
        return f"{s:d}s"