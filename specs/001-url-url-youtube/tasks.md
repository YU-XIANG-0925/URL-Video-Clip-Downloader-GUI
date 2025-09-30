# Tasks: 多格式影片片段下載器

**主題分支**: `001-url-url-youtube`
**規格**: `specs/001-url-url-youtube/spec.md`

---

## 任務產生策略

本文件是根據 `plan.md` 中定義的設計自動產生的。任務按依賴關係排序。

- **TDD 流程**: 測試任務先於實作任務。
- **依賴順序**: 模型 -> 服務 -> UI。
- **並行執行**: 標有 `[P]` 的任務可以並行執行。

---

## Phase 1: 專案設定 (T001-T003)

這些任務只需執行一次，用於設定專案骨架和環境。

### T001: 初始化 Python 虛擬環境
- **Status**: Done
- **檔案**: `(根目錄)`
- **命令**: `uv venv`
- **描述**: 在專案根目錄建立一個新的虛擬環境。

### T002: 安裝依賴套件
- **Status**: Done
- **檔案**: `(根目錄)`
- **命令**: `uv pip install yt-dlp`
- **描述**: 安裝影片下載所需的核心依賴套件 `yt-dlp`。

### T003: 建立專案結構
- **Status**: Done
- **檔案**: `src/main.py`, `src/gui.py`, `src/downloader.py`, `tests/test_downloader.py`
- **描述**: 建立空的 Python 檔案以定義應用程式的結構。

---

## Phase 2: 核心實作 (T004-T010)

此階段著重於根據 TDD 原則建構核心功能。

### T004: [P] 定義 `DownloadJob` 資料類別
- **Status**: Done
- **檔案**: `src/downloader.py`
- **描述**: 根據 `data-model.md`，建立 `DownloadJob` dataclass 來儲存所有與下載任務相關的資訊。

### T005: [P] 為下載器邏輯編寫單元測試
- **Status**: Done
- **檔案**: `tests/test_downloader.py`
- **描述**: 為 `downloader.py` 中的核心功能編寫 `pytest` 測試，包括模擬 `yt-dlp` 和 `ffmpeg` 的呼叫。

### T006: 實作核心下載邏輯
- **Status**: Done
- **檔案**: `src/downloader.py`
- **依賴**: T004, T005
- **描述**: 實作 `start_download` 函式，該函式接收一個 `DownloadJob` 物件並使用 `yt-dlp` 或 `ffmpeg` 執行下載和剪輯。

### T007: 建立基本 GUI 佈局
- **Status**: Done
- **檔案**: `src/gui.py`
- **描述**: 使用 Tkinter 建立主應用程式視窗，包含 `spec.md` 中定義的所有 UI 元件 (URL 輸入、時間輸入、檔案路徑等)。

### T008: 實作 GUI 輸入處理
- **Status**: Done
- **檔案**: `src/gui.py`
- **依賴**: T007
- **描述**: 為 UI 元件新增事件監聽器，以收集使用者輸入並在點擊按鈕時建立一個 `DownloadJob` 實例。

### T009: 整合 GUI 與下載器
- **Status**: Done
- **檔案**: `src/gui.py`, `src/main.py`
- **依賴**: T006, T008
- **描述**: 在 `main.py` 中啟動 GUI。修改 `gui.py`，使「開始轉換」按鈕在一個單獨的執行緒中呼叫 `downloader.start_download`，以避免凍結 UI。

### T010: 在 GUI 中實作進度回報
- **Status**: Done
- **檔案**: `src/gui.py`
- **依賴**: T009
- **描述**: 更新 GUI 以顯示進度條和狀態文字，反映 `downloader` 回傳的下載進度。

---

## Phase 3: 優化與完成 (T011-T014)

此階段專注於錯誤處理、邊界案例和文件。

### T011: [P] 實作錯誤處理
- **Status**: Done
- **檔案**: `src/gui.py`, `src/downloader.py`
- **描述**: 新增穩健的錯誤處理機制，以處理無效的 URL、網路錯誤以及 `yt-dlp`/`ffmpeg` 失敗的情況，並在 GUI 中顯示清晰的錯誤訊息。

### T012: [P] 實作檔案存在檢查
- **Status**: Done
- **檔案**: `src/downloader.py`
- **描述**: 在儲存檔案之前，檢查檔案是否已存在。如果存在，則在檔名中附加一個數字 (例如 `video(1).mp4`)。

### T013: [P] 實作下載佇列
- **Status**: Done
- **檔案**: `src/gui.py`, `src/downloader.py`
- **描述**: 實作一個簡單的佇列系統，一次只處理一個下載任務。如果使用者在下載過程中啟動新任務，則將其新增到佇列中。

### T014: 編寫專案文件
- **Status**: Done
- **檔案**: `README.md`
- **描述**: 更新 `README.md`，包含專案的詳細說明、安裝步驟和使用指南。

---

## 並行執行指南

標有 `[P]` 的任務可以並行執行以加快開發速度。

**範例**:
可以同時開始 `T004` 和 `T005`。

```
(Terminal 1)
/gemini --task T004

(Terminal 2)
/gemini --task T005
```
