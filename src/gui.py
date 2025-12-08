import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
from downloader import DownloadJob, start_download
from reencoder import reencode_video
from merger import merge_videos
from task_utils import TaskController

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("URL Video Clip Downloader")
        self.geometry("600x450") # Increased height for new buttons

        # Task Controllers
        self.dl_controller = None
        self.re_controller = None
        self.me_controller = None
        self.current_dl_job = None

        # Create Tab Control
        self.tabControl = ttk.Notebook(self)
        self.tab1 = ttk.Frame(self.tabControl)
        self.tab2 = ttk.Frame(self.tabControl)
        self.tab3 = ttk.Frame(self.tabControl)
        self.tabControl.add(self.tab1, text='Downloader')
        self.tabControl.add(self.tab2, text='Re-encoder')
        self.tabControl.add(self.tab3, text='Merger')
        self.tabControl.pack(expand=1, fill="both")

        # --- Tab 1: Downloader ---
        self.create_downloader_tab()

        # --- Tab 2: Re-encoder ---
        self.create_reencoder_tab()

        # --- Tab 3: Merger ---
        self.create_merger_tab()

        self.download_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self.process_download_queue, daemon=True)
        self.worker_thread.start()

    def create_merger_tab(self):
        # Merge Mode Selection
        self.merge_mode_var = tk.StringVar(self.tab3, value="selected")
        self.merge_selected_radio = ttk.Radiobutton(self.tab3, text="Selected Files", variable=self.merge_mode_var, value="selected", command=self.update_merge_input_ui)
        self.merge_selected_radio.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.merge_dir_radio = ttk.Radiobutton(self.tab3, text="Directory", variable=self.merge_mode_var, value="directory", command=self.update_merge_input_ui)
        self.merge_dir_radio.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Input UI Container (Dynamic)
        self.merge_input_frame = ttk.Frame(self.tab3)
        self.merge_input_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.EW)
        self.merge_input_frame.columnconfigure(1, weight=1)

        # Initial Setup (Selected Files Mode)
        self.merge_files_listbox = tk.Listbox(self.merge_input_frame, height=5, selectmode=tk.EXTENDED)
        self.merge_files_listbox.grid(row=0, column=0, columnspan=2, sticky=tk.EW)
        self.merge_files_btn_frame = ttk.Frame(self.merge_input_frame)
        self.merge_files_btn_frame.grid(row=0, column=2, sticky=tk.NS)
        self.merge_add_files_btn = ttk.Button(self.merge_files_btn_frame, text="Add Files", command=self.browse_merge_files)
        self.merge_add_files_btn.pack(fill=tk.X, pady=2)
        self.merge_clear_files_btn = ttk.Button(self.merge_files_btn_frame, text="Clear", command=lambda: self.merge_files_listbox.delete(0, tk.END))
        self.merge_clear_files_btn.pack(fill=tk.X, pady=2)

        # Directory UI (Hidden initially)
        self.merge_dir_label = ttk.Label(self.merge_input_frame, text="Input Directory:")
        self.merge_dir_entry = ttk.Entry(self.merge_input_frame)
        self.merge_dir_browse_btn = ttk.Button(self.merge_input_frame, text="Browse", command=self.browse_merge_dir)

        # Output Directory
        self.merge_output_dir_label = ttk.Label(self.tab3, text="Output Directory:")
        self.merge_output_dir_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.merge_output_dir_entry = ttk.Entry(self.tab3)
        self.merge_output_dir_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        self.merge_browse_output_btn = ttk.Button(self.tab3, text="Browse", command=self.browse_merge_output_dir)
        self.merge_browse_output_btn.grid(row=2, column=2, padx=5, pady=5)

        # Output Filename
        self.merge_output_filename_label = ttk.Label(self.tab3, text="Output Filename:")
        self.merge_output_filename_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.merge_output_filename_entry = ttk.Entry(self.tab3)
        self.merge_output_filename_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # Output Container (optional, for extension)
        self.merge_container_label = ttk.Label(self.tab3, text="Output Format:")
        self.merge_container_label.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.merge_containers = ["mp4", "mkv", "mov", "avi", "ts"]
        self.merge_container_var = tk.StringVar(self.tab3)
        self.merge_container_var.set(self.merge_containers[0])
        self.merge_container_option = ttk.OptionMenu(self.tab3, self.merge_container_var, self.merge_containers[0], *self.merge_containers)
        self.merge_container_option.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)

        # Recycle Original Checkbox
        self.merge_recycle_var = tk.BooleanVar(value=False)
        self.merge_recycle_check = ttk.Checkbutton(self.tab3, text="Delete original after success (Recycle Bin)", variable=self.merge_recycle_var)
        self.merge_recycle_check.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # Merge Button
        self.merge_btn_frame = ttk.Frame(self.tab3)
        self.merge_btn_frame.grid(row=6, column=1, pady=10)

        self.merge_button = ttk.Button(self.merge_btn_frame, text="Start Merge", command=self.start_merge)
        self.merge_button.pack(side=tk.LEFT, padx=5)

        self.merge_pause_button = ttk.Button(self.merge_btn_frame, text="Pause", command=self.toggle_merge_pause, state=tk.DISABLED)
        self.merge_pause_button.pack(side=tk.LEFT, padx=5)

        self.merge_stop_button = ttk.Button(self.merge_btn_frame, text="Stop", command=self.stop_merge, state=tk.DISABLED)
        self.merge_stop_button.pack(side=tk.LEFT, padx=5)

        # Progress
        self.merge_progress_bar = ttk.Progressbar(self.tab3, orient="horizontal", length=300, mode="determinate")
        self.merge_progress_bar.grid(row=7, column=0, columnspan=3, padx=5, pady=5)
        self.merge_status_label = ttk.Label(self.tab3, text="Status: Idle")
        self.merge_status_label.grid(row=8, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)

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
        files = filedialog.askopenfilenames(title="Select Video Files to Merge")
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
            self.merge_progress_bar['value'] = percentage
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

        if not output_dir or not output_filename:
             messagebox.showerror("Error", "Please specify output directory and filename.")
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
                files = sorted([os.path.join(input_dir, f) for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))])
                # Basic filter for video extensions?
                video_exts = ('.mp4', '.mkv', '.mov', '.avi', '.ts', '.flv', '.webm')
                input_files = [f for f in files if f.lower().endswith(video_exts)]
                
                if not input_files:
                     messagebox.showerror("Error", "No video files found in directory.")
                     return
            except Exception as e:
                messagebox.showerror("Error", f"Error reading directory: {e}")
                return

        output_path = os.path.join(output_dir, f"{output_filename}.{container}")
        
        self.merge_status_label.config(text="Status: Starting merge...")
        self.merge_progress_bar['value'] = 0
        self.merge_button.config(state=tk.DISABLED)
        self.merge_pause_button.config(state=tk.NORMAL, text="Pause")
        self.merge_stop_button.config(state=tk.NORMAL)

        self.me_controller = TaskController()

        threading.Thread(target=self._run_merge_task, args=(input_files, output_path, self.merge_recycle_var.get())).start()

    def _run_merge_task(self, input_files, output_path, recycle_original):
        success, message = merge_videos(input_files, output_path, self.merge_progress_callback, self.me_controller, recycle_original)
        self.after(0, self._complete_merge_task, success, message)

    def _complete_merge_task(self, success, message):
        self.merge_button.config(state=tk.NORMAL)
        self.merge_pause_button.config(state=tk.DISABLED, text="Pause")
        self.merge_stop_button.config(state=tk.DISABLED)
        self.me_controller = None

        if success:
            self.merge_progress_bar['value'] = 100
            self.merge_status_label.config(text="Status: Merge finished.")
            messagebox.showinfo("Success", message)
        else:
            if "stopped by user" in message.lower():
                self.merge_progress_bar['value'] = 0
                self.merge_status_label.config(text="Status: Merge stopped.")
            else:
                self.merge_progress_bar['value'] = 0
                self.merge_status_label.config(text="Status: Merge failed.")
                messagebox.showerror("Error", message)

    def create_downloader_tab(self):
        # URL
        self.url_label = ttk.Label(self.tab1, text="URL:")
        self.url_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.url_entry = ttk.Entry(self.tab1, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # Start Time
        self.start_time_label = ttk.Label(self.tab1, text="Start Time (HH:MM:SS):")
        self.start_time_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.start_time_entry = ttk.Entry(self.tab1)
        self.start_time_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        # End Time
        self.end_time_label = ttk.Label(self.tab1, text="End Time (HH:MM:SS):")
        self.end_time_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.end_time_entry = ttk.Entry(self.tab1)
        self.end_time_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)

        # Output Path
        self.output_path_label = ttk.Label(self.tab1, text="Output Path:")
        self.output_path_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.output_path_entry = ttk.Entry(self.tab1)
        self.output_path_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        self.browse_button = ttk.Button(self.tab1, text="Browse", command=self.browse_download_output_path)
        self.browse_button.grid(row=3, column=2, padx=5, pady=5)

        # Output Filename
        self.output_filename_label = ttk.Label(self.tab1, text="Output Filename:")
        self.output_filename_label.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.output_filename_entry = ttk.Entry(self.tab1)
        self.output_filename_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)

        # Video Codec
        self.video_codec_label = ttk.Label(self.tab1, text="Video Codec:")
        self.video_codec_label.grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        self.video_codecs = ["hevc_nvenc", "hevc_amf", "hevc_qsv", "libx265", "libx264", "vp9", "mpeg4", "copy"]
        self.video_codec_var = tk.StringVar(self.tab1)
        self.video_codec_var.set(self.video_codecs[0]) # Default to hevc_nvenc
        self.video_codec_option = ttk.OptionMenu(self.tab1, self.video_codec_var, self.video_codecs[0], *self.video_codecs)
        self.video_codec_option.grid(row=5, column=1, padx=5, pady=5, sticky=tk.EW)

        # Audio Codec
        self.audio_codec_label = ttk.Label(self.tab1, text="Audio Codec:")
        self.audio_codec_label.grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
        self.audio_codecs = ["aac", "opus", "libmp3lame", "copy"]
        self.audio_codec_var = tk.StringVar(self.tab1)
        self.audio_codec_var.set(self.audio_codecs[0]) # Default to aac
        self.audio_codec_option = ttk.OptionMenu(self.tab1, self.audio_codec_var, self.audio_codecs[0], *self.audio_codecs)
        self.audio_codec_option.grid(row=6, column=1, padx=5, pady=5, sticky=tk.EW)

        # Container Format
        self.container_format_label = ttk.Label(self.tab1, text="Container Format:")
        self.container_format_label.grid(row=7, column=0, padx=5, pady=5, sticky=tk.W)
        self.container_formats = ["mp4", "mkv", "mov", "avi"]
        self.container_format_var = tk.StringVar(self.tab1)
        self.container_format_var.set(self.container_formats[0]) # Default to mp4
        self.container_format_option = ttk.OptionMenu(self.tab1, self.container_format_var, self.container_formats[0], *self.container_formats)
        self.container_format_option.grid(row=7, column=1, padx=5, pady=5, sticky=tk.EW)

        # Low VRAM Mode Checkbox
        self.dl_low_vram_var = tk.BooleanVar(value=False)
        self.dl_low_vram_check = ttk.Checkbutton(self.tab1, text="Low VRAM Mode (Prevent Lag)", variable=self.dl_low_vram_var)
        self.dl_low_vram_check.grid(row=7, column=2, padx=5, pady=5, sticky=tk.W)

        # Download Button
        self.download_btn_frame = ttk.Frame(self.tab1)
        self.download_btn_frame.grid(row=8, column=1, pady=10)
        
        self.download_button = ttk.Button(self.download_btn_frame, text="Start Download", command=self.start_download)
        self.download_button.pack(side=tk.LEFT, padx=5)

        self.dl_pause_button = ttk.Button(self.download_btn_frame, text="Pause", command=self.toggle_dl_pause, state=tk.DISABLED)
        self.dl_pause_button.pack(side=tk.LEFT, padx=5)

        self.dl_stop_button = ttk.Button(self.download_btn_frame, text="Stop", command=self.stop_dl, state=tk.DISABLED)
        self.dl_stop_button.pack(side=tk.LEFT, padx=5)

        # Progress
        self.progress_bar = ttk.Progressbar(self.tab1, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=9, column=0, columnspan=3, padx=5, pady=5)
        self.status_label = ttk.Label(self.tab1, text="Status: Idle")
        self.status_label.grid(row=10, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)

        self.tab1.columnconfigure(1, weight=1)

    def create_reencoder_tab(self):
        # Re-encode Mode Selection
        self.re_mode_var = tk.StringVar(self.tab2, value="single")
        self.re_single_file_radio = ttk.Radiobutton(self.tab2, text="Single File", variable=self.re_mode_var, value="single", command=self.update_reencode_input_label)
        self.re_single_file_radio.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.re_batch_dir_radio = ttk.Radiobutton(self.tab2, text="Batch Directory", variable=self.re_mode_var, value="batch", command=self.update_reencode_input_label)
        self.re_batch_dir_radio.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Input Path
        self.re_input_path_label = ttk.Label(self.tab2, text="Input Video File:")
        self.re_input_path_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.re_input_path_entry = ttk.Entry(self.tab2, width=50)
        self.re_input_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.re_browse_input_button = ttk.Button(self.tab2, text="Browse", command=self.browse_reencode_input_path)
        self.re_browse_input_button.grid(row=1, column=2, padx=5, pady=5)

        # Batch File Types (only visible in batch mode)
        self.re_batch_filetypes_label = ttk.Label(self.tab2, text="File Types (e.g., mp4,mkv):")
        self.re_batch_filetypes_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.re_batch_filetypes_entry = ttk.Entry(self.tab2)
        self.re_batch_filetypes_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        self.re_batch_filetypes_label.grid_remove() # Hide by default
        self.re_batch_filetypes_entry.grid_remove() # Hide by default

        # Output Directory
        self.re_output_dir_label = ttk.Label(self.tab2, text="Output Directory:")
        self.re_output_dir_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.re_output_dir_entry = ttk.Entry(self.tab2)
        self.re_output_dir_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        self.re_browse_output_button = ttk.Button(self.tab2, text="Browse", command=self.browse_reencode_output_dir)
        self.re_browse_output_button.grid(row=3, column=2, padx=5, pady=5)

        # Output Filename
        self.re_output_filename_label = ttk.Label(self.tab2, text="Output Filename:")
        self.re_output_filename_label.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.re_output_filename_entry = ttk.Entry(self.tab2)
        self.re_output_filename_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)

        # Video Codec
        self.re_video_codec_label = ttk.Label(self.tab2, text="Video Codec:")
        self.re_video_codec_label.grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        self.video_codecs = ["hevc_nvenc", "hevc_amf", "hevc_qsv", "libx265", "libx264", "vp9", "mpeg4"]
        self.re_video_codec_var = tk.StringVar(self.tab2)
        self.re_video_codec_var.set(self.video_codecs[0]) # Default to hevc_nvenc
        self.re_video_codec_option = ttk.OptionMenu(self.tab2, self.re_video_codec_var, self.video_codecs[0], *self.video_codecs)
        self.re_video_codec_option.grid(row=5, column=1, padx=5, pady=5, sticky=tk.EW)

        # Audio Codec
        self.re_audio_codec_label = ttk.Label(self.tab2, text="Audio Codec:")
        self.re_audio_codec_label.grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
        self.audio_codecs = ["aac", "opus", "libmp3lame"]
        self.re_audio_codec_var = tk.StringVar(self.tab2)
        self.re_audio_codec_var.set(self.audio_codecs[0]) # Default to aac
        self.re_audio_codec_option = ttk.OptionMenu(self.tab2, self.re_audio_codec_var, self.audio_codecs[0], *self.audio_codecs)
        self.re_audio_codec_option.grid(row=6, column=1, padx=5, pady=5, sticky=tk.EW)

        # Container Format
        self.re_container_format_label = ttk.Label(self.tab2, text="Container Format:")
        self.re_container_format_label.grid(row=7, column=0, padx=5, pady=5, sticky=tk.W)
        self.container_formats = ["mp4", "mkv", "mov", "avi"]
        self.re_container_format_var = tk.StringVar(self.tab2)
        self.re_container_format_var.set(self.container_formats[0]) # Default to mp4
        self.re_container_format_option = ttk.OptionMenu(self.tab2, self.re_container_format_var, self.container_formats[0], *self.container_formats)
        self.re_container_format_option.grid(row=7, column=1, padx=5, pady=5, sticky=tk.EW)

        # Low VRAM Mode Checkbox
        self.re_low_vram_var = tk.BooleanVar(value=False)
        self.re_low_vram_check = ttk.Checkbutton(self.tab2, text="Low VRAM Mode (Prevent Lag)", variable=self.re_low_vram_var)
        self.re_low_vram_check.grid(row=7, column=2, padx=5, pady=5, sticky=tk.W)

        # Recycle Original Checkbox
        self.re_recycle_var = tk.BooleanVar(value=False)
        self.re_recycle_check = ttk.Checkbutton(self.tab2, text="Delete original after success (Recycle Bin)", variable=self.re_recycle_var)
        self.re_recycle_check.grid(row=8, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # Re-encode Button
        self.re_btn_frame = ttk.Frame(self.tab2)
        self.re_btn_frame.grid(row=9, column=1, pady=10)

        self.re_encode_button = ttk.Button(self.re_btn_frame, text="Start Re-encode", command=self.start_reencode)
        self.re_encode_button.pack(side=tk.LEFT, padx=5)

        self.re_pause_button = ttk.Button(self.re_btn_frame, text="Pause", command=self.toggle_re_pause, state=tk.DISABLED)
        self.re_pause_button.pack(side=tk.LEFT, padx=5)

        self.re_stop_button = ttk.Button(self.re_btn_frame, text="Stop", command=self.stop_re, state=tk.DISABLED)
        self.re_stop_button.pack(side=tk.LEFT, padx=5)

        # Progress
        self.re_progress_bar = ttk.Progressbar(self.tab2, orient="horizontal", length=300, mode="determinate")
        self.re_progress_bar.grid(row=10, column=0, columnspan=3, padx=5, pady=5)
        self.re_status_label = ttk.Label(self.tab2, text="Status: Idle")
        self.re_status_label.grid(row=11, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)

        self.tab2.columnconfigure(1, weight=1)

    def process_download_queue(self):
        while True:
            job = self.download_queue.get()
            self.after(0, self.on_dl_start, job)
            # Run the download
            try:
                start_download(job)
            except Exception as e:
                pass # Error handling is inside start_download usually
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
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                percentage = (d['downloaded_bytes'] / total_bytes) * 100
                self.progress_bar['value'] = percentage
                self.status_label.config(text=f"Status: Downloading {percentage:.2f}%")
                self.update_idletasks()
        elif d['status'] == 'finished':
            self.progress_bar['value'] = 100
            self.status_label.config(text="Status: Download finished.")
            self.update_idletasks()
            # Don't show messagebox here, maybe confusing if queued. 
            # Or show it only if queue is empty? 
            # Original code showed it. Let's keep it but maybe make it less blocking?
            # messagebox.showinfo("Success", "Download completed successfully.") 
            # Better to show in status label for queued items.
        elif d['status'] == 'error':
            self.status_label.config(text=f"Status: Error")
            self.update_idletasks()
            messagebox.showerror("Error", d['info'])

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
            low_vram=self.dl_low_vram_var.get()
        )
        self.download_queue.put(job)
        self.status_label.config(text=f"Status: Queued {job.url}")

    def browse_reencode_input_path(self):
        current_mode = self.re_mode_var.get()
        if current_mode == "single":
            file_path = filedialog.askopenfilename(
                title="Select a video file",
                filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov *.flv *.webm"), ("All files", "*.*")])
        else: # batch mode
            file_path = filedialog.askdirectory(
                title="Select a directory containing video files")
        
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
        else: # batch mode
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
            self.re_progress_bar['value'] = percentage
        
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

        if not input_path or not output_dir:
            messagebox.showerror("Error", "Please fill in all required re-encoding fields.")
            return
        
        if re_mode == "single" and not output_filename:
            messagebox.showerror("Error", "Please provide an output filename for single file re-encoding.")
            return

        self.re_status_label.config(text="Status: Starting re-encoding...")
        self.re_progress_bar['value'] = 0
        self.re_encode_button.config(state=tk.DISABLED)
        self.re_pause_button.config(state=tk.NORMAL, text="Pause")
        self.re_stop_button.config(state=tk.NORMAL)

        self.re_controller = TaskController()

        # Run re-encoding in a separate thread to keep GUI responsive
        threading.Thread(target=self._run_reencode_task,
                         args=(input_path, output_dir, output_filename, video_codec, audio_codec, container_format, re_mode, file_types, self.re_low_vram_var.get(), self.re_recycle_var.get())).start()

    def _run_reencode_task(self, input_path, output_dir, output_filename, video_codec, audio_codec, container_format, re_mode, file_types, low_vram, recycle_original):
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
            recycle_original
        )
        self.after(0, self._complete_reencode_task, success, message)

    def _complete_reencode_task(self, success, message):
        self.re_encode_button.config(state=tk.NORMAL)
        self.re_pause_button.config(state=tk.DISABLED, text="Pause")
        self.re_stop_button.config(state=tk.DISABLED)
        self.re_controller = None

        if success:
            self.re_progress_bar['value'] = 100
            self.re_status_label.config(text="Status: Re-encoding finished.")
            messagebox.showinfo("Success", message)
        else:
            if "stopped by user" in message.lower():
                 self.re_progress_bar['value'] = 0
                 self.re_status_label.config(text="Status: Re-encoding stopped.")
            else:
                self.re_progress_bar['value'] = 0
                self.re_status_label.config(text="Status: Re-encoding failed.")
                messagebox.showerror("Error", message)

if __name__ == "__main__":
    app = App()
    app.mainloop()