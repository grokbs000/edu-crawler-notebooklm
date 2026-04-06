# 🚀 國中教材 PDF 爬蟲 & NotebookLM 一鍵匯入助手 - 部署教學

本專案是一個基於 Streamlit 的網頁應用程式，專為台灣國中教育設計。以下是將此應用程式部署到 **Streamlit Community Cloud** 的完整步驟。

## 📦 專案結構
```text
edu-pdf-notebooklm/
├── app.py                # Streamlit 主程式
├── requirements.txt      # 必要套件清單
├── modules/              # 核心功能模組
│   ├── __init__.py
│   ├── search_engine.py  # 智慧搜尋引擎 (ddgs)
│   └── pdf_processor.py  # PDF 處理與文字擷取 (PyMuPDF)
└── .streamlit/
    └── config.toml       # Streamlit 介面設定
```

## 🛠️ 本地執行步驟
1. **複製專案檔案**到您的電腦。
2. **安裝 Python 3.10+**。
3. **安裝必要套件**：
   ```bash
   pip install -r requirements.txt
   ```
4. **啟動應用程式**：
   ```bash
   streamlit run app.py
   ```

## ☁️ 部署到 Streamlit Community Cloud
1. **上傳至 GitHub**：
   - 在 GitHub 上建立一個新的私有或公開儲存庫。
   - 將所有專案檔案上傳至該儲存庫。
2. **連接 Streamlit Cloud**：
   - 前往 [Streamlit Community Cloud](https://share.streamlit.io/)。
   - 點擊 "New app"。
   - 選擇您的 GitHub 儲存庫、分支（通常是 `main`）以及主程式檔案（`app.py`）。
3. **部署**：
   - 點擊 "Deploy!"。Streamlit 會自動安裝 `requirements.txt` 中的套件並啟動您的應用程式。

## 💡 使用小撇步
- **搜尋技巧**：輸入「國一數學 講義」即可自動搜尋多個教育入口網站。
- **NotebookLM 匯入**：擷取文字後，使用「⚡ 一鍵下載 + 開啟 NotebookLM」按鈕，檔案下載後直接拖進新開的 NotebookLM 視窗即可。
- **清理功能**：系統會自動移除 PDF 中的頁首、頁尾、頁碼與目錄，確保 AI 讀取到最純淨的教材內容。

---
*所有資源均來自公開教育網站，僅供學習使用。*
