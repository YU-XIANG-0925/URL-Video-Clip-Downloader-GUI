import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
from PIL import Image, ImageTk
from downloader import DownloadJob, start_download
from reencoder import reencode_video
from merger import merge_videos
from clipper import ClipJob, start_clip
from editor import (
    VideoFrameReader,
    KeyframeManager,
    CropRegion,
    ASPECT_RATIOS,
    PREVIEW_SIZE,
    format_time_short,
    export_video_with_keyframes,
)
from task_utils import TaskController
from constants import (
    VIDEO_CODECS,
    AUDIO_CODECS,
    CONTAINER_FORMATS,
    MERGE_VIDEO_EXTENSIONS,
    MERGE_CONTAINER_FORMATS,
    BEST_CODEC_LABEL,
    STREAMING_CODEC_LABEL,
    DOWNLOADER_VIDEO_CODECS,
    DOWNLOADER_AUDIO_CODECS,
    CLIPPER_MODES,
    COPY_CODEC_LABEL,
    PRECISE_CUT_LABEL,
)
from utils import get_media_info


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎵 URL Video Clip Downloader")
        # 設定全螢幕模式
        self.state("zoomed")  # Windows 全螢幕

        # === 深色音樂風格主題配置 ===
        self.colors = {
            "bg_dark": "#1a1a2e",  # 深色背景
            "bg_medium": "#16213e",  # 中等深度背景
            "bg_light": "#0f3460",  # 淺深色背景
            "accent": "#e94560",  # 主要強調色（霓虹粉紅）
            "accent2": "#7b2cbf",  # 次要強調色（紫色）
            "accent3": "#00d9ff",  # 第三強調色（霓虹藍）
            "text": "#ffffff",  # 主要文字
            "text_dim": "#a0a0a0",  # 暗淡文字
            "success": "#00ff88",  # 成功綠
            "warning": "#ffaa00",  # 警告橙
            "entry_bg": "#2d2d44",  # 輸入框背景
            "button_bg": "#e94560",  # 按鈕背景
            "progress_trough": "#2d2d44",  # 進度條背景
            "progress_bar": "#00d9ff",  # 進度條填充
        }

        # 設定主視窗背景
        self.configure(bg=self.colors["bg_dark"])

        # 配置 ttk 樣式
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # 配置各種元件樣式
        self._configure_styles()

        # Task Controllers
        self.dl_controller = None
        self.re_controller = None
        self.me_controller = None
        self.cl_controller = None  # Clipper controller
        self.ed_controller = None  # Editor controller
        self.current_dl_job = None
        self.current_cl_job = None  # Clipper job

        # Editor 相關變數
        self.editor_video_reader = None
        self.editor_keyframe_manager = KeyframeManager()
        self.editor_current_time_ms = 0
        self.editor_crop_rect = None  # Canvas 上的裁切框 ID
        self.editor_preview_scale = 1.0  # 預覽縮放比例

        # === 頂部框架：標籤控制 + 結束按鈕 ===
        top_frame = ttk.Frame(self, style="Music.TFrame")
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        # 結束按鈕（放在右上角）
        exit_btn = ttk.Button(
            top_frame,
            text="✕ 結束",
            command=self.quit_app,
            style="Music.TButton",
            width=8,
        )
        exit_btn.pack(side=tk.RIGHT, padx=5)

        # Create Tab Control
        self.tabControl = ttk.Notebook(self, style="Music.TNotebook")
        self.tab1 = ttk.Frame(self.tabControl, style="Music.TFrame")
        self.tab2 = ttk.Frame(self.tabControl, style="Music.TFrame")
        self.tab3 = ttk.Frame(self.tabControl, style="Music.TFrame")
        self.tab4 = ttk.Frame(self.tabControl, style="Music.TFrame")
        self.tab5 = ttk.Frame(self.tabControl, style="Music.TFrame")
        self.tab6 = ttk.Frame(self.tabControl, style="Music.TFrame")
        self.tabControl.add(self.tab1, text="🎬 Downloader")
        self.tabControl.add(self.tab2, text="🔄 Re-encoder")
        self.tabControl.add(self.tab3, text="🔗 Merger")
        self.tabControl.add(self.tab4, text="✂️ Clipper")
        self.tabControl.add(self.tab5, text="✏️ Editor")
        self.tabControl.add(self.tab6, text="📊 File Info")
        self.tabControl.pack(expand=1, fill="both", padx=5, pady=(0, 5))

        # --- Tab 1: Downloader ---
        self.create_downloader_tab()

        # --- Tab 2: Re-encoder ---
        self.create_reencoder_tab()

        # --- Tab 3: Merger ---
        self.create_merger_tab()

        # --- Tab 4: Clipper ---
        self.create_clipper_tab()

        # --- Tab 5: Editor ---
        self.create_editor_tab()

        # --- Tab 6: File Info ---
        self.create_file_info_tab()

        self.download_queue = queue.Queue()
        self.clipper_queue = queue.Queue()
        self.worker_thread = threading.Thread(
            target=self.process_download_queue, daemon=True
        )
        self.worker_thread.start()
        self.clipper_worker_thread = threading.Thread(
            target=self.process_clipper_queue, daemon=True
        )
        self.clipper_worker_thread.start()

    def _configure_styles(self):
        """配置深色音樂風格的 ttk 樣式"""
        colors = self.colors

        # Notebook 樣式
        self.style.configure(
            "Music.TNotebook", background=colors["bg_dark"], borderwidth=0
        )
        self.style.configure(
            "Music.TNotebook.Tab",
            background=colors["bg_medium"],
            foreground=colors["text"],
            padding=[15, 8],
            font=("Segoe UI", 10, "bold"),
        )
        self.style.map(
            "Music.TNotebook.Tab",
            background=[("selected", colors["accent"]), ("active", colors["bg_light"])],
            foreground=[("selected", colors["text"]), ("active", colors["text"])],
        )

        # Frame 樣式
        self.style.configure("Music.TFrame", background=colors["bg_dark"])

        # Label 樣式
        self.style.configure(
            "Music.TLabel",
            background=colors["bg_dark"],
            foreground=colors["text"],
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Music.Header.TLabel",
            background=colors["bg_dark"],
            foreground=colors["accent"],
            font=("Segoe UI", 12, "bold"),
        )
        self.style.configure(
            "Music.Status.TLabel",
            background=colors["bg_dark"],
            foreground=colors["accent3"],
            font=("Segoe UI", 10),
        )

        # Entry 樣式
        self.style.configure(
            "Music.TEntry",
            fieldbackground=colors["entry_bg"],
            foreground=colors["text"],
            insertcolor=colors["text"],
            borderwidth=2,
            relief="flat",
        )

        # Button 樣式
        self.style.configure(
            "Music.TButton",
            background=colors["accent"],
            foreground=colors["text"],
            font=("Segoe UI", 10, "bold"),
            padding=[15, 8],
            borderwidth=0,
        )
        self.style.map(
            "Music.TButton",
            background=[
                ("active", colors["accent2"]),
                ("disabled", colors["bg_medium"]),
            ],
            foreground=[("disabled", colors["text_dim"])],
        )

        self.style.configure(
            "Music.Success.TButton",
            background=colors["success"],
            foreground=colors["bg_dark"],
            font=("Segoe UI", 10, "bold"),
            padding=[15, 8],
        )
        self.style.map(
            "Music.Success.TButton",
            background=[("active", "#00cc6a"), ("disabled", colors["bg_medium"])],
        )

        self.style.configure(
            "Music.Warning.TButton",
            background=colors["warning"],
            foreground=colors["bg_dark"],
            font=("Segoe UI", 10, "bold"),
            padding=[15, 8],
        )

        # Radiobutton 樣式
        self.style.configure(
            "Music.TRadiobutton",
            background=colors["bg_dark"],
            foreground=colors["text"],
            font=("Segoe UI", 10),
        )
        self.style.map("Music.TRadiobutton", background=[("active", colors["bg_dark"])])

        # Checkbutton 樣式
        self.style.configure(
            "Music.TCheckbutton",
            background=colors["bg_dark"],
            foreground=colors["text"],
            font=("Segoe UI", 10),
        )
        self.style.map("Music.TCheckbutton", background=[("active", colors["bg_dark"])])

        # OptionMenu 樣式
        self.style.configure(
            "Music.TMenubutton",
            background=colors["entry_bg"],
            foreground=colors["text"],
            font=("Segoe UI", 10),
            padding=[10, 5],
        )
        self.style.map("Music.TMenubutton", background=[("active", colors["bg_light"])])

        # Progressbar 樣式
        self.style.configure(
            "Music.Horizontal.TProgressbar",
            background=colors["progress_bar"],
            troughcolor=colors["progress_trough"],
            borderwidth=0,
            lightcolor=colors["progress_bar"],
            darkcolor=colors["progress_bar"],
        )

        # LabelFrame 樣式
        self.style.configure(
            "Music.TLabelframe",
            background=colors["bg_dark"],
            foreground=colors["accent"],
            borderwidth=2,
            relief="groove",
        )
        self.style.configure(
            "Music.TLabelframe.Label",
            background=colors["bg_dark"],
            foreground=colors["accent"],
            font=("Segoe UI", 11, "bold"),
        )

    def create_merger_tab(self):
        """建立 Merger 分頁 - 深色音樂風格"""

        # 主要內容框架
        main_frame = ttk.Frame(self.tab3, style="Music.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # === 輸入模式區塊 ===
        mode_frame = ttk.LabelFrame(
            main_frame, text="📥 輸入模式", style="Music.TLabelframe"
        )
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        self.merge_mode_var = tk.StringVar(value="selected")
        ttk.Radiobutton(
            mode_frame,
            text="🎬 選擇檔案",
            variable=self.merge_mode_var,
            value="selected",
            command=self.update_merge_input_ui,
            style="Music.TRadiobutton",
        ).pack(side=tk.LEFT, padx=20, pady=10)
        ttk.Radiobutton(
            mode_frame,
            text="📁 整個目錄",
            variable=self.merge_mode_var,
            value="directory",
            command=self.update_merge_input_ui,
            style="Music.TRadiobutton",
        ).pack(side=tk.LEFT, padx=20, pady=10)

        # === 輸入區塊 ===
        input_frame = ttk.LabelFrame(
            main_frame, text="📂 輸入檔案", style="Music.TLabelframe"
        )
        input_frame.pack(fill=tk.X, pady=(0, 10))

        self.merge_input_frame = ttk.Frame(input_frame, style="Music.TFrame")
        self.merge_input_frame.pack(fill=tk.X, padx=10, pady=10)
        self.merge_input_frame.columnconfigure(0, weight=1)

        # 檔案清單 (Selected Files Mode)
        self.merge_files_listbox = tk.Listbox(
            self.merge_input_frame,
            height=5,
            selectmode=tk.EXTENDED,
            bg=self.colors["entry_bg"],
            fg=self.colors["text"],
            font=("Segoe UI", 10),
            selectbackground=self.colors["accent"],
        )
        self.merge_files_listbox.grid(row=0, column=0, sticky=tk.EW, padx=(0, 10))

        self.merge_files_btn_frame = ttk.Frame(
            self.merge_input_frame, style="Music.TFrame"
        )
        self.merge_files_btn_frame.grid(row=0, column=1, sticky=tk.NS)
        self.merge_add_files_btn = ttk.Button(
            self.merge_files_btn_frame,
            text="新增檔案",
            command=self.browse_merge_files,
            style="Music.TButton",
        )
        self.merge_add_files_btn.pack(fill=tk.X, pady=2)
        self.merge_clear_files_btn = ttk.Button(
            self.merge_files_btn_frame,
            text="清除",
            command=lambda: self.merge_files_listbox.delete(0, tk.END),
            style="Music.TButton",
        )
        self.merge_clear_files_btn.pack(fill=tk.X, pady=2)

        # Directory UI (Hidden initially)
        self.merge_dir_label = ttk.Label(
            self.merge_input_frame, text="輸入目錄:", style="Music.TLabel"
        )
        self.merge_dir_entry = ttk.Entry(
            self.merge_input_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.merge_dir_browse_btn = ttk.Button(
            self.merge_input_frame,
            text="瀏覽",
            command=self.browse_merge_dir,
            style="Music.TButton",
        )

        # === 輸出設定區塊 ===
        output_frame = ttk.LabelFrame(
            main_frame, text="📁 輸出設定", style="Music.TLabelframe"
        )
        output_frame.pack(fill=tk.X, pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)

        # Output Directory
        ttk.Label(output_frame, text="輸出目錄:", style="Music.TLabel").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W
        )
        self.merge_output_dir_entry = ttk.Entry(
            output_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.merge_output_dir_entry.grid(row=0, column=1, padx=10, pady=8, sticky=tk.EW)
        self.merge_browse_output_btn = ttk.Button(
            output_frame,
            text="瀏覽",
            command=self.browse_merge_output_dir,
            style="Music.TButton",
        )
        self.merge_browse_output_btn.grid(row=0, column=2, padx=10, pady=8)

        # Output Filename
        ttk.Label(output_frame, text="輸出檔名:", style="Music.TLabel").grid(
            row=1, column=0, padx=10, pady=8, sticky=tk.W
        )
        self.merge_output_filename_entry = ttk.Entry(
            output_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.merge_output_filename_entry.grid(
            row=1, column=1, padx=10, pady=8, sticky=tk.EW
        )

        # Output Format
        ttk.Label(output_frame, text="輸出格式:", style="Music.TLabel").grid(
            row=2, column=0, padx=10, pady=8, sticky=tk.W
        )
        self.merge_containers = MERGE_CONTAINER_FORMATS
        self.merge_container_var = tk.StringVar(value=self.merge_containers[0])
        ttk.OptionMenu(
            output_frame,
            self.merge_container_var,
            self.merge_containers[0],
            *self.merge_containers,
            style="Music.TMenubutton",
        ).grid(row=2, column=1, padx=10, pady=8, sticky=tk.W)

        # Video Codec
        ttk.Label(output_frame, text="影片編碼:", style="Music.TLabel").grid(
            row=3, column=0, padx=10, pady=8, sticky=tk.W
        )
        self.merge_video_codecs = VIDEO_CODECS
        self.merge_video_codec_var = tk.StringVar(value="copy")
        ttk.OptionMenu(
            output_frame,
            self.merge_video_codec_var,
            "copy",
            *self.merge_video_codecs,
            style="Music.TMenubutton",
        ).grid(row=3, column=1, padx=10, pady=8, sticky=tk.W)

        # Recycle Option
        self.merge_recycle_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            output_frame,
            text="合併成功後刪除原始檔案（移至回收筒）",
            variable=self.merge_recycle_var,
            style="Music.TCheckbutton",
        ).grid(row=4, column=0, columnspan=2, padx=10, pady=8, sticky=tk.W)

        # === 控制按鈕 ===
        btn_frame = ttk.Frame(main_frame, style="Music.TFrame")
        btn_frame.pack(pady=10)

        self.merge_button = ttk.Button(
            btn_frame,
            text="▶ 開始合併",
            command=self.start_merge,
            style="Music.Success.TButton",
        )
        self.merge_button.pack(side=tk.LEFT, padx=8)

        self.merge_pause_button = ttk.Button(
            btn_frame,
            text="⏸ 暫停",
            command=self.toggle_merge_pause,
            state=tk.DISABLED,
            style="Music.Warning.TButton",
        )
        self.merge_pause_button.pack(side=tk.LEFT, padx=8)

        self.merge_stop_button = ttk.Button(
            btn_frame,
            text="⏹ 停止",
            command=self.stop_merge,
            state=tk.DISABLED,
            style="Music.TButton",
        )
        self.merge_stop_button.pack(side=tk.LEFT, padx=8)

        # === 進度區塊 ===
        progress_frame = ttk.Frame(main_frame, style="Music.TFrame")
        progress_frame.pack(fill=tk.X, pady=5)

        self.merge_progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=400,
            mode="determinate",
            style="Music.Horizontal.TProgressbar",
        )
        self.merge_progress_bar.pack(fill=tk.X, pady=5)

        self.merge_status_label = ttk.Label(
            progress_frame, text="狀態：待機中", style="Music.Status.TLabel"
        )
        self.merge_status_label.pack(anchor=tk.W, pady=5)

    def update_merge_input_ui(self):
        mode = self.merge_mode_var.get()
        # Clear grid
        for widget in self.merge_input_frame.winfo_children():
            widget.grid_remove()
            widget.pack_forget()

        if mode == "selected":
            self.merge_files_listbox.grid(row=0, column=0, columnspan=2, sticky=tk.EW)
            self.merge_files_btn_frame.grid(row=0, column=2, sticky=tk.NS)
            self.merge_add_files_btn.pack(fill=tk.X, pady=2)
            self.merge_clear_files_btn.pack(fill=tk.X, pady=2)
        else:
            self.merge_dir_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            self.merge_dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
            self.merge_dir_browse_btn.grid(row=0, column=2, padx=5, pady=5)

    def browse_merge_files(self):
        files = filedialog.askopenfilenames(title="Select Media Files to Merge")
        for f in files:
            self.merge_files_listbox.insert(tk.END, f)

    def browse_merge_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.merge_dir_entry.delete(0, tk.END)
            self.merge_dir_entry.insert(0, path)

    def browse_merge_output_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.merge_output_dir_entry.delete(0, tk.END)
            self.merge_output_dir_entry.insert(0, path)

    def merge_progress_callback(self, percentage, message):
        if percentage is not None:
            self.merge_progress_bar["value"] = percentage
        self.merge_status_label.config(text=f"Status: {message}")
        self.update_idletasks()

    def toggle_merge_pause(self):
        if self.me_controller:
            if self.me_controller.pause_event.is_set():
                self.me_controller.resume()
                self.merge_pause_button.config(text="Pause")
            else:
                self.me_controller.pause()
                self.merge_pause_button.config(text="Resume")

    def stop_merge(self):
        if self.me_controller:
            self.me_controller.stop()
            self.merge_stop_button.config(state=tk.DISABLED)
            self.merge_status_label.config(text="Status: Stopping...")

    def start_merge(self):
        mode = self.merge_mode_var.get()
        output_dir = self.merge_output_dir_entry.get()
        output_filename = self.merge_output_filename_entry.get()
        container = self.merge_container_var.get()
        video_codec = self.merge_video_codec_var.get()

        if not output_dir or not output_filename:
            messagebox.showerror(
                "Error", "Please specify output directory and filename."
            )
            return

        input_files = []
        if mode == "selected":
            input_files = list(self.merge_files_listbox.get(0, tk.END))
            if not input_files:
                messagebox.showerror("Error", "Please add files to merge.")
                return
        else:
            input_dir = self.merge_dir_entry.get()
            if not input_dir or not os.path.isdir(input_dir):
                messagebox.showerror("Error", "Invalid input directory.")
                return
            # Get all files, sort them by name (implies timestamp usually for segments)
            try:
                files = sorted(
                    [
                        os.path.join(input_dir, f)
                        for f in os.listdir(input_dir)
                        if os.path.isfile(os.path.join(input_dir, f))
                    ]
                )
                # Basic filter for video extensions?
                input_files = [
                    f
                    for f in files
                    if f.lower().endswith(tuple(MERGE_VIDEO_EXTENSIONS))
                ]

                if not input_files:
                    messagebox.showerror(
                        "Error", "No supported media files found in directory."
                    )
                    return
            except Exception as e:
                messagebox.showerror("Error", f"Error reading directory: {e}")
                return

        output_path = os.path.join(output_dir, f"{output_filename}.{container}")

        self.merge_status_label.config(text="Status: Starting merge...")
        self.merge_progress_bar["value"] = 0
        self.merge_button.config(state=tk.DISABLED)
        self.merge_pause_button.config(state=tk.NORMAL, text="Pause")
        self.merge_stop_button.config(state=tk.NORMAL)

        self.me_controller = TaskController()

        threading.Thread(
            target=self._run_merge_task,
            args=(input_files, output_path, self.merge_recycle_var.get(), video_codec),
        ).start()

    def _run_merge_task(self, input_files, output_path, recycle_original, video_codec):
        success, message = merge_videos(
            input_files,
            output_path,
            self.merge_progress_callback,
            self.me_controller,
            recycle_original,
            video_codec,
        )
        self.after(0, self._complete_merge_task, success, message)

    def _complete_merge_task(self, success, message):
        self.merge_button.config(state=tk.NORMAL)
        self.merge_pause_button.config(state=tk.DISABLED, text="Pause")
        self.merge_stop_button.config(state=tk.DISABLED)
        self.me_controller = None

        if success:
            self.merge_progress_bar["value"] = 100
            self.merge_status_label.config(text="Status: Merge finished.")
            messagebox.showinfo("Success", message)
        else:
            if "stopped by user" in message.lower():
                self.merge_progress_bar["value"] = 0
                self.merge_status_label.config(text="Status: Merge stopped.")
            else:
                self.merge_progress_bar["value"] = 0
                self.merge_status_label.config(text="Status: Merge failed.")
                messagebox.showerror("Error", message)

    def create_clipper_tab(self):
        """建立 Clipper 分頁 - 影片裁切功能"""

        # 主要內容框架
        main_frame = ttk.Frame(self.tab4, style="Music.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # === 輸入設定區塊 ===
        input_frame = ttk.LabelFrame(
            main_frame, text="📥 輸入設定", style="Music.TLabelframe"
        )
        input_frame.pack(fill=tk.X, pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        # Input File
        ttk.Label(input_frame, text="輸入檔案:", style="Music.TLabel").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W
        )
        self.clip_input_entry = ttk.Entry(
            input_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.clip_input_entry.grid(row=0, column=1, padx=10, pady=8, sticky=tk.EW)
        ttk.Button(
            input_frame,
            text="瀏覽",
            command=self.browse_clip_input,
            style="Music.TButton",
        ).grid(row=0, column=2, padx=10, pady=8)

        # Start Time
        ttk.Label(input_frame, text="開始時間 (HH:MM:SS):", style="Music.TLabel").grid(
            row=1, column=0, padx=10, pady=8, sticky=tk.W
        )
        self.clip_start_entry = ttk.Entry(
            input_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.clip_start_entry.grid(row=1, column=1, padx=10, pady=8, sticky=tk.W)

        # End Time
        ttk.Label(input_frame, text="結束時間 (HH:MM:SS):", style="Music.TLabel").grid(
            row=2, column=0, padx=10, pady=8, sticky=tk.W
        )
        self.clip_end_entry = ttk.Entry(
            input_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.clip_end_entry.grid(row=2, column=1, padx=10, pady=8, sticky=tk.W)

        # === 輸出設定區塊 ===
        output_frame = ttk.LabelFrame(
            main_frame, text="📁 輸出設定", style="Music.TLabelframe"
        )
        output_frame.pack(fill=tk.X, pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)

        # Output Path
        ttk.Label(output_frame, text="輸出路徑:", style="Music.TLabel").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W
        )
        self.clip_output_path_entry = ttk.Entry(
            output_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.clip_output_path_entry.grid(row=0, column=1, padx=10, pady=8, sticky=tk.EW)
        ttk.Button(
            output_frame,
            text="瀏覽",
            command=self.browse_clip_output,
            style="Music.TButton",
        ).grid(row=0, column=2, padx=10, pady=8)

        # Output Filename
        ttk.Label(output_frame, text="輸出檔名:", style="Music.TLabel").grid(
            row=1, column=0, padx=10, pady=8, sticky=tk.W
        )
        self.clip_output_name_entry = ttk.Entry(
            output_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.clip_output_name_entry.grid(row=1, column=1, padx=10, pady=8, sticky=tk.EW)

        # === 裁切模式區塊 ===
        mode_frame = ttk.LabelFrame(
            main_frame, text="⚙️ 裁切模式", style="Music.TLabelframe"
        )
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        self.clip_mode_var = tk.StringVar(value=COPY_CODEC_LABEL)

        ttk.Radiobutton(
            mode_frame,
            text="🚀 快速裁切（從最近的關鍵幀開始，可能有幾秒誤差）",
            variable=self.clip_mode_var,
            value=COPY_CODEC_LABEL,
            style="Music.TRadiobutton",
        ).pack(anchor=tk.W, padx=10, pady=5)

        ttk.Radiobutton(
            mode_frame,
            text="🎯 精確裁切（重新編碼，100% 精確但需要較長時間）",
            variable=self.clip_mode_var,
            value=PRECISE_CUT_LABEL,
            style="Music.TRadiobutton",
        ).pack(anchor=tk.W, padx=10, pady=5)

        # Container Format
        format_frame = ttk.Frame(mode_frame, style="Music.TFrame")
        format_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(format_frame, text="容器格式:", style="Music.TLabel").pack(
            side=tk.LEFT
        )
        self.clip_format_var = tk.StringVar(value="mp4")
        ttk.OptionMenu(
            format_frame,
            self.clip_format_var,
            "mp4",
            *CONTAINER_FORMATS,
            style="Music.TMenubutton",
        ).pack(side=tk.LEFT, padx=10)

        # === 控制按鈕 ===
        btn_frame = ttk.Frame(main_frame, style="Music.TFrame")
        btn_frame.pack(pady=10)

        self.clip_start_btn = ttk.Button(
            btn_frame,
            text="▶ 開始裁切",
            command=self.start_clip_job,
            style="Music.Success.TButton",
        )
        self.clip_start_btn.pack(side=tk.LEFT, padx=8)

        self.clip_pause_btn = ttk.Button(
            btn_frame,
            text="⏸ 暫停",
            command=self.toggle_clip_pause,
            state=tk.DISABLED,
            style="Music.Warning.TButton",
        )
        self.clip_pause_btn.pack(side=tk.LEFT, padx=8)

        self.clip_stop_btn = ttk.Button(
            btn_frame,
            text="⏹ 停止",
            command=self.stop_clip,
            state=tk.DISABLED,
            style="Music.TButton",
        )
        self.clip_stop_btn.pack(side=tk.LEFT, padx=8)

        # === 進度區塊 ===
        progress_frame = ttk.Frame(main_frame, style="Music.TFrame")
        progress_frame.pack(fill=tk.X, pady=5)

        self.clip_progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=400,
            mode="indeterminate",
            style="Music.Horizontal.TProgressbar",
        )
        self.clip_progress_bar.pack(fill=tk.X, pady=5)

        self.clip_status_label = ttk.Label(
            progress_frame, text="狀態：待機中", style="Music.Status.TLabel"
        )
        self.clip_status_label.pack(anchor=tk.W, pady=5)

    def create_editor_tab(self):
        """建立 Editor 分頁 - 進階影片編輯器"""

        # 主要框架 - 使用 PanedWindow 分割預覽和控制區
        main_frame = ttk.Frame(self.tab5, style="Music.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # === 上方：檔案選擇 ===
        file_frame = ttk.Frame(main_frame, style="Music.TFrame")
        file_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(
            file_frame,
            text="📂 載入影片",
            command=self.editor_load_video,
            style="Music.TButton",
        ).pack(side=tk.LEFT, padx=5)

        self.editor_file_label = ttk.Label(
            file_frame, text="尚未載入影片", style="Music.TLabel"
        )
        self.editor_file_label.pack(side=tk.LEFT, padx=10)

        # === 中間：預覽區域 ===
        preview_container = ttk.LabelFrame(
            main_frame, text="🎬 預覽", style="Music.TLabelframe"
        )
        preview_container.pack(fill=tk.BOTH, expand=True, pady=5)

        # 預覽 Canvas
        self.editor_canvas = tk.Canvas(
            preview_container,
            width=PREVIEW_SIZE[0],
            height=PREVIEW_SIZE[1],
            bg=self.colors["bg_medium"],
            highlightthickness=0,
        )
        self.editor_canvas.pack(padx=5, pady=5)

        # 綁定滑鼠事件（用於拖動裁切框）
        self.editor_canvas.bind("<Button-1>", self.editor_on_canvas_click)
        self.editor_canvas.bind("<B1-Motion>", self.editor_on_canvas_drag)
        self.editor_canvas.bind("<ButtonRelease-1>", self.editor_on_canvas_release)

        # === 時間軸區域 ===
        timeline_frame = ttk.Frame(main_frame, style="Music.TFrame")
        timeline_frame.pack(fill=tk.X, pady=5)

        self.editor_time_label = ttk.Label(
            timeline_frame, text="00:00 / 00:00", style="Music.TLabel"
        )
        self.editor_time_label.pack(side=tk.LEFT, padx=5)

        self.editor_timeline_var = tk.IntVar(value=0)
        self.editor_timeline = ttk.Scale(
            timeline_frame,
            from_=0,
            to=1000,
            orient=tk.HORIZONTAL,
            variable=self.editor_timeline_var,
            command=self.editor_on_timeline_change,
        )
        self.editor_timeline.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # === 裁切設定區域 ===
        crop_frame = ttk.LabelFrame(
            main_frame, text="✂️ 裁切設定", style="Music.TLabelframe"
        )
        crop_frame.pack(fill=tk.X, pady=5)

        # 比例選擇
        ratio_frame = ttk.Frame(crop_frame, style="Music.TFrame")
        ratio_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(ratio_frame, text="輸出比例:", style="Music.TLabel").pack(
            side=tk.LEFT
        )

        self.editor_ratio_var = tk.StringVar(value="自由")
        for ratio_name in ASPECT_RATIOS.keys():
            ttk.Radiobutton(
                ratio_frame,
                text=ratio_name,
                value=ratio_name,
                variable=self.editor_ratio_var,
                style="Music.TRadiobutton",
                command=self.editor_on_ratio_change,
            ).pack(side=tk.LEFT, padx=5)

        # 輸出尺寸
        size_frame = ttk.Frame(crop_frame, style="Music.TFrame")
        size_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(size_frame, text="輸出尺寸:", style="Music.TLabel").pack(side=tk.LEFT)
        self.editor_width_var = tk.StringVar(value="600")
        ttk.Entry(
            size_frame,
            textvariable=self.editor_width_var,
            width=6,
            style="Music.TEntry",
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Label(size_frame, text="×", style="Music.TLabel").pack(side=tk.LEFT)
        self.editor_height_var = tk.StringVar(value="400")
        ttk.Entry(
            size_frame,
            textvariable=self.editor_height_var,
            width=6,
            style="Music.TEntry",
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT, padx=5)

        # === 關鍵幀控制 ===
        keyframe_frame = ttk.LabelFrame(
            main_frame, text="🔑 關鍵幀", style="Music.TLabelframe"
        )
        keyframe_frame.pack(fill=tk.X, pady=5)

        kf_btn_frame = ttk.Frame(keyframe_frame, style="Music.TFrame")
        kf_btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            kf_btn_frame,
            text="➕ 新增關鍵幀",
            command=self.editor_add_keyframe,
            style="Music.Success.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            kf_btn_frame,
            text="🗑️ 刪除",
            command=self.editor_remove_keyframe,
            style="Music.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            kf_btn_frame,
            text="🔄 清除全部",
            command=self.editor_clear_keyframes,
            style="Music.TButton",
        ).pack(side=tk.LEFT, padx=5)

        # 關鍵幀列表
        self.editor_keyframe_list = ttk.Label(
            keyframe_frame, text="尚未設定關鍵幀", style="Music.TLabel"
        )
        self.editor_keyframe_list.pack(padx=10, pady=5, anchor=tk.W)

        # === 匯出設定 ===
        export_frame = ttk.Frame(main_frame, style="Music.TFrame")
        export_frame.pack(fill=tk.X, pady=10)

        ttk.Label(export_frame, text="輸出路徑:", style="Music.TLabel").pack(
            side=tk.LEFT, padx=5
        )
        self.editor_output_entry = ttk.Entry(
            export_frame, style="Music.TEntry", font=("Segoe UI", 10), width=40
        )
        self.editor_output_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(
            export_frame,
            text="瀏覽",
            command=self.editor_browse_output,
            style="Music.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            export_frame,
            text="🎬 匯出影片",
            command=self.editor_export,
            style="Music.Success.TButton",
        ).pack(side=tk.LEFT, padx=20)

        # Editor 狀態
        self.editor_status_label = ttk.Label(
            main_frame, text="狀態：待機中", style="Music.Status.TLabel"
        )
        self.editor_status_label.pack(anchor=tk.W, pady=5)

        # 裁切框拖動狀態
        self.editor_drag_start = None
        self.editor_crop_x = 100
        self.editor_crop_y = 100
        self.editor_crop_w = 200
        self.editor_crop_h = 150

    def create_file_info_tab(self):
        """建立 File Info 分頁"""
        # 主要內容框架
        main_frame = ttk.Frame(self.tab6, style="Music.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # File Selection Frame
        file_frame = ttk.LabelFrame(
            main_frame, text="📁 檔案選擇", style="Music.TLabelframe"
        )
        file_frame.pack(fill=tk.X, pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        self.info_file_label = ttk.Label(
            file_frame, text="影片檔案:", style="Music.TLabel"
        )
        self.info_file_label.grid(row=0, column=0, padx=10, pady=8, sticky=tk.W)
        self.info_file_entry = ttk.Entry(
            file_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.info_file_entry.grid(row=0, column=1, padx=10, pady=8, sticky=tk.EW)
        self.info_browse_btn = ttk.Button(
            file_frame,
            text="瀏覽",
            command=self.browse_info_file,
            style="Music.TButton",
        )
        self.info_browse_btn.grid(row=0, column=2, padx=10, pady=8)

        # Analyze Button
        self.info_analyze_btn = ttk.Button(
            main_frame,
            text="🔍 分析檔案",
            command=self.analyze_file,
            style="Music.Success.TButton",
        )
        self.info_analyze_btn.pack(pady=10)

        # Info Display Frame
        info_frame = ttk.LabelFrame(
            main_frame, text="📊 檔案資訊", style="Music.TLabelframe"
        )
        info_frame.pack(fill=tk.BOTH, expand=True)

        self.info_text = tk.Text(
            info_frame,
            height=15,
            width=60,
            bg=self.colors["entry_bg"],
            fg=self.colors["text"],
            font=("Consolas", 10),
            insertbackground=self.colors["text"],
        )
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbar
        self.info_scroll = ttk.Scrollbar(info_frame, command=self.info_text.yview)
        self.info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_text["yscrollcommand"] = self.info_scroll.set

    def browse_info_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.avi *.mov *.flv *.webm *.ts"),
                ("All files", "*.*"),
            ],
        )
        if file_path:
            self.info_file_entry.delete(0, tk.END)
            self.info_file_entry.insert(0, file_path)
            self.analyze_file()  # Auto analyze

    def analyze_file(self):
        file_path = self.info_file_entry.get()
        if not file_path:
            return

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, "Analyzing...\n")
        self.update_idletasks()

        # Run in thread if needed, but ffprobe is usually fast. Main thread for now is likely fine,
        # but to be safe and consistent, we can just run it synchronously as it returns text.
        # If it hangs, we might need threading, but typically ffprobe on local file is instant.

        info, error = get_media_info(file_path)

        self.info_text.delete(1.0, tk.END)
        if error:
            self.info_text.insert(tk.END, f"Error: {error}")
            return

        # Format Output
        output = []
        output.append(f"Filename: {info['filename']}")
        output.append(f"Size: {info['size']}")
        output.append(f"Duration: {info['duration']} s")
        output.append(f"Total Bitrate: {info['bitrate']}")
        output.append("-" * 30)

        for stream in info["streams"]:
            if stream["codec_type"] == "video":
                output.append(f"[Video Stream #{stream['index']}]")
                output.append(f"  Codec: {stream['codec_name']} ({stream['profile']})")
                output.append(f"  Resolution: {stream['resolution']}")
                output.append(f"  FPS: {stream['fps']}")
            elif stream["codec_type"] == "audio":
                output.append(f"[Audio Stream #{stream['index']}]")
                output.append(f"  Codec: {stream['codec_name']}")
                output.append(f"  Sample Rate: {stream['sample_rate']}")
                output.append(f"  Channels: {stream['channels']}")
            else:
                output.append(f"[{stream['codec_type']} Stream #{stream['index']}]")
                output.append(f"  Codec: {stream['codec_name']}")
            output.append("")

        self.info_text.insert(tk.END, "\n".join(output))

    def create_downloader_tab(self):
        """建立 Downloader 分頁 - 純下載功能（不含裁切）"""

        # 主要內容框架
        main_frame = ttk.Frame(self.tab1, style="Music.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # === 來源設定區塊 ===
        source_frame = ttk.LabelFrame(
            main_frame, text="📥 來源設定", style="Music.TLabelframe"
        )
        source_frame.pack(fill=tk.X, pady=(0, 15))
        source_frame.columnconfigure(1, weight=1)

        # URL
        self.url_label = ttk.Label(source_frame, text="URL:", style="Music.TLabel")
        self.url_label.grid(row=0, column=0, padx=10, pady=8, sticky=tk.W)
        self.url_entry = ttk.Entry(
            source_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.url_entry.grid(
            row=0, column=1, columnspan=2, padx=10, pady=8, sticky=tk.EW
        )

        # === 輸出設定區塊 ===
        output_frame = ttk.LabelFrame(
            main_frame, text="📁 輸出設定", style="Music.TLabelframe"
        )
        output_frame.pack(fill=tk.X, pady=(0, 15))
        output_frame.columnconfigure(1, weight=1)

        # Output Path
        self.output_path_label = ttk.Label(
            output_frame, text="輸出路徑:", style="Music.TLabel"
        )
        self.output_path_label.grid(row=0, column=0, padx=10, pady=8, sticky=tk.W)
        self.output_path_entry = ttk.Entry(
            output_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.output_path_entry.grid(row=0, column=1, padx=10, pady=8, sticky=tk.EW)
        self.browse_button = ttk.Button(
            output_frame,
            text="瀏覽",
            command=self.browse_download_output_path,
            style="Music.TButton",
        )
        self.browse_button.grid(row=0, column=2, padx=10, pady=8)

        # Output Filename
        self.output_filename_label = ttk.Label(
            output_frame, text="輸出檔名:", style="Music.TLabel"
        )
        self.output_filename_label.grid(row=1, column=0, padx=10, pady=8, sticky=tk.W)
        self.output_filename_entry = ttk.Entry(
            output_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.output_filename_entry.grid(row=1, column=1, padx=10, pady=8, sticky=tk.EW)

        # Container Format
        self.container_format_label = ttk.Label(
            output_frame, text="容器格式:", style="Music.TLabel"
        )
        self.container_format_label.grid(row=2, column=0, padx=10, pady=8, sticky=tk.W)
        self.container_formats = CONTAINER_FORMATS
        self.container_format_var = tk.StringVar(self.tab1)
        self.container_format_var.set(self.container_formats[0])
        self.container_format_option = ttk.OptionMenu(
            output_frame,
            self.container_format_var,
            self.container_formats[0],
            *self.container_formats,
            style="Music.TMenubutton",
        )
        self.container_format_option.grid(row=2, column=1, padx=10, pady=8, sticky=tk.W)

        # === 編碼設定 - 固定為 Copy 模式（隱藏變數） ===
        self.video_codec_var = tk.StringVar(self.tab1)
        self.video_codec_var.set(DOWNLOADER_VIDEO_CODECS[0])
        self.audio_codec_var = tk.StringVar(self.tab1)
        self.audio_codec_var.set(DOWNLOADER_AUDIO_CODECS[0])
        self.dl_quality_var = tk.IntVar(value=30)
        self.dl_low_vram_var = tk.BooleanVar(value=False)
        # 保留空的 start/end time 變數以相容 DownloadJob
        self.start_time_entry = type("obj", (object,), {"get": lambda: ""})()
        self.end_time_entry = type("obj", (object,), {"get": lambda: ""})()

        # 提示訊息
        info_label = ttk.Label(
            main_frame,
            text="💡 純下載模式：直接下載原始影音，如需裁切請使用 Clipper 分頁",
            style="Music.Status.TLabel",
        )
        info_label.pack(anchor=tk.W, pady=(0, 10))

        # === 控制按鈕 ===
        self.download_btn_frame = ttk.Frame(main_frame, style="Music.TFrame")
        self.download_btn_frame.pack(pady=10)

        self.download_button = ttk.Button(
            self.download_btn_frame,
            text="▶ 開始下載",
            command=self.start_download,
            style="Music.Success.TButton",
        )
        self.download_button.pack(side=tk.LEFT, padx=8)

        self.dl_pause_button = ttk.Button(
            self.download_btn_frame,
            text="⏸ 暫停",
            command=self.toggle_dl_pause,
            state=tk.DISABLED,
            style="Music.Warning.TButton",
        )
        self.dl_pause_button.pack(side=tk.LEFT, padx=8)

        self.dl_stop_button = ttk.Button(
            self.download_btn_frame,
            text="⏹ 停止",
            command=self.stop_dl,
            state=tk.DISABLED,
            style="Music.TButton",
        )
        self.dl_stop_button.pack(side=tk.LEFT, padx=8)

        # === 進度區塊 ===
        progress_frame = ttk.Frame(main_frame, style="Music.TFrame")
        progress_frame.pack(fill=tk.X, pady=10)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=400,
            mode="determinate",
            style="Music.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.status_label = ttk.Label(
            progress_frame, text="狀態：待機中", style="Music.Status.TLabel"
        )
        self.status_label.pack(anchor=tk.W, pady=5)

    def create_reencoder_tab(self):
        """建立 Re-encoder 分頁 - 深色音樂風格"""

        # 主要內容框架
        main_frame = ttk.Frame(self.tab2, style="Music.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # === 模式選擇區塊 ===
        mode_frame = ttk.LabelFrame(
            main_frame, text="📂 處理模式", style="Music.TLabelframe"
        )
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        self.re_mode_var = tk.StringVar(self.tab2, value="single")
        self.re_single_file_radio = ttk.Radiobutton(
            mode_frame,
            text="🎬 單一檔案",
            variable=self.re_mode_var,
            value="single",
            command=self.update_reencode_input_label,
            style="Music.TRadiobutton",
        )
        self.re_single_file_radio.pack(side=tk.LEFT, padx=15, pady=8)
        self.re_batch_dir_radio = ttk.Radiobutton(
            mode_frame,
            text="📁 批次目錄",
            variable=self.re_mode_var,
            value="batch",
            command=self.update_reencode_input_label,
            style="Music.TRadiobutton",
        )
        self.re_batch_dir_radio.pack(side=tk.LEFT, padx=15, pady=8)

        # === 輸入/輸出設定區塊 ===
        io_frame = ttk.LabelFrame(
            main_frame, text="📥 輸入/輸出設定", style="Music.TLabelframe"
        )
        io_frame.pack(fill=tk.X, pady=(0, 10))
        io_frame.columnconfigure(1, weight=1)

        # Input Path
        self.re_input_path_label = ttk.Label(
            io_frame, text="輸入檔案:", style="Music.TLabel"
        )
        self.re_input_path_label.grid(row=0, column=0, padx=10, pady=6, sticky=tk.W)
        self.re_input_path_entry = ttk.Entry(
            io_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.re_input_path_entry.grid(row=0, column=1, padx=10, pady=6, sticky=tk.EW)
        self.re_browse_input_button = ttk.Button(
            io_frame,
            text="瀏覽",
            command=self.browse_reencode_input_path,
            style="Music.TButton",
        )
        self.re_browse_input_button.grid(row=0, column=2, padx=10, pady=6)

        # Batch File Types (hidden by default)
        self.re_batch_filetypes_label = ttk.Label(
            io_frame, text="檔案類型 (例: mp4,mkv):", style="Music.TLabel"
        )
        self.re_batch_filetypes_label.grid(
            row=1, column=0, padx=10, pady=6, sticky=tk.W
        )
        self.re_batch_filetypes_entry = ttk.Entry(
            io_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.re_batch_filetypes_entry.grid(
            row=1, column=1, padx=10, pady=6, sticky=tk.EW
        )
        self.re_batch_filetypes_label.grid_remove()
        self.re_batch_filetypes_entry.grid_remove()

        # Output Directory
        self.re_output_dir_label = ttk.Label(
            io_frame, text="輸出目錄:", style="Music.TLabel"
        )
        self.re_output_dir_label.grid(row=2, column=0, padx=10, pady=6, sticky=tk.W)
        self.re_output_dir_entry = ttk.Entry(
            io_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.re_output_dir_entry.grid(row=2, column=1, padx=10, pady=6, sticky=tk.EW)
        self.re_browse_output_button = ttk.Button(
            io_frame,
            text="瀏覽",
            command=self.browse_reencode_output_dir,
            style="Music.TButton",
        )
        self.re_browse_output_button.grid(row=2, column=2, padx=10, pady=6)

        # Output Filename
        self.re_output_filename_label = ttk.Label(
            io_frame, text="輸出檔名:", style="Music.TLabel"
        )
        self.re_output_filename_label.grid(
            row=3, column=0, padx=10, pady=6, sticky=tk.W
        )
        self.re_output_filename_entry = ttk.Entry(
            io_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.re_output_filename_entry.grid(
            row=3, column=1, padx=10, pady=6, sticky=tk.EW
        )

        # === 編碼設定區塊 ===
        codec_frame = ttk.LabelFrame(
            main_frame, text="⚙️ 編碼設定", style="Music.TLabelframe"
        )
        codec_frame.pack(fill=tk.X, pady=(0, 10))
        codec_frame.columnconfigure(1, weight=1)
        codec_frame.columnconfigure(3, weight=1)

        # Video Codec
        ttk.Label(codec_frame, text="視訊編碼:", style="Music.TLabel").grid(
            row=0, column=0, padx=10, pady=6, sticky=tk.W
        )
        self.video_codecs = [c for c in VIDEO_CODECS if c != "copy"]
        self.re_video_codec_var = tk.StringVar(self.tab2)
        self.re_video_codec_var.set(self.video_codecs[0])
        self.re_video_codec_option = ttk.OptionMenu(
            codec_frame,
            self.re_video_codec_var,
            self.video_codecs[0],
            *self.video_codecs,
            style="Music.TMenubutton",
        )
        self.re_video_codec_option.grid(row=0, column=1, padx=10, pady=6, sticky=tk.W)

        # Audio Codec
        ttk.Label(codec_frame, text="音訊編碼:", style="Music.TLabel").grid(
            row=0, column=2, padx=10, pady=6, sticky=tk.W
        )
        self.audio_codecs = [c for c in AUDIO_CODECS if c != "copy"]
        self.re_audio_codec_var = tk.StringVar(self.tab2)
        self.re_audio_codec_var.set(self.audio_codecs[0])
        self.re_audio_codec_option = ttk.OptionMenu(
            codec_frame,
            self.re_audio_codec_var,
            self.audio_codecs[0],
            *self.audio_codecs,
            style="Music.TMenubutton",
        )
        self.re_audio_codec_option.grid(row=0, column=3, padx=10, pady=6, sticky=tk.W)

        # Container Format
        ttk.Label(codec_frame, text="容器格式:", style="Music.TLabel").grid(
            row=1, column=0, padx=10, pady=6, sticky=tk.W
        )
        self.container_formats = CONTAINER_FORMATS
        self.re_container_format_var = tk.StringVar(self.tab2)
        self.re_container_format_var.set(self.container_formats[0])
        self.re_container_format_option = ttk.OptionMenu(
            codec_frame,
            self.re_container_format_var,
            self.container_formats[0],
            *self.container_formats,
            style="Music.TMenubutton",
        )
        self.re_container_format_option.grid(
            row=1, column=1, padx=10, pady=6, sticky=tk.W
        )

        # Quality (CQ/CRF)
        ttk.Label(codec_frame, text="品質 (CQ/CRF):", style="Music.TLabel").grid(
            row=1, column=2, padx=10, pady=6, sticky=tk.W
        )
        self.re_quality_var = tk.IntVar(value=30)
        quality_frame = ttk.Frame(codec_frame, style="Music.TFrame")
        quality_frame.grid(row=1, column=3, padx=10, pady=6, sticky=tk.W)
        self.re_quality_scale = tk.Scale(
            quality_frame,
            from_=0,
            to=51,
            orient=tk.HORIZONTAL,
            variable=self.re_quality_var,
            length=150,
            bg=self.colors["bg_dark"],
            fg=self.colors["text"],
            highlightthickness=0,
            troughcolor=self.colors["entry_bg"],
        )
        self.re_quality_scale.pack(side=tk.LEFT)

        # Add trace for codec quality defaults
        def on_codec_change(*args):
            selected = self.re_video_codec_var.get()
            if selected == BEST_CODEC_LABEL:
                self.re_quality_var.set(30)
            elif selected == STREAMING_CODEC_LABEL:
                self.re_quality_var.set(30)  # 串流優化預設 QP 30（最佳壓縮）

        self.re_video_codec_var.trace_add("write", on_codec_change)

        # === 選項區塊 ===
        options_frame = ttk.Frame(main_frame, style="Music.TFrame")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        self.re_low_vram_var = tk.BooleanVar(value=False)
        self.re_low_vram_check = ttk.Checkbutton(
            options_frame,
            text="🎮 低 VRAM 模式",
            variable=self.re_low_vram_var,
            style="Music.TCheckbutton",
        )
        self.re_low_vram_check.pack(side=tk.LEFT, padx=10)

        self.re_recycle_var = tk.BooleanVar(value=False)
        self.re_recycle_check = ttk.Checkbutton(
            options_frame,
            text="🗑️ 完成後移除原檔",
            variable=self.re_recycle_var,
            style="Music.TCheckbutton",
        )
        self.re_recycle_check.pack(side=tk.LEFT, padx=10)

        # === 控制按鈕 ===
        self.re_btn_frame = ttk.Frame(main_frame, style="Music.TFrame")
        self.re_btn_frame.pack(pady=10)

        self.re_encode_button = ttk.Button(
            self.re_btn_frame,
            text="▶ 開始編碼",
            command=self.start_reencode,
            style="Music.Success.TButton",
        )
        self.re_encode_button.pack(side=tk.LEFT, padx=8)

        self.re_pause_button = ttk.Button(
            self.re_btn_frame,
            text="⏸ 暫停",
            command=self.toggle_re_pause,
            state=tk.DISABLED,
            style="Music.Warning.TButton",
        )
        self.re_pause_button.pack(side=tk.LEFT, padx=8)

        self.re_stop_button = ttk.Button(
            self.re_btn_frame,
            text="⏹ 停止",
            command=self.stop_re,
            state=tk.DISABLED,
            style="Music.TButton",
        )
        self.re_stop_button.pack(side=tk.LEFT, padx=8)

        # === 進度區塊 ===
        progress_frame = ttk.Frame(main_frame, style="Music.TFrame")
        progress_frame.pack(fill=tk.X, pady=5)

        self.re_progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=400,
            mode="determinate",
            style="Music.Horizontal.TProgressbar",
        )
        self.re_progress_bar.pack(fill=tk.X, pady=5)

        self.re_status_label = ttk.Label(
            progress_frame, text="狀態：待機中", style="Music.Status.TLabel"
        )
        self.re_status_label.pack(anchor=tk.W, pady=5)

    def process_download_queue(self):
        while True:
            job = self.download_queue.get()
            self.after(0, self.on_dl_start, job)
            # Run the download
            try:
                start_download(job)
            except Exception as e:
                pass  # Error handling is inside start_download usually
            self.after(0, self.on_dl_finish, job)
            self.download_queue.task_done()

    def on_dl_start(self, job):
        self.current_dl_job = job
        self.dl_controller = job.task_controller
        self.download_button.config(state=tk.DISABLED)
        self.dl_pause_button.config(state=tk.NORMAL, text="Pause")
        self.dl_stop_button.config(state=tk.NORMAL)

    def on_dl_finish(self, job):
        self.download_button.config(state=tk.NORMAL)
        self.dl_pause_button.config(state=tk.DISABLED, text="Pause")
        self.dl_stop_button.config(state=tk.DISABLED)
        self.current_dl_job = None
        self.dl_controller = None

    def toggle_dl_pause(self):
        if self.dl_controller:
            if self.dl_controller.pause_event.is_set():
                self.dl_controller.resume()
                self.dl_pause_button.config(text="Pause")
            else:
                self.dl_controller.pause()
                self.dl_pause_button.config(text="Resume")

    def stop_dl(self):
        if self.dl_controller:
            self.dl_controller.stop()
            self.dl_stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Stopping...")

    def browse_download_output_path(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path_entry.delete(0, tk.END)
            self.output_path_entry.insert(0, path)

    def progress_hook(self, d):
        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total_bytes:
                percentage = (d["downloaded_bytes"] / total_bytes) * 100
                self.progress_bar["value"] = percentage
                self.status_label.config(text=f"Status: Downloading {percentage:.2f}%")
                self.update_idletasks()
        elif d["status"] == "finished":
            self.progress_bar["value"] = 100
            self.status_label.config(text="Status: Download finished.")
            self.update_idletasks()
            # Don't show messagebox here, maybe confusing if queued.
            # Or show it only if queue is empty?
            # Original code showed it. Let's keep it but maybe make it less blocking?
            # messagebox.showinfo("Success", "Download completed successfully.")
            # Better to show in status label for queued items.
        elif d["status"] == "error":
            self.status_label.config(text=f"Status: Error")
            self.update_idletasks()
            messagebox.showerror("Error", d["info"])

    def start_download(self):
        controller = TaskController()
        job = DownloadJob(
            url=self.url_entry.get(),
            start_time=self.start_time_entry.get(),
            end_time=self.end_time_entry.get(),
            output_path=self.output_path_entry.get(),
            output_filename=self.output_filename_entry.get(),
            video_codec=self.video_codec_var.get(),
            audio_codec=self.audio_codec_var.get(),
            container_format=self.container_format_var.get(),
            progress_hook=self.progress_hook,
            task_controller=controller,
            low_vram=self.dl_low_vram_var.get(),
            quality=self.dl_quality_var.get(),
        )
        self.download_queue.put(job)
        self.status_label.config(text=f"Status: Queued {job.url}")

    def browse_reencode_input_path(self):
        current_mode = self.re_mode_var.get()
        if current_mode == "single":
            file_path = filedialog.askopenfilename(
                title="Select a video file",
                filetypes=[
                    ("Video files", "*.mp4 *.mkv *.avi *.mov *.flv *.webm"),
                    ("All files", "*.*"),
                ],
            )
        else:  # batch mode
            file_path = filedialog.askdirectory(
                title="Select a directory containing video files"
            )

        if file_path:
            self.re_input_path_entry.delete(0, tk.END)
            self.re_input_path_entry.insert(0, file_path)

    def update_reencode_input_label(self):
        current_mode = self.re_mode_var.get()
        if current_mode == "single":
            self.re_input_path_label.config(text="Input Video File:")
            self.re_batch_filetypes_label.grid_remove()
            self.re_batch_filetypes_entry.grid_remove()
            self.re_output_filename_label.grid()
            self.re_output_filename_entry.grid()
        else:  # batch mode
            self.re_input_path_label.config(text="Input Directory:")
            self.re_batch_filetypes_label.grid()
            self.re_batch_filetypes_entry.grid()
            self.re_output_filename_label.grid_remove()
            self.re_output_filename_entry.grid_remove()

    def browse_reencode_output_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.re_output_dir_entry.delete(0, tk.END)
            self.re_output_dir_entry.insert(0, path)

    def reencode_progress_callback(self, percentage, message):
        if percentage is not None:
            self.re_progress_bar["value"] = percentage

        # Only update text if it's meaningful (avoid clearing specific errors or status too quickly if desired,
        # but here we generally just show what's passed)
        self.re_status_label.config(text=f"Status: {message}")
        self.update_idletasks()

    def toggle_re_pause(self):
        if self.re_controller:
            if self.re_controller.pause_event.is_set():
                self.re_controller.resume()
                self.re_pause_button.config(text="Pause")
            else:
                self.re_controller.pause()
                self.re_pause_button.config(text="Resume")

    def stop_re(self):
        if self.re_controller:
            self.re_controller.stop()
            self.re_stop_button.config(state=tk.DISABLED)
            self.re_status_label.config(text="Status: Stopping...")

    def start_reencode(self):
        input_path = self.re_input_path_entry.get()
        output_dir = self.re_output_dir_entry.get()
        output_filename = self.re_output_filename_entry.get()
        video_codec = self.re_video_codec_var.get()
        audio_codec = self.re_audio_codec_var.get()
        container_format = self.re_container_format_var.get()
        re_mode = self.re_mode_var.get()
        file_types = self.re_batch_filetypes_entry.get()
        quality = self.re_quality_var.get()

        if not input_path or not output_dir:
            messagebox.showerror(
                "Error", "Please fill in all required re-encoding fields."
            )
            return

        if re_mode == "single" and not output_filename:
            messagebox.showerror(
                "Error",
                "Please provide an output filename for single file re-encoding.",
            )
            return

        self.re_status_label.config(text="Status: Starting re-encoding...")
        self.re_progress_bar["value"] = 0
        self.re_encode_button.config(state=tk.DISABLED)
        self.re_pause_button.config(state=tk.NORMAL, text="Pause")
        self.re_stop_button.config(state=tk.NORMAL)

        self.re_controller = TaskController()

        # Run re-encoding in a separate thread to keep GUI responsive
        threading.Thread(
            target=self._run_reencode_task,
            args=(
                input_path,
                output_dir,
                output_filename,
                video_codec,
                audio_codec,
                container_format,
                re_mode,
                file_types,
                self.re_low_vram_var.get(),
                self.re_recycle_var.get(),
                quality,
            ),
        ).start()

    def _run_reencode_task(
        self,
        input_path,
        output_dir,
        output_filename,
        video_codec,
        audio_codec,
        container_format,
        re_mode,
        file_types,
        low_vram,
        recycle_original,
        quality,
    ):
        success, message = reencode_video(
            input_path,
            output_dir,
            output_filename,
            video_codec,
            audio_codec,
            container_format,
            re_mode,
            file_types,
            self.reencode_progress_callback,
            self.re_controller,
            low_vram,
            recycle_original,
            quality,
        )
        self.after(0, self._complete_reencode_task, success, message)

    def _complete_reencode_task(self, success, message):
        self.re_encode_button.config(state=tk.NORMAL)
        self.re_pause_button.config(state=tk.DISABLED, text="Pause")
        self.re_stop_button.config(state=tk.DISABLED)
        self.re_controller = None

        if success:
            self.re_progress_bar["value"] = 100
            self.re_status_label.config(text="Status: Re-encoding finished.")
            messagebox.showinfo("Success", message)
        else:
            if "stopped by user" in message.lower():
                self.re_progress_bar["value"] = 0
                self.re_status_label.config(text="Status: Re-encoding stopped.")
            else:
                self.re_progress_bar["value"] = 0
                self.re_status_label.config(text="Status: Re-encoding failed.")
                messagebox.showerror("Error", message)

    # === Clipper Methods ===

    def browse_clip_input(self):
        file_path = filedialog.askopenfilename(
            title="選擇影片檔案",
            filetypes=[
                ("影片檔案", "*.mp4 *.mkv *.avi *.mov *.flv *.webm *.ts"),
                ("所有檔案", "*.*"),
            ],
        )
        if file_path:
            self.clip_input_entry.delete(0, tk.END)
            self.clip_input_entry.insert(0, file_path)
            # Auto-fill output path and filename
            dir_name = os.path.dirname(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            self.clip_output_path_entry.delete(0, tk.END)
            self.clip_output_path_entry.insert(0, dir_name)
            self.clip_output_name_entry.delete(0, tk.END)
            self.clip_output_name_entry.insert(0, f"{base_name}_clip")

    def browse_clip_output(self):
        dir_path = filedialog.askdirectory(title="選擇輸出目錄")
        if dir_path:
            self.clip_output_path_entry.delete(0, tk.END)
            self.clip_output_path_entry.insert(0, dir_path)

    def start_clip_job(self):
        input_path = self.clip_input_entry.get()
        start_time = self.clip_start_entry.get()
        end_time = self.clip_end_entry.get()
        output_path = self.clip_output_path_entry.get()
        output_name = self.clip_output_name_entry.get()
        clip_mode = self.clip_mode_var.get()
        container_format = self.clip_format_var.get()

        if not all([input_path, start_time, end_time, output_path, output_name]):
            messagebox.showerror("錯誤", "請填寫所有必填欄位")
            return

        if not os.path.exists(input_path):
            messagebox.showerror("錯誤", f"輸入檔案不存在: {input_path}")
            return

        self.cl_controller = TaskController()

        job = ClipJob(
            input_path=input_path,
            start_time=start_time,
            end_time=end_time,
            output_path=output_path,
            output_filename=output_name,
            clip_mode=clip_mode,
            container_format=container_format,
            progress_hook=lambda d: self.after(0, self.update_clip_status, d),
            task_controller=self.cl_controller,
        )

        self.current_cl_job = job
        self.clipper_queue.put(job)

        # Update UI
        self.clip_start_btn.config(state=tk.DISABLED)
        self.clip_pause_btn.config(state=tk.NORMAL)
        self.clip_stop_btn.config(state=tk.NORMAL)
        self.clip_progress_bar.start(10)
        self.clip_status_label.config(text="狀態：處理中...")

    def process_clipper_queue(self):
        while True:
            job = self.clipper_queue.get()
            try:
                success, message = start_clip(job)
                self.after(0, self.on_clip_finish, success, message)
            except Exception as e:
                self.after(0, self.on_clip_finish, False, str(e))
            self.clipper_queue.task_done()

    def update_clip_status(self, d):
        status = d.get("status", "")
        info = d.get("info", "")
        self.clip_status_label.config(text=f"狀態：{info}")

    def on_clip_finish(self, success, message):
        self.clip_progress_bar.stop()
        self.clip_start_btn.config(state=tk.NORMAL)
        self.clip_pause_btn.config(state=tk.DISABLED)
        self.clip_stop_btn.config(state=tk.DISABLED)
        self.cl_controller = None
        self.current_cl_job = None

        if success:
            self.clip_progress_bar["value"] = 100
            self.clip_status_label.config(text="狀態：裁切完成！")
            messagebox.showinfo("成功", message)
        else:
            self.clip_progress_bar["value"] = 0
            if "停止" in message:
                self.clip_status_label.config(text="狀態：已停止")
            else:
                self.clip_status_label.config(text=f"狀態：失敗 - {message}")
                messagebox.showerror("錯誤", message)

    def toggle_clip_pause(self):
        if self.cl_controller:
            if self.cl_controller.pause_event.is_set():
                self.cl_controller.resume()
                self.clip_pause_btn.config(text="⏸ 暫停")
            else:
                self.cl_controller.pause()
                self.clip_pause_btn.config(text="▶ 繼續")

    def stop_clip(self):
        if self.cl_controller:
            self.cl_controller.stop()
            self.clip_stop_btn.config(state=tk.DISABLED)
            self.clip_status_label.config(text="狀態：正在停止...")

    # === Editor Methods ===

    def editor_load_video(self):
        """載入影片到編輯器"""
        file_path = filedialog.askopenfilename(
            title="選擇影片檔案",
            filetypes=[
                ("影片檔案", "*.mp4 *.mkv *.avi *.mov *.flv *.webm *.ts"),
                ("所有檔案", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            # 關閉舊的讀取器
            if self.editor_video_reader:
                self.editor_video_reader.close()

            # 建立新的讀取器
            self.editor_video_reader = VideoFrameReader(file_path)

            # 更新 UI
            filename = os.path.basename(file_path)
            self.editor_file_label.config(
                text=f"{filename} ({self.editor_video_reader.width}×{self.editor_video_reader.height})"
            )

            # 設定時間軸範圍
            self.editor_timeline.config(to=self.editor_video_reader.duration_ms)

            # 計算預覽縮放比例
            scale_w = PREVIEW_SIZE[0] / self.editor_video_reader.width
            scale_h = PREVIEW_SIZE[1] / self.editor_video_reader.height
            self.editor_preview_scale = min(scale_w, scale_h)

            # 初始化裁切框（置中，預設 200x150）
            self.editor_crop_w = int(200 / self.editor_preview_scale)
            self.editor_crop_h = int(150 / self.editor_preview_scale)
            self.editor_crop_x = (
                self.editor_video_reader.width - self.editor_crop_w
            ) // 2
            self.editor_crop_y = (
                self.editor_video_reader.height - self.editor_crop_h
            ) // 2

            # 清除關鍵幀
            self.editor_keyframe_manager.clear()
            self.editor_update_keyframe_list()

            # 設定輸出路徑
            dir_name = os.path.dirname(file_path)
            base_name = os.path.splitext(filename)[0]
            self.editor_output_entry.delete(0, tk.END)
            self.editor_output_entry.insert(
                0, os.path.join(dir_name, f"{base_name}_edited.mp4")
            )

            # 顯示第一幀
            self.editor_current_time_ms = 0
            self.editor_timeline_var.set(0)
            self.editor_update_preview()

            self.editor_status_label.config(text="狀態：影片已載入")

        except Exception as e:
            messagebox.showerror("錯誤", f"載入影片失敗: {e}")

    def editor_update_preview(self):
        """更新預覽畫面"""
        if not self.editor_video_reader:
            return

        # 取得當前幀
        frame = self.editor_video_reader.get_frame_for_preview(
            self.editor_current_time_ms, PREVIEW_SIZE
        )

        if frame:
            # 轉換為 Tkinter 可用格式
            self.editor_preview_image = ImageTk.PhotoImage(frame)

            # 清除並重繪 Canvas
            self.editor_canvas.delete("all")

            # 計算居中位置
            x_offset = (PREVIEW_SIZE[0] - frame.width) // 2
            y_offset = (PREVIEW_SIZE[1] - frame.height) // 2

            # 繪製影片幀
            self.editor_canvas.create_image(
                x_offset, y_offset, anchor=tk.NW, image=self.editor_preview_image
            )

            # 繪製裁切框
            self.editor_draw_crop_rect(x_offset, y_offset)

        # 更新時間標籤
        current = format_time_short(self.editor_current_time_ms)
        total = format_time_short(self.editor_video_reader.duration_ms)
        self.editor_time_label.config(text=f"{current} / {total}")

    def editor_draw_crop_rect(self, x_offset=0, y_offset=0):
        """繪製裁切框"""
        # 將原始座標轉換為預覽座標
        x1 = x_offset + int(self.editor_crop_x * self.editor_preview_scale)
        y1 = y_offset + int(self.editor_crop_y * self.editor_preview_scale)
        x2 = x_offset + int(
            (self.editor_crop_x + self.editor_crop_w) * self.editor_preview_scale
        )
        y2 = y_offset + int(
            (self.editor_crop_y + self.editor_crop_h) * self.editor_preview_scale
        )

        # 繪製裁切框（霓虹藍色邊框）
        self.editor_canvas.create_rectangle(
            x1, y1, x2, y2, outline=self.colors["accent3"], width=2, tags="crop_rect"
        )

        # 繪製角落控制點
        for cx, cy in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
            self.editor_canvas.create_oval(
                cx - 5,
                cy - 5,
                cx + 5,
                cy + 5,
                fill=self.colors["accent"],
                outline=self.colors["accent3"],
                tags="crop_rect",
            )

    def editor_on_timeline_change(self, value):
        """時間軸變更事件"""
        self.editor_current_time_ms = int(float(value))
        self.editor_update_preview()

    def editor_on_canvas_click(self, event):
        """Canvas 點擊事件 - 開始拖動"""
        self.editor_drag_start = (event.x, event.y)

    def editor_on_canvas_drag(self, event):
        """Canvas 拖動事件 - 移動裁切框"""
        if not self.editor_drag_start or not self.editor_video_reader:
            return

        # 計算位移（轉換為原始座標）
        dx = int((event.x - self.editor_drag_start[0]) / self.editor_preview_scale)
        dy = int((event.y - self.editor_drag_start[1]) / self.editor_preview_scale)

        # 更新裁切框位置（限制在影片範圍內）
        new_x = max(
            0,
            min(
                self.editor_crop_x + dx,
                self.editor_video_reader.width - self.editor_crop_w,
            ),
        )
        new_y = max(
            0,
            min(
                self.editor_crop_y + dy,
                self.editor_video_reader.height - self.editor_crop_h,
            ),
        )

        self.editor_crop_x = new_x
        self.editor_crop_y = new_y
        self.editor_drag_start = (event.x, event.y)

        # 重繪預覽
        self.editor_update_preview()

    def editor_on_canvas_release(self, event):
        """Canvas 釋放事件"""
        self.editor_drag_start = None

    def editor_on_ratio_change(self):
        """比例變更事件"""
        ratio_name = self.editor_ratio_var.get()
        ratio = ASPECT_RATIOS.get(ratio_name)

        if ratio and self.editor_video_reader:
            # 根據比例調整裁切框大小
            w, h = ratio
            # 計算最大可容納的裁切框
            max_w = self.editor_video_reader.width
            max_h = self.editor_video_reader.height

            if (max_w / w) * h <= max_h:
                self.editor_crop_w = max_w
                self.editor_crop_h = int((max_w / w) * h)
            else:
                self.editor_crop_h = max_h
                self.editor_crop_w = int((max_h / h) * w)

            # 置中
            self.editor_crop_x = (max_w - self.editor_crop_w) // 2
            self.editor_crop_y = (max_h - self.editor_crop_h) // 2

            # 更新輸出尺寸
            self.editor_width_var.set(str(self.editor_crop_w))
            self.editor_height_var.set(str(self.editor_crop_h))

            self.editor_update_preview()

    def editor_add_keyframe(self):
        """新增關鍵幀"""
        if not self.editor_video_reader:
            messagebox.showwarning("警告", "請先載入影片")
            return

        crop = CropRegion(
            x=self.editor_crop_x,
            y=self.editor_crop_y,
            width=self.editor_crop_w,
            height=self.editor_crop_h,
        )

        self.editor_keyframe_manager.add_keyframe(self.editor_current_time_ms, crop)
        self.editor_update_keyframe_list()
        self.editor_status_label.config(
            text=f"狀態：已新增關鍵幀 @ {format_time_short(self.editor_current_time_ms)}"
        )

    def editor_remove_keyframe(self):
        """移除當前時間的關鍵幀"""
        self.editor_keyframe_manager.remove_keyframe(self.editor_current_time_ms)
        self.editor_update_keyframe_list()

    def editor_clear_keyframes(self):
        """清除所有關鍵幀"""
        if messagebox.askyesno("確認", "確定要清除所有關鍵幀嗎？"):
            self.editor_keyframe_manager.clear()
            self.editor_update_keyframe_list()

    def editor_update_keyframe_list(self):
        """更新關鍵幀列表顯示"""
        if not self.editor_keyframe_manager.keyframes:
            self.editor_keyframe_list.config(text="尚未設定關鍵幀")
        else:
            times = [
                format_time_short(kf.time_ms)
                for kf in self.editor_keyframe_manager.keyframes
            ]
            self.editor_keyframe_list.config(text=f"關鍵幀: {', '.join(times)}")

    def editor_browse_output(self):
        """選擇輸出檔案路徑"""
        file_path = filedialog.asksaveasfilename(
            title="儲存影片",
            defaultextension=".mp4",
            filetypes=[
                ("MP4 檔案", "*.mp4"),
                ("MKV 檔案", "*.mkv"),
                ("所有檔案", "*.*"),
            ],
        )
        if file_path:
            self.editor_output_entry.delete(0, tk.END)
            self.editor_output_entry.insert(0, file_path)

    def editor_export(self):
        """匯出影片"""
        if not self.editor_video_reader:
            messagebox.showwarning("警告", "請先載入影片")
            return

        if not self.editor_keyframe_manager.keyframes:
            messagebox.showwarning("警告", "請至少設定一個關鍵幀")
            return

        output_path = self.editor_output_entry.get()
        if not output_path:
            messagebox.showwarning("警告", "請指定輸出路徑")
            return

        try:
            output_width = int(self.editor_width_var.get())
            output_height = int(self.editor_height_var.get())
        except ValueError:
            messagebox.showerror("錯誤", "輸出尺寸必須是數字")
            return

        self.editor_status_label.config(text="狀態：匯出中...")
        self.update_idletasks()

        # 在背景執行匯出
        def do_export():
            success, message = export_video_with_keyframes(
                input_path=self.editor_video_reader.video_path,
                output_path=output_path,
                keyframe_manager=self.editor_keyframe_manager,
                output_width=output_width,
                output_height=output_height,
            )
            self.after(0, self.editor_on_export_finish, success, message)

        threading.Thread(target=do_export, daemon=True).start()

    def editor_on_export_finish(self, success, message):
        """匯出完成回調"""
        if success:
            self.editor_status_label.config(text="狀態：匯出完成！")
            messagebox.showinfo("成功", message)
        else:
            self.editor_status_label.config(text=f"狀態：匯出失敗")
            messagebox.showerror("錯誤", message)

    def quit_app(self):
        """結束程式"""
        # 關閉編輯器的影片讀取器
        if self.editor_video_reader:
            self.editor_video_reader.close()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
