# 實施計畫：多格式影片片段下載器

**分支**：`001-url-url-youtube` | **日期**：2025年10月1日 | **規格**：[D:\Documents\GitHub\URL-Video-Clip-Downloader-GUI\specs\001-url-url-youtube\spec.md]
**輸入**：來自 `/specs/001-url-url-youtube/spec.md` 的功能規格

## 執行流程 (/plan 命令範圍)
```
1. 從輸入路徑載入功能規格
   → 如果找不到：錯誤 "在 {path} 找不到功能規格"
2. 填寫技術背景 (掃描 NEEDS CLARIFICATION)
   → 從檔案系統結構或上下文中檢測專案類型 (web=前端+後端, mobile=應用+api)
   → 根據專案類型設定結構決策
3. 根據憲法文件的內容填寫「憲法檢查」部分。
4. 評估下面的「憲法檢查」部分
   → 如果存在違規：在「複雜性追蹤」中記錄
   → 如果沒有正當理由：錯誤 "請先簡化方法"
   → 更新進度追蹤：初始憲法檢查
5. 執行階段 0 → research.md
   → 如果 NEEDS CLARIFICATION 仍然存在：錯誤 "解決未知問題"
6. 執行階段 1 → contracts, data-model.md, quickstart.md, 特定於代理的範本檔案 (例如，Claude Code 的 `CLAUDE.md`，GitHub Copilot 的 `.github/copilot-instructions.md`，Gemini CLI 的 `GEMINI.md`，Qwen Code 的 `QWEN.md` 或 opencode 的 `AGENTS.md`)。
7. 重新評估「憲法檢查」部分
   → 如果出現新的違規：重構設計，返回階段 1
   → 更新進度追蹤：設計後憲法檢查
8. 規劃階段 2 → 描述任務生成方法 (不要建立 tasks.md)
9. 停止 - 準備好執行 /tasks 命令
```

**重要提示**：/plan 命令在步驟 7 停止。階段 2-4 由其他命令執行：
- 階段 2：/tasks 命令建立 tasks.md
- 階段 3-4：實施執行 (手動或透過工具)

## 摘要
此計畫旨在建立一個桌面GUI應用程式，讓使用者可以從各種URL（包括YouTube）下載影片片段。使用者可以指定開始/結束時間、儲存路徑和檔名。應用程式將使用Python、Tkinter、yt-dlp和FFmpeg構建。

## 技術背景
**語言/版本**：Python 3.11
**主要依賴項**：uv, Tkinter, yt-dlp, FFmpeg (via subprocess)
**儲存**：檔案系統
**測試**：pytest
**目標平台**：Windows
**專案類型**：單一專案
**效能目標**：N/A
**限制**：N/A
**規模/範圍**：N/A

## 憲法檢查
*閘門：必須在階段 0 研究之前通過。在階段 1 設計之後重新檢查。*

- **I. 優質程式碼 (Code Quality):** 將遵循標準Python風格指南 (PEP 8)。程式碼將被模組化以提高可讀性和可維護性。
- **II. 嚴謹的測試 (Rigorous Testing):** 將為核心下載和處理邏輯編寫單元測試。將使用`pytest`。
- **III. 一致的使用者體驗 (Consistent User Experience):** 將使用原生的Tkinter UI元件，以確保在Windows上有一致的外觀和感覺。
- **IV. 效能設計 (Performance by Design):** `yt-dlp`和`FFmpeg`是高效能的工具，適用於影片下載和處理。

**結論**: 設計符合所有憲法原則。

## 專案結構

### 文件 (此功能)
```
specs/001-url-url-youtube/
├── plan.md              # 此檔案 (/plan 命令輸出)
├── research.md          # 階段 0 輸出 (/plan 命令)
├── data-model.md        # 階段 1 輸出 (/plan 命令)
├── quickstart.md        # 階段 1 輸出 (/plan 命令)
├── contracts/           # 階段 1 輸出 (/plan 命令)
└── tasks.md             # 階段 2 輸出 (/tasks 命令 - 不是由 /plan 建立)
```

### 原始碼 (儲存庫根目錄)
```
src/
├── main.py              # 應用程式進入點
├── gui.py               # Tkinter UI 程式碼
└── downloader.py        # 下載和剪輯邏輯
tests/
└── test_downloader.py   # downloader 模組的單元測試
```

**結構決策**：選擇了單一專案結構，因為這是一個簡單的桌面應用程式。程式碼被分為UI (`gui.py`)和業務邏輯 (`downloader.py`)，以實現關注點分離。

