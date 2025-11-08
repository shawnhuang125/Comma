#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, io, threading, queue, traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import requests, yt_dlp
import json
import shutil
COOKIE_FILE = os.path.join(os.path.dirname(__file__), "cookies.json")

APP_TITLE = "X.com Audio Converter"

# 錯誤提示框
def custom_yesno(title, message, yes_text="Yes", no_text="No", parent=None):
    result = {"choice": None}

    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("320x200")
    dialog.resizable(False, False)
    dialog.transient(parent)   # 讓對話框浮在主視窗上
    dialog.grab_set()          # 鎖定焦點（模態）
    dialog.lift()
    dialog.attributes('-topmost', True)
    dialog.after_idle(dialog.attributes, '-topmost', False)

    # -------------- 🔹置中視窗（關鍵）--------------
    dialog.update_idletasks()
    if parent:
        # 取得主視窗的位置與大小
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        # 取得對話框的寬高
        win_w = dialog.winfo_reqwidth()
        win_h = dialog.winfo_reqheight()
        # 計算置中位置
        x = parent_x + (parent_w // 2 - win_w // 2)
        y = parent_y + (parent_h // 2 - win_h // 2)
    else:
        # 若沒有 parent，就置中於螢幕中央
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        win_w = dialog.winfo_reqwidth()
        win_h = dialog.winfo_reqheight()
        x = (screen_w // 2) - (win_w // 2)
        y = (screen_h // 2) - (win_h // 2)
    dialog.geometry(f"+{x}+{y}")
    # -----------------------------------------------

    ttk.Label(dialog, text=message, wraplength=260, justify="center").pack(pady=20)

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=10)

    def choose(value):
        result["choice"] = value
        dialog.destroy()

    ttk.Button(btn_frame, text=yes_text, command=lambda: choose(True)).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text=no_text, command=lambda: choose(False)).pack(side=tk.RIGHT, padx=10)

    dialog.wait_window()
    return result["choice"]


# GUI STYLE
def setup_style(root):
    import ttkbootstrap as tb
    style = tb.Style("pulse")  # 預設主題
    root.style = style
    return style

# ---------- Card helper (no place, only pack) ----------
def make_card(parent, pad=14):
    """回傳 (shadow, card)。要顯示/隱藏時以 shadow 為單位操作。"""
    shadow = ttk.Frame(parent, style="Shadow.TFrame")
    shadow.pack(fill=tk.X)
    card = ttk.Frame(shadow, style="Card.TFrame", padding=pad)
    # 以內外層+邊距模擬陰影/層次
    card.pack(fill=tk.X, padx=2, pady=2)
    return shadow, card

# GUI APPLICATION初始化與運行
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.temp_files = []  # 記錄正在下載的暫存檔 (.part)
        self.title(APP_TITLE)
        # GUI 內狀態提示字串
        self.ffmpeg_status = tk.StringVar(value="Checking FFmpeg...")

        # 檢查 FFmpeg 是否可用
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            self.ffmpeg_status.set(f"FFmpeg found at: {ffmpeg_path}")
            self.ffmpeg_ok = True
        else:
            self.ffmpeg_status.set("FFmpeg not found. Please install FFmpeg before downloading.")
            self.ffmpeg_ok = False


        # 設定程式圖示（使用 PNG）
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "repost.png")
            if os.path.exists(icon_path):
                icon_img = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, icon_img)  # 使用 iconphoto() 載入 PNG
            else:
                print("can not find icon.png")
        except Exception as e:
            print(f"can not load icon：{e}")

        self.minsize(780, 480)

        import ttkbootstrap as tb
        self.style = setup_style(self)
        self.themed_frame = tb.Frame(self)  # 讓 ttkbootstrap 接管
        self.themed_frame.pack(fill=tk.BOTH, expand=True)

        # state
        self.msgq = queue.Queue()
        self.stop_flag = False
        self.thumbnail_tk = None
        self.last_filename = None
        self.output_dir = ""
        # 載入 cookie 記錄
        self.saved_cookie = self._load_cookie()
        setup_style(self)
        self._build_ui()
        self.after(80, self._drain_queue)
    
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
            self.title_frame, text="x.com Audio Converter",
            font=("Segoe UI", 14, "bold")
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ttk.Label(
            self.title_frame,
            text="Preview and progress shown; auto-clear on completion.",
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
        ttk.Button(row2, text="Choose File", command=self._pick_cookie).pack(side=tk.LEFT, padx=(6,2))
        ttk.Button(row2, text="Clear", command=self._clear_cookie).pack(side=tk.LEFT, padx=(2,16))

        ttk.Label(row2, text="Output Folder：").pack(side=tk.LEFT)
        self.outdir_var = tk.StringVar(value=self.output_dir)
        ttk.Entry(row2, textvariable=self.outdir_var, width=34).pack(side=tk.LEFT)
        ttk.Button(row2, text="Choose Folder", command=self._pick_outdir).pack(side=tk.LEFT, padx=(8,0))

        # 下載按鈕
        row3 = ttk.Frame(input_card); row3.pack(fill=tk.X, pady=(4,0))
        self.btn_download = ttk.Button(row3, text="Download MP4",
                                       command=self.on_download, style="Accent.TButton")
        #停止按鈕
        self.btn_download.pack(side=tk.LEFT)
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

        # === FFmpeg 狀態列 ===
        status_bar = ttk.Frame(self, padding=(12, 4))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(
            status_bar,
            textvariable=self.ffmpeg_status,
            foreground=("green" if self.ffmpeg_ok else "red"),
            font=("Segoe UI", 9, "italic")
        ).pack(side=tk.LEFT)

    # ------- show/hide dynamic by shadow frame -------
    def _set_dynamic_visible(self, visible: bool):
        if visible:
            self.dynamic_shadow.pack(fill=tk.X)
        else:
            self.dynamic_shadow.pack_forget()

    # ---------------- Events ----------------
    def _pick_cookie(self):
        p = filedialog.askopenfilename(
            title="choose cookies.txt",
            filetypes=[("Netscape cookies.txt", "*.txt"), ("All files", "*.*")]
        )
        if p: self.cookie_var.set(p)

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
                for ext in ["", ".part", ".ytdl", ".temp", ".temp.mp4"]:
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

    def on_download(self):
        if not self.ffmpeg_ok:
            messagebox.showwarning(
                "FFmpeg Missing",
                "FFmpeg is not installed.\nPlease install it first before downloading."
            )
            return  # return 才會停止執行

        # 檢查 URL
        url = (self.url_var.get() or "").strip()
        if not url:
            messagebox.showwarning("Prompt:", "Please enter the video URL first.")
            return

        # 檢查輸出資料夾
        outdir = (self.outdir_var.get() or "").strip()
        if not outdir:
            messagebox.showwarning("Missing Folder", "Please select an output folder before downloading.")
            return

        os.makedirs(outdir, exist_ok=True)

        # 檢查是否已有同名影片
        try:
            info_opts = {
                "quiet": True,
                "no_warnings": True,
                "cookiefile": self.cookie_var.get().strip() or None,
                "noplaylist": True,
                # 加上完整 outtmpl 與 paths
                "outtmpl": "%(title)s.%(ext)s",
                "paths": {"home": outdir},  # 關鍵：讓 prepare_filename 指向正確資料夾
            }

            with yt_dlp.YoutubeDL(info_opts) as y:
                info = y.extract_info(url, download=False)
                expected_name = y.prepare_filename(info)

            # 現在 expected_name 一定是實際路徑，例如 D:\Downloads\myvideo.mp4
            if os.path.exists(expected_name):
                ans = custom_yesno(
                    "File has already exists.",
                    f"Detected Same File：\n\n{os.path.basename(expected_name)}\n\n要覆寫這個檔案嗎？",
                    yes_text="overwrite",
                    no_text="cancel",
                    parent=self   # 指定父視窗
                )
                if not ans:
                    return  # 使用者選擇取消
                else:
                    try: 
                        os.remove(expected_name)
                    except Exception as e:
                        messagebox.showerror("Error", f"Cannot delete old file:\n{e}")
                        return
        except Exception as e:
            print(f"File pre-check failed: {e}")


        cookie_path = self.cookie_var.get().strip() or None

        # reset for a run
        self.stop_flag = False
        self.btn_download.configure(state=tk.DISABLED)
        self.btn_stop.configure(state=tk.NORMAL)
        self._reset_dynamic_only()
        self._set_dynamic_visible(True)

        def worker():
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
                    "title": title,
                    "uploader": uploader,
                    "duration": self._human_duration(duration)
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

                # real download
                ydl_opts = {
                    "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
                    "cookiefile": self.cookie_var.get().strip() or None,
                    "noplaylist": True,
                    "merge_output_format": "mp4",
                    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "progress_hooks": [progress_hook],
                    "postprocessors": [
                        {"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"},
                        {"key": "FFmpegMetadata"},
                    ],
                    "quiet": True, "no_warnings": True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as y:
                    info2 = y.extract_info(url, download=True)
                    fn = y.prepare_filename(info2)
                    base, _ = os.path.splitext(fn)
                    final_path = base + ".mp4"

                self.msgq.put(("done", final_path))

            except yt_dlp.utils.DownloadCancelled:
                self.msgq.put(("done", None))
            except Exception as e:
                self.msgq.put(("error", f"download error：\n{e}"))
                self.msgq.put(("done", None))
                traceback.print_exc()

        threading.Thread(target=worker, daemon=True).start()

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
                    self.btn_stop.configure(state=tk.DISABLED)
                    if payload:
                        messagebox.showinfo("finished", f"download finished：\n{payload}")
                    self._reset_for_next()
                elif kind == "error":
                    messagebox.showerror("error", payload)
        except queue.Empty:
            pass
        self.after(80, self._drain_queue)

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

    def _load_cookie(self):
        """啟動時讀取 cookie 路徑"""
        if os.path.exists(COOKIE_FILE):
            try:
                with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("cookie_path", "")
            except Exception:
                return ""
        return ""
    
    
    def _pick_cookie(self):
        """選擇 cookie.txt 並記錄路徑"""
        p = filedialog.askopenfilename(
            title="choose cookies.txt",
            filetypes=[("Netscape cookies.txt", "*.txt"), ("All files", "*.*")]
        )
        if not p:
            return
        self.cookie_var.set(p)
        try:
            with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                json.dump({"cookie_path": p}, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("successed", f"Cookie file path has stored：\n{p}")
        except Exception as e:
            messagebox.showerror("error", f"can not store Cookie file path：{e}")

    def _clear_cookie(self):
        """清除記錄"""
        self.cookie_var.set("")
        if os.path.exists(COOKIE_FILE):
            os.remove(COOKIE_FILE)
        messagebox.showinfo("clean finished", "Cookie file has finished。")



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

def main():
    App().mainloop()

if __name__ == "__main__":
    main()
