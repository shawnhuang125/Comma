#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from gui.main_window import App

def main():
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        print(f"[Critical Error] Application crashed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()