## 階段 0：大綱與研究
1. **從上面的「技術背景」中提取未知數**：
   - 所有技術選擇都已確定，沒有`NEEDS CLARIFICATION`。

2. **產生並分派研究代理**：
   - **任務**: "研究使用Tkinter、yt-dlp和subprocess FFmpeg整合的最佳實踐"。
   - **任務**: "研究如何使用`uv`來管理Python專案的依賴項"。

3. **在 `research.md` 中整合研究結果**，使用以下格式：
   - **決策**: 將使用`uv`進行虛擬環境和套件管理。GUI將使用`Tkinter`。影片下載將首先嘗試`FFmpeg`，如果失敗則使用`yt-dlp`。
   - **理由**: 這是使用者指定的技術堆疊。`uv`是一個現代且快速的Python套件管理工具。`Tkinter`是Python的標準GUI庫。`FFmpeg`和`yt-dlp`是強大的影片處理工具。
   - **考慮過的替代方案**: 無，因為技術堆疊已由使用者指定。

**輸出**：`research.md`，其中所有 NEEDS CLARIFICATION 都已解決

## 階段 1：設計與合約
*先決條件：research.md 已完成*

1. **從功能規格中提取實體** → `data-model.md`：
   - **實體**: `DownloadJob`
   - **屬性**: `url`, `start_time`, `end_time`, `output_path`, `output_filename`, `status`, `progress`
   - **狀態**: `queued`, `downloading`, `processing`, `completed`, `failed`

2. **從功能需求產生 API 合約**：
   - 這是一個桌面GUI應用程式，因此沒有RESTful API。合約將是`downloader.py`模組中的函式簽名。
   - `def start_download(job: DownloadJob)`

3. **從合約產生合約測試**：
   - 將在`tests/test_downloader.py`中為`start_download`函式建立測試。

4. **從使用者故事中提取測試場景**：
   - **場景**: 使用者提供有效的YouTube URL和時間。
   - **快速入門測試**: 執行應用程式，輸入URL和時間，點擊下載，驗證檔案是否已創建。

5. **增量更新代理檔案** (O(1) 操作)：
   - 此步驟將被跳過，因為它不是此階段的關鍵路徑。

**輸出**：data-model.md, /contracts/*, 失敗的測試, quickstart.md, 特定於代理的檔案

## 階段 2：任務規劃方法
*本節描述 /tasks 命令將執行的操作 - 不要在 /plan 期間執行*

**任務產生策略**：
- 載入 `.specify/templates/tasks-template.md` 作為基礎
- 從階段 1 設計文件 (合約、資料模型、快速入門) 產生任務
- 每個合約 → 合約測試任務 [P]
- 每個實體 → 模型建立任務 [P]
- 每個使用者故事 → 整合測試任務
- 實施任務以使測試通過

**排序策略**：
- TDD 順序：測試先於實施
- 依賴順序：模型先於服務先於 UI
- 標記 [P] 以進行並行執行 (獨立檔案)

**預計輸出**：tasks.md 中 25-30 個編號、排序的任務

**重要提示**：此階段由 /tasks 命令執行，而不是由 /plan 執行

## 階段 3+：未來實施
*這些階段超出了 /plan 命令的範圍*

**階段 3**：任務執行 (/tasks 命令建立 tasks.md)
**階段 4**：實施 (遵循憲法原則執行 tasks.md)
**階段 5**：驗證 (執行測試、執行 quickstart.md、效能驗證)

## 複雜性追蹤
*僅當「憲法檢查」有必須證明的違規時填寫*

| 違規 | 為何需要 | 拒絕的更簡單替代方案因為 |
|-----------|------------|-------------------------------------|
| N/A       | N/A        | N/A                                 |


## 進度追蹤
*此檢查清單在執行流程中更新*

**階段狀態**：
- [x] 階段 0：研究完成 (/plan 命令)
- [x] 階段 1：設計完成 (/plan 命令)
- [ ] 階段 2：任務規劃完成 (/plan 命令 - 僅描述方法)
- [ ] 階段 3：任務已產生 (/tasks 命令)
- [ ] 階段 4：實施完成
- [ ] 階段 5：驗證通過

**閘門狀態**：
- [x] 初始憲法檢查：通過
- [x] 設計後憲法檢查：通過
- [x] 所有 NEEDS CLARIFICATION 已解決
- [ ] 複雜性偏差已記錄

---
*基於憲法 v1.0.0 - 請參閱 `D:\Documents\GitHub\URL-Video-Clip-Downloader-GUI\.specify\memory\constitution.md`*
