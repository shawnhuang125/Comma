# X.com Audio Converter

一款基於 **Python + Tkinter + yt_dlp + FFmpeg** 的桌面應用程式，  
可將 X（前身為 Twitter）影片自動下載並轉換為MP4檔案。  
支援自定義輸出資料夾、即時下載進度顯示與錯誤提示。

---

## 功能特色
- 支援 X.com / Twitter 影片連結下載  
- 自動擷取最高音質音訊流  
- 可選輸出資料夾與檔案命名  
- 內建 GUI 介面（Tkinter）  
- 下載進度條與速度顯示  
- 打包成單一 EXE 檔（可離線執行）

---

## 安裝方式

### 下載專案
```bash
git clone https://github.com/你的帳號/X-Audio-Converter.git
cd X-Audio-Converter
```

### 建立與啟動虛擬環境
```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 安裝依賴套件
```bash
pip install -r requirements.txt
```

若尚未建立 `requirements.txt`，可用以下指令產生：
```bash
pip freeze > requirements.txt
```

---

## 安裝 FFmpeg

程式執行前必須安裝 [FFmpeg](https://ffmpeg.org/download.html)。

### Windows 使用者
1. 下載 FFmpeg 壓縮檔（建議使用 [Gyan.dev 版本](https://www.gyan.dev/ffmpeg/builds/)）。  
2. 解壓縮後將 `bin` 目錄路徑加入系統環境變數 `PATH`。  
3. 重新啟動終端機並確認是否安裝成功：
   ```bash
   ffmpeg -version
   ```

### macOS / Linux 使用者
```bash
brew install ffmpeg    # macOS
sudo apt install ffmpeg  # Ubuntu / Debian
```

---

## 執行程式
```bash
python app.py
```

若要打包為 EXE：
```bash
pyinstaller --noconsole --onefile --icon=icon.ico app.py
```

打包完成後的執行檔會在 `dist/` 資料夾中。

---

## 授權條款
本專案採用 MIT License。  
可自由修改與分發，惟請保留原作者資訊。

---

>  **作者註記：**
> 若要包成 EXE 發佈，可將 `cookies.json` 與 `ffmpeg.exe` 一併放入執行檔同層資料夾中，  
> 以確保下載功能正常運作。
