# 功能規格：多格式影片片段下載器

**功能分支**：`001-url-url-youtube`  
**建立日期**：2025年10月1日  
**狀態**：草稿  
**輸入**：使用者描述："我現在要建立一個可以輸入url、起始時間、結束時間、儲存路徑、輸出檔名，以及"開始轉換"按鈕的多格式影片下載器，他要讓使用者可以輸入各種影片的URL甚至包含YouTube影片的連結，並透過輸入起始時間和結束時間讓下載程式知道要下載的影片片段，當起始時間未輸入時默認為0，當結束時間未輸入時默認為不需要設定結束時間，再透過儲存路徑和輸出檔名來決定要將下載下來的影片存在哪裡"

---

## ⚡ 快速指引
- ✅ 專注於使用者需要什麼 (WHAT) 以及為什麼 (WHY)
- ❌ 避免如何實作 (HOW) (不含技術堆疊、API、程式碼結構)
- 👥 為業務相關人員而非開發人員編寫

---
## Clarifications
### Session 2025-10-01
- Q: When the start time is later than the end time, how should the system respond? → A: Automatically swap the start and end times.
- Q: What output video formats should be supported? The description mentions "multi-format". → A: Let the user choose from a list of formats.
- Q: Which formats should be included in the list for the user to choose from? → A: MP4, WebM, MKV
- Q: How should the system handle video URLs that require a login or are behind a paywall? → A: Display an error message stating that protected content is not supported.
- Q: How should the system handle incorrect time formats like "abc"? → A: Use a spinbox or similar UI control for time input (HH:MM:SS) to prevent invalid formats, making a specific error message for format validation unnecessary.
- Q: If the output file already exists, how should the system proceed? → A: Append a number to the filename (e.g., my-clip(1).mp4).
- Q: How should the system indicate progress during download/processing? → A: Use a combination of a progress bar with percentage and detailed text updates (e.g., "Downloading: 50MB / 100MB").
- Q: What should happen if a download is interrupted by network loss? → A: Automatically try to reconnect and resume, retrying up to 3 times.
- Q: Should the application support concurrent downloads or a queue? → A: Process only one download task at a time (a queue).

---

## 使用者場景與測試 *(強制性)*

### 主要使用者故事
作為一個使用者，我想要能夠提供一個影片的 URL、指定一個時間範圍，然後下載該影片的特定片段，並將其儲存為我指定的檔案名稱和位置，這樣我就可以輕鬆地從線上影片中擷取我需要的片段。

### 驗收場景
1.  **假設** 使用者在介面中輸入了有效的 YouTube 影片 URL、起始時間 "00:01:30"、結束時間 "00:02:00"、儲存路徑 "D:\Downloads" 以及輸出檔名 "my-clip.mp4"，**當** 使用者點擊 "開始轉換" 按鈕，**則** 系統應下載指定的影片片段，並將其儲存為 "D:\Downloads\my-clip.mp4"。
2.  **假設** 使用者輸入了有效的影片 URL，但將起始時間留空，並設定了結束時間，**當** 使用者點擊 "開始轉換" 按鈕，**則** 系統應從影片的開頭 (00:00:00) 開始下載，直到指定的結束時間。
3.  **假設** 使用者輸入了有效的影片 URL 和起始時間，但將結束時間留空，**當** 使用者點擊 "開始轉換" 按鈕，**則** 系統應從指定的起始時間開始下載，直到影片的結尾。
4.  **假設** 使用者未輸入儲存路徑或輸出檔名，**當** 使用者點擊 "開始轉換" 按鈕，**則** 系統應顯示錯誤訊息，提示使用者必須指定儲存位置和檔案名稱。
5.  **假設** 使用者輸入了無效的 URL，**當** 使用者點擊 "開始轉換" 按鈕，**則** 系統應顯示錯誤訊息，指出 URL 無效或無法存取。
6.  **假設** 一個下載正在進行中，**當** 使用者查看介面，**則** 系統應顯示一個進度條和描述目前狀態的文字 (例如，"正在下載..." 或 "正在轉換格式...")。
7.  **假設** 一個下載任務正在進行中，**當** 使用者啟動第二個下載任務，**則** 第二個任務應進入「等待中」狀態，直到第一個任務完成。

