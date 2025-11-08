import tkinter as tk
from tkinter import ttk

def custom_yesno(title, message, yes_text="Yes", no_text="No", parent=None):
    result = {"choice": None}
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("320x200")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.lift()
    dialog.attributes('-topmost', True)
    dialog.after_idle(dialog.attributes, '-topmost', False)
    dialog.update_idletasks()
    if parent:
        parent_x, parent_y = parent.winfo_rootx(), parent.winfo_rooty()
        parent_w, parent_h = parent.winfo_width(), parent.winfo_height()
        win_w, win_h = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        x = parent_x + (parent_w // 2 - win_w // 2)
        y = parent_y + (parent_h // 2 - win_h // 2)
    else:
        screen_w, screen_h = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
        win_w, win_h = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        x = (screen_w // 2) - (win_w // 2)
        y = (screen_h // 2) - (win_h // 2)
    dialog.geometry(f"+{x}+{y}")

    ttk.Label(dialog, text=message, wraplength=260, justify="center").pack(pady=20)
    btn_frame = ttk.Frame(dialog); btn_frame.pack(pady=10)
    def choose(value):
        result["choice"] = value
        dialog.destroy()
    ttk.Button(btn_frame, text=yes_text, command=lambda: choose(True)).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text=no_text, command=lambda: choose(False)).pack(side=tk.RIGHT, padx=10)
    dialog.wait_window()
    return result["choice"]
