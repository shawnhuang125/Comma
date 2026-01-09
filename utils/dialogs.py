import tkinter as tk
from tkinter import ttk
import os

class AskRenameDialog(tk.Toplevel):
    def __init__(self, parent, filepath):
        super().__init__(parent)
        self.title("File Already Exists")
        self.result = ("cancel", None)  # 預設回傳格式: (動作, 後綴字串)
        
        filename = os.path.basename(filepath)
        
        # 設定視窗大小
        w, h = 420, 350
        self.geometry(f"{w}x{h}")
        self.resizable(False, False)
        
        # === 視窗置中邏輯 ===
        try:
            if parent:
                px, py = parent.winfo_rootx(), parent.winfo_rooty()
                pw, ph = parent.winfo_width(), parent.winfo_height()
                x = px + (pw - w) // 2
                y = py + (ph - h) // 2
            else:
                sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
                x = (sw - w) // 2
                y = (sh - h) // 2
            self.geometry(f"+{x}+{y}")
        except:
            pass

        # === 介面佈局 ===
        container = ttk.Frame(self, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # 提示訊息
        msg = (
            f"The file already exists:\n{filename}\n\n"
            "If downloading the same video, please enter a suffix (e.g. '_1') to rename.\n"
            "What would you like to do?"
        )
        lbl_msg = ttk.Label(
            container, 
            text=msg, 
            wraplength=380, 
            justify="left",
            font=("Segoe UI", 10)
        )
        lbl_msg.pack(fill=tk.X, pady=(0, 15))

        # --- 區域 1: 重新命名 (Rename) ---
        group_rename = ttk.LabelFrame(container, text="Option 1: Rename", padding=10)
        group_rename.pack(fill=tk.X, pady=(0, 10))

        # 輸入框 (預設後綴 _1)
        self.suffix_var = tk.StringVar(value="_1")
        self.entry = ttk.Entry(group_rename, textvariable=self.suffix_var, width=12)
        self.entry.pack(side=tk.LEFT, padx=(0, 10))
        # 綁定 Enter 鍵直接觸發重新命名
        self.entry.bind("<Return>", lambda e: self.on_rename())

        btn_rename = ttk.Button(
            group_rename, 
            text="Rename", 
            command=self.on_rename,
            style="Accent.TButton" # 假設你有設定 Accent style，若無則會顯示為普通按鈕
        )
        btn_rename.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- 區域 2: 覆寫或取消 ---
        frame_actions = ttk.Frame(container)
        frame_actions.pack(fill=tk.X, side=tk.BOTTOM)

        btn_overwrite = ttk.Button(frame_actions, text="Overwrite Existing", command=self.on_overwrite)
        btn_overwrite.pack(side=tk.LEFT)

        btn_cancel = ttk.Button(frame_actions, text="Cancel", command=self.on_cancel)
        btn_cancel.pack(side=tk.RIGHT)

        # 設定為模態視窗 (Modal) - 強制使用者必須回應
        self.transient(parent)
        self.grab_set()
        self.entry.focus_set() # 預設聚焦在輸入框，方便使用者直接打字
        self.wait_window(self)

    def on_rename(self):
        suffix = self.suffix_var.get().strip()
        if not suffix:
            suffix = "_new" # 防止使用者輸入空白
        self.result = ("rename", suffix)
        self.destroy()

    def on_overwrite(self):
        self.result = ("overwrite", None)
        self.destroy()

    def on_cancel(self):
        self.result = ("cancel", None)
        self.destroy()

# 這是給 app.py 呼叫的函式
def ask_overwrite_or_rename(parent, filepath):
    """
    Returns:
        tuple: (action_string, suffix_string)
        action_string: "rename", "overwrite", or "cancel"
    """
    dialog = AskRenameDialog(parent, filepath)
    return dialog.result

# 保留舊的函式以免其他地方報錯 (選擇性保留)
def custom_yesno(title, message, yes_text="Yes", no_text="No", parent=None):
    return tk.messagebox.askyesno(title, message, parent=parent)