import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
from downloader import DownloadJob, start_download
from reencoder import reencode_video
from merger import merge_videos
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
)
from utils import get_media_info


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎵 URL Video Clip Downloader")
        self.geometry("950x650")

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
        self.current_dl_job = None

        # Create Tab Control
        self.tabControl = ttk.Notebook(self, style="Music.TNotebook")
        self.tab1 = ttk.Frame(self.tabControl, style="Music.TFrame")
        self.tab2 = ttk.Frame(self.tabControl, style="Music.TFrame")
        self.tab3 = ttk.Frame(self.tabControl, style="Music.TFrame")
        self.tab4 = ttk.Frame(self.tabControl, style="Music.TFrame")
        self.tabControl.add(self.tab1, text="🎬 Downloader")
        self.tabControl.add(self.tab2, text="🔄 Re-encoder")
        self.tabControl.add(self.tab3, text="🔗 Merger")
        self.tabControl.add(self.tab4, text="📊 File Info")
        self.tabControl.pack(expand=1, fill="both", padx=10, pady=10)

        # --- Tab 1: Downloader ---
        self.create_downloader_tab()

        # --- Tab 2: Re-encoder ---
        self.create_reencoder_tab()

        # --- Tab 3: Merger ---
        self.create_merger_tab()

        # --- Tab 4: File Info ---
        self.create_file_info_tab()

        self.download_queue = queue.Queue()
        self.worker_thread = threading.Thread(
            target=self.process_download_queue, daemon=True
        )
        self.worker_thread.start()

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
        # Merge Mode Selection
        self.merge_mode_var = tk.StringVar(self.tab3, value="selected")
        self.merge_selected_radio = ttk.Radiobutton(
            self.tab3,
            text="Selected Files",
            variable=self.merge_mode_var,
            value="selected",
            command=self.update_merge_input_ui,
        )
        self.merge_selected_radio.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.merge_dir_radio = ttk.Radiobutton(
            self.tab3,
            text="Directory",
            variable=self.merge_mode_var,
            value="directory",
            command=self.update_merge_input_ui,
        )
        self.merge_dir_radio.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Input UI Container (Dynamic)
        self.merge_input_frame = ttk.Frame(self.tab3)
        self.merge_input_frame.grid(
            row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.EW
        )
        self.merge_input_frame.columnconfigure(1, weight=1)

        # Initial Setup (Selected Files Mode)
        self.merge_files_listbox = tk.Listbox(
            self.merge_input_frame, height=5, selectmode=tk.EXTENDED
        )
        self.merge_files_listbox.grid(row=0, column=0, columnspan=2, sticky=tk.EW)
        self.merge_files_btn_frame = ttk.Frame(self.merge_input_frame)
        self.merge_files_btn_frame.grid(row=0, column=2, sticky=tk.NS)
        self.merge_add_files_btn = ttk.Button(
            self.merge_files_btn_frame,
            text="Add Files",
            command=self.browse_merge_files,
        )
        self.merge_add_files_btn.pack(fill=tk.X, pady=2)
        self.merge_clear_files_btn = ttk.Button(
            self.merge_files_btn_frame,
            text="Clear",
            command=lambda: self.merge_files_listbox.delete(0, tk.END),
        )
        self.merge_clear_files_btn.pack(fill=tk.X, pady=2)

        # Directory UI (Hidden initially)
        self.merge_dir_label = ttk.Label(
            self.merge_input_frame, text="Input Directory:"
        )
        self.merge_dir_entry = ttk.Entry(self.merge_input_frame)
        self.merge_dir_browse_btn = ttk.Button(
            self.merge_input_frame, text="Browse", command=self.browse_merge_dir
        )

        # Output Directory
        self.merge_output_dir_label = ttk.Label(self.tab3, text="Output Directory:")
        self.merge_output_dir_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.merge_output_dir_entry = ttk.Entry(self.tab3)
        self.merge_output_dir_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        self.merge_browse_output_btn = ttk.Button(
            self.tab3, text="Browse", command=self.browse_merge_output_dir
        )
        self.merge_browse_output_btn.grid(row=2, column=2, padx=5, pady=5)

        # Output Filename
        self.merge_output_filename_label = ttk.Label(self.tab3, text="Output Filename:")
        self.merge_output_filename_label.grid(
            row=3, column=0, padx=5, pady=5, sticky=tk.W
        )
        self.merge_output_filename_entry = ttk.Entry(self.tab3)
        self.merge_output_filename_entry.grid(
            row=3, column=1, padx=5, pady=5, sticky=tk.EW
        )

        # Output Container (optional, for extension)
        self.merge_container_label = ttk.Label(self.tab3, text="Output Format:")
        self.merge_container_label.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.merge_containers = MERGE_CONTAINER_FORMATS
        self.merge_container_var = tk.StringVar(self.tab3)
        self.merge_container_var.set(self.merge_containers[0])
        self.merge_container_option = ttk.OptionMenu(
            self.tab3,
            self.merge_container_var,
            self.merge_containers[0],
            *self.merge_containers,
        )
        self.merge_container_option.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)

        # Merge Video Codec
        self.merge_video_codec_label = ttk.Label(self.tab3, text="Video Codec:")
        self.merge_video_codec_label.grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        # For merge, we default to copy, but allow re-encoding
        # Using full VIDEO_CODECS list which includes "Best" and "copy"
        self.merge_video_codecs = VIDEO_CODECS
        self.merge_video_codec_var = tk.StringVar(self.tab3)
        self.merge_video_codec_var.set("copy")  # Default to copy
        self.merge_video_codec_option = ttk.OptionMenu(
            self.tab3, self.merge_video_codec_var, "copy", *self.merge_video_codecs
        )
        self.merge_video_codec_option.grid(
            row=5, column=1, padx=5, pady=5, sticky=tk.EW
        )

        # Recycle Original Checkbox
        self.merge_recycle_var = tk.BooleanVar(value=False)
        self.merge_recycle_check = ttk.Checkbutton(
            self.tab3,
            text="Delete original after success (Recycle Bin)",
            variable=self.merge_recycle_var,
        )
        self.merge_recycle_check.grid(
            row=6, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W
        )

        # Merge Button
        self.merge_btn_frame = ttk.Frame(self.tab3)
        self.merge_btn_frame.grid(row=7, column=1, pady=10)

        self.merge_button = ttk.Button(
            self.merge_btn_frame, text="Start Merge", command=self.start_merge
        )
        self.merge_button.pack(side=tk.LEFT, padx=5)

        self.merge_pause_button = ttk.Button(
            self.merge_btn_frame,
            text="Pause",
            command=self.toggle_merge_pause,
            state=tk.DISABLED,
        )
        self.merge_pause_button.pack(side=tk.LEFT, padx=5)

        self.merge_stop_button = ttk.Button(
            self.merge_btn_frame,
            text="Stop",
            command=self.stop_merge,
            state=tk.DISABLED,
        )
        self.merge_stop_button.pack(side=tk.LEFT, padx=5)

        # Progress
        self.merge_progress_bar = ttk.Progressbar(
            self.tab3, orient="horizontal", length=300, mode="determinate"
        )
        self.merge_progress_bar.grid(row=8, column=0, columnspan=3, padx=5, pady=5)
        self.merge_status_label = ttk.Label(self.tab3, text="Status: Idle")
        self.merge_status_label.grid(
            row=9, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W
        )

        self.tab3.columnconfigure(1, weight=1)

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

    def create_file_info_tab(self):
        # File Selection
        self.info_file_label = ttk.Label(self.tab4, text="Video File:")
        self.info_file_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.info_file_entry = ttk.Entry(self.tab4, width=50)
        self.info_file_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.info_browse_btn = ttk.Button(
            self.tab4, text="Browse", command=self.browse_info_file
        )
        self.info_browse_btn.grid(row=0, column=2, padx=5, pady=5)

        # Analyze Button
        self.info_analyze_btn = ttk.Button(
            self.tab4, text="Analyze File", command=self.analyze_file
        )
        self.info_analyze_btn.grid(row=1, column=1, pady=10, sticky=tk.W)

        # Info Display
        self.info_text = tk.Text(self.tab4, height=15, width=60)
        self.info_text.grid(
            row=2, column=0, columnspan=3, padx=5, pady=5, sticky="nsew"
        )

        # Scrollbar
        self.info_scroll = ttk.Scrollbar(self.tab4, command=self.info_text.yview)
        self.info_scroll.grid(row=2, column=3, sticky="ns")
        self.info_text["yscrollcommand"] = self.info_scroll.set

        self.tab4.columnconfigure(1, weight=1)
        self.tab4.rowconfigure(2, weight=1)

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
        """建立 Downloader 分頁 - 簡化版，只支援 copy 模式下載"""

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
        self.url_label = ttk.Label(
            source_frame, text="URL / 本機檔案:", style="Music.TLabel"
        )
        self.url_label.grid(row=0, column=0, padx=10, pady=8, sticky=tk.W)
        self.url_entry = ttk.Entry(
            source_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.url_entry.grid(
            row=0, column=1, columnspan=2, padx=10, pady=8, sticky=tk.EW
        )

        # Start Time
        self.start_time_label = ttk.Label(
            source_frame, text="開始時間 (HH:MM:SS):", style="Music.TLabel"
        )
        self.start_time_label.grid(row=1, column=0, padx=10, pady=8, sticky=tk.W)
        self.start_time_entry = ttk.Entry(
            source_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.start_time_entry.grid(row=1, column=1, padx=10, pady=8, sticky=tk.EW)

        # End Time
        self.end_time_label = ttk.Label(
            source_frame, text="結束時間 (HH:MM:SS):", style="Music.TLabel"
        )
        self.end_time_label.grid(row=2, column=0, padx=10, pady=8, sticky=tk.W)
        self.end_time_entry = ttk.Entry(
            source_frame, style="Music.TEntry", font=("Segoe UI", 10)
        )
        self.end_time_entry.grid(row=2, column=1, padx=10, pady=8, sticky=tk.EW)

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
        # 直接使用 copy 模式，不再顯示編碼選項
        self.video_codec_var = tk.StringVar(self.tab1)
        self.video_codec_var.set(DOWNLOADER_VIDEO_CODECS[0])  # 固定為 copy 模式
        self.audio_codec_var = tk.StringVar(self.tab1)
        self.audio_codec_var.set(DOWNLOADER_AUDIO_CODECS[0])  # 固定為 copy
        self.dl_quality_var = tk.IntVar(value=30)  # 保留變數但不使用
        self.dl_low_vram_var = tk.BooleanVar(value=False)  # 保留變數但不使用

        # 提示訊息
        info_label = ttk.Label(
            main_frame,
            text="💡 下載模式：直接擷取原始影音，不進行任何轉碼處理",
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
                self.re_quality_var.set(26)  # 串流優化預設 CQ 26

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


if __name__ == "__main__":
    app = App()
    app.mainloop()
