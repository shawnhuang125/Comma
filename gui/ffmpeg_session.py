# gui/ffmpeg_session.py
import os, urllib.request, zipfile, threading, shutil
from utils.config_manager import save_config, load_config


class FFmpegSession:
    """FFmpeg 安裝、檢查與下載模組"""
    def __init__(self, app):
        self.app = app
        self.config = load_config()
        self.status_var = getattr(app, "ffmpeg_status", None)
        self.progressbar = getattr(app, "ffmpeg_progress", None)
        self.label = getattr(app, "ffmpeg_label", None)
        self.button = getattr(app, "btn_ffmpeg", None)
        self.ffmpeg_ok = False
        self.bin_path = None
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """檢查 FFmpeg 是否存在"""
        ffmpeg_path_cfg = self.config.get("ffmpeg_path")

        if ffmpeg_path_cfg and os.path.isdir(ffmpeg_path_cfg):
            os.environ["PATH"] = ffmpeg_path_cfg + os.pathsep + os.environ["PATH"]
            exec_path = shutil.which("ffmpeg")
            if exec_path:
                self._set_status(f"FFmpeg ready (from config): {exec_path}", ok=True)
                self.ffmpeg_ok = True
                return

        exec_path = shutil.which("ffmpeg")
        if exec_path:
            self._set_status(f"FFmpeg found at: {exec_path}", ok=True)
            self.ffmpeg_ok = True
        else:
            self._set_status("⚠️ FFmpeg not found — click 'Download FFmpeg' below.", ok=False)

    def _set_status(self, msg, ok=True):
        if self.status_var:
            self.status_var.set(msg)
        if self.label:
            self.label.configure(foreground=("green" if ok else "red"))

    def download_ffmpeg(self):
        """背景下載與解壓縮"""
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        zip_path = os.path.join(save_dir, "ffmpeg-release-essentials.zip")
        target_dir = os.path.join(save_dir, "ffmpeg")

        if self.button:
            self.button.configure(state="disabled")

        def worker():
            try:
                self._set_status("Downloading FFmpeg (0%)", ok=True)
                if self.progressbar:
                    self.progressbar["value"] = 0

                def _progress_hook(block_num, block_size, total_size):
                    downloaded = block_num * block_size
                    percent = min(downloaded / total_size * 100, 100) if total_size else 0
                    if self.progressbar:
                        self.progressbar["value"] = percent
                    mb_done = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    if self.status_var:
                        self.status_var.set(f"{percent:.1f}%  ({mb_done:.1f}/{mb_total:.1f} MB)")
                    self.app.update_idletasks()

                urllib.request.urlretrieve(url, zip_path, _progress_hook)
                self._set_status("Extracting FFmpeg...", ok=True)

                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(target_dir)

                extracted_root = next(
                    (os.path.join(target_dir, d) for d in os.listdir(target_dir)
                     if os.path.isdir(os.path.join(target_dir, d)) and "ffmpeg" in d),
                    None
                )
                if extracted_root:
                    bin_path = os.path.join(extracted_root, "bin")
                    self._finalize_ffmpeg(bin_path)
                else:
                    self._set_status("Extracted, but bin folder not found.", ok=False)

            except Exception as e:
                self._set_status(f"Download failed: {e}", ok=False)
            finally:
                if self.button:
                    self.button.configure(state="normal")
                if os.path.exists(zip_path):
                    os.remove(zip_path)

        threading.Thread(target=worker, daemon=True).start()

    def _finalize_ffmpeg(self, bin_path):
        """解壓完成後寫入設定"""
        self.bin_path = bin_path
        self.ffmpeg_ok = True
        self._set_status(f"FFmpeg ready at: {bin_path}", ok=True)
        self.config["ffmpeg_path"] = bin_path
        save_config(self.config)
        os.environ["PATH"] = bin_path + os.pathsep + os.environ["PATH"]
        if self.progressbar:
            self.progressbar["value"] = 100
        if self.button:
            self.button.configure(state="disabled")
