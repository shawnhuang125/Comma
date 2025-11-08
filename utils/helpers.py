from tkinter import ttk

def make_card(parent, pad=14):
    shadow = ttk.Frame(parent, style="Shadow.TFrame")
    shadow.pack(fill="x")
    card = ttk.Frame(shadow, style="Card.TFrame", padding=pad)
    card.pack(fill="x", padx=2, pady=2)
    return shadow, card


# === 其他共用格式化函式 ===

def human_duration(seconds):
    """把秒數轉成人類可讀時間格式"""
    if seconds is None:
        return "—"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def hr_size(num):
    """把位元組數轉成 KB/MB/GB 顯示"""
    try:
        num = float(num)
    except Exception:
        return "-"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def hr_eta(eta):
    """把秒數轉成 ETA 格式"""
    if eta is None:
        return "—"
    try:
        s = int(eta)
    except Exception:
        return "—"
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}h {m:02d}m {s:02d}s"
    if m:
        return f"{m:d}m {s:02d}s"
    return f"{s:d}s"
