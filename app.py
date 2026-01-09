# app.py 內容
import sys
import os

# 這一行是為了確保能找到 gui 資料夾
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import App

if __name__ == "__main__":
    app = App()
    app.mainloop()