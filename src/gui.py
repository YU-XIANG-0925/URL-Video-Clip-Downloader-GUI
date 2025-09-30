import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
from downloader import DownloadJob, start_download

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("URL Video Clip Downloader")
        self.geometry("500x300")

        # URL
        self.url_label = ttk.Label(self, text="URL:")
        self.url_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.url_entry = ttk.Entry(self, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # Start Time
        self.start_time_label = ttk.Label(self, text="Start Time (HH:MM:SS):")
        self.start_time_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.start_time_entry = ttk.Entry(self)
        self.start_time_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        # End Time
        self.end_time_label = ttk.Label(self, text="End Time (HH:MM:SS):")
        self.end_time_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.end_time_entry = ttk.Entry(self)
        self.end_time_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)

        # Output Path
        self.output_path_label = ttk.Label(self, text="Output Path:")
        self.output_path_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.output_path_entry = ttk.Entry(self)
        self.output_path_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        self.browse_button = ttk.Button(self, text="Browse", command=self.browse_output_path)
        self.browse_button.grid(row=3, column=2, padx=5, pady=5)

        # Output Filename
        self.output_filename_label = ttk.Label(self, text="Output Filename:")
        self.output_filename_label.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.output_filename_entry = ttk.Entry(self)
        self.output_filename_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)

        # Download Button
        self.download_button = ttk.Button(self, text="Start Download", command=self.start_download)
        self.download_button.grid(row=5, column=1, pady=10)

        # Progress
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=6, column=0, columnspan=3, padx=5, pady=5)
        self.status_label = ttk.Label(self, text="Status: Idle")
        self.status_label.grid(row=7, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)

        self.columnconfigure(1, weight=1)

        self.download_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.worker_thread.start()

    def process_queue(self):
        while True:
            job = self.download_queue.get()
            start_download(job)
            self.download_queue.task_done()

    def browse_output_path(self):
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
            messagebox.showinfo("Success", "Download completed successfully.")
        elif d['status'] == 'error':
            self.status_label.config(text=f"Status: Error")
            self.update_idletasks()
            messagebox.showerror("Error", d['info'])

    def start_download(self):
        job = DownloadJob(
            url=self.url_entry.get(),
            start_time=self.start_time_entry.get(),
            end_time=self.end_time_entry.get(),
            output_path=self.output_path_entry.get(),
            output_filename=self.output_filename_entry.get(),
            progress_hook=self.progress_hook
        )
        self.download_queue.put(job)
        self.status_label.config(text=f"Status: Queued {job.url}")

if __name__ == "__main__":
    app = App()
    app.mainloop()