# utils/style.py
import ttkbootstrap as tb

def setup_style(root):
    """初始化 ttkbootstrap 主題樣式"""
    style = tb.Style("pulse")  # 預設主題，可改成 "darkly"、"superhero" 等
    root.style = style
    return style
