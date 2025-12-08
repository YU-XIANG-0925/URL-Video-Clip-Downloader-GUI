# URL Video Clip Downloader GUI (影片片段下載器)

這是一個簡單的圖形化介面 (GUI) 應用程式，用於從包含 YouTube 在內的各種 URL 下載影片片段，並提供影片轉檔與合併功能。

## 功能特色

### 📥 下載器 (Downloader)
- **URL 下載**: 支援從各種影音平台 (透過 `yt-dlp`) 下載影片。
- **片段剪輯**: 指定開始與結束時間 (格式：HH:MM:SS)，僅下載所需的影片片段。
- **本地檔案剪輯**: 亦支援對本地影片檔案進行時間軸剪輯。
- **格式選擇**: 可選擇影片編碼 (如 H.264, H.265/HEVC, NVENC, AMF, QSV) 與音訊編碼。
- **低 VRAM 模式**: 提供針對低顯存環境的優化選項。

### 🔄 重編碼器 (Re-encoder)
- **格式轉換**: 將影片轉換為不同的編碼或容器格式 (MP4, MKV, AVI 等)。
- **批次處理**: 支援單一檔案或整個目錄的批次轉檔。
- **硬體加速**: 支援 NVIDIA (NVENC), AMD (AMF), Intel (QSV) 等硬體加速編碼。
- **資源回收**: 可選擇在轉檔成功後，自動將原始檔案移至資源回收桶。

### 🎞️ 合併器 (Merger)
- **影片合併**: 將多個影片片段無損合併為一個檔案。
- **輸入選擇**: 可選擇多個特定檔案或指定目錄下的所有影片進行合併。
- **資源回收**: 可選擇在合併成功後，自動將原始檔案移至資源回收桶。

### ⚙️ 其他功能
- **任務控制**: 支援下載、轉檔與合併任務的 **暫停**、**恢復** 與 **停止**。
- **佇列系統**: 簡單的佇列系統來處理多個下載任務。
- **進度顯示**: 即時顯示處理進度條與狀態更新。

## 系統需求

- Python 3.11 或更高版本。
- `uv` 套件管理器。
- 系統路徑 (PATH) 中需安裝並設定 `FFmpeg`。

## 安裝說明

1.  **複製儲存庫**

    ```bash
    git clone https://github.com/your-username/URL-Video-Clip-Downloader-GUI.git
    cd URL-Video-Clip-Downloader-GUI
    ```

2.  **建立虛擬環境**

    ```bash
    uv venv
    ```

3.  **啟用虛擬環境**

    Windows:
    ```bash
    .venv\Scripts\activate
    ```

    macOS 和 Linux:
    ```bash
    source .venv/bin/activate
    ```

4.  **安裝依賴套件**

    ```bash
    uv pip install -r requirements.txt
    ```

## 使用方法

1.  **執行應用程式**

    ```bash
    python src/main.py
    ```

2.  **選擇功能分頁**:
    - **Downloader**: 輸入 URL、設定時間範圍與輸出格式後點擊 "Start Download"。
    - **Re-encoder**: 選擇來源檔案/目錄與輸出設定，點擊 "Start Re-encode"。
    - **Merger**: 加入多個影片片段，設定輸出檔名，點擊 "Start Merge"。

## 貢獻

歡迎提交 Pull Request。對於重大變更，請先開啟 Issue 討論您想要更改的內容。

## 授權

[MIT](https://choosealicense.com/licenses/mit/)