### 邊界案例
- 當輸入的起始時間晚於結束時間時，系統會自動交換時間。
- 時間輸入將透過專門的 UI 控制項 (例如，spinbox) 進行，以防止輸入無效格式。
- 當影片 URL 需要登入或付費時，系統會顯示錯誤訊息，說明不支援受保護的內容。
- 使用者將能夠從一個預定義的清單中選擇輸出格式。
- 如果輸出檔案已存在，系統會自動在檔名中添加數字後綴 (例如，`my-clip(1).mp4`)。
- 如果下載因網路問題中斷，系統將自動嘗試重新連線並續傳，最多重試 3 次。

---

## 需求 *(強制性)*

### 功能性需求
- **FR-001**：系統必須提供一個圖形化使用者介面 (GUI)，其中包含影片 URL 的文字輸入、用於選擇起始與結束時間的 UI 控制項 (spinbox)、儲存路徑和輸出檔名的文字輸入。
- **FR-002**：系統必須接受並處理多種影片來源的 URL，包含但不限於 YouTube。
- **FR-003**：使用者必須能夠透過 "開始轉換" 按鈕觸發影片下載與剪輯流程。
- **FR-004**：系統必須能夠根據使用者輸入的起始時間和結束時間剪輯影片。
- **FR-005**：如果使用者未提供起始時間，系統必須預設從影片的 0 秒開始。
- **FR-006**：如果使用者未提供結束時間，系統必須剪輯到影片的結尾。
- **FR-007**：系統必須將處理完成的影片儲存到使用者指定的儲存路徑和輸出檔名。
- **FR-008**：系統必須在必要欄位 (如 URL、儲存路徑、輸出檔名) 未填寫時，向使用者顯示明確的錯誤提示。
- **FR-009**：系統必須在處理無效或無法存取的 URL 時，向使用者顯示錯誤訊息。
- **FR-010**：系統必須允許使用者從一個支援的格式清單 (MP4, WebM, MKV) 中選擇輸出檔案的格式。
- **FR-011**：如果使用者指定的輸出檔案已存在，系統必須自動為新檔案重新命名以避免覆蓋 (例如，附加一個數字後綴)。
- **FR-012**：在下載和處理過程中，系統必須向使用者顯示進度，包含一個總體進度條 (含百分比) 和詳細的狀態文字 (例如，"正在下載: 50MB / 100MB")。
- **FR-013**：當下載因網路中斷而失敗時，系統必須自動嘗試重新連線並從中斷點續傳。在將任務標記為失敗之前，最多應重試 3 次。
- **FR-014**：系統一次只能處理一個下載任務。如果使用者在一個任務正在進行時啟動新任務，新任務將被加入到佇列中，並在目前任務完成後開始。

### 關鍵實體 *(若功能涉及資料則包含)*
- **下載任務 (Download Job)**：代表一個使用者請求的下載與剪輯操作。屬性包含：來源 URL、起始時間、結束時間、儲存路徑、輸出檔名、狀態 (例如，等待中、處理中、完成、失敗)、重試次數。

---

## 審查與驗收檢查清單
*閘門：在 main() 執行期間運行的自動化檢查*

### 內容品質
- [ ] 沒有實作細節 (語言、框架、API)
- [ ] 專注於使用者價值與業務需求
- [ ] 為非技術相關人員編寫
- [ ] 所有強制性章節皆已完成

### 需求完整性
- [ ] 沒有殘留的 [需要釐清] 標記
- [ ] 需求是可測試且無歧義的
- [ ] 成功標準是可衡量的
- [ ] 範圍已明確界定
- [ ] 已識別依賴關係與假設

---

## 執行狀態
*由 main() 在處理期間更新*

- [ ] 已解析使用者描述
- [ ] 已提取關鍵概念
- [ ] 已標記模糊之處
- [ ] 已定義使用者場景
- [ ] 已產生需求
- [ ] 已識別實體
- [ ] 已通過審查檢查清單

---