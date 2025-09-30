from dataclasses import dataclass, field
from enum import Enum
import subprocess
import yt_dlp
import os
from typing import Callable

class DownloadStatus(Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class DownloadJob:
    url: str
    start_time: str
    end_time: str
    output_path: str
    output_filename: str
    status: DownloadStatus = DownloadStatus.QUEUED
    progress: int = 0
    progress_hook: Callable = None

def start_download(job: DownloadJob):
    job.status = DownloadStatus.DOWNLOADING
    if job.progress_hook:
        job.progress_hook({'status': 'downloading', 'info': 'Starting download...'})

    output_full_path = os.path.join(job.output_path, job.output_filename)
    
    # Handle existing files
    base, ext = os.path.splitext(output_full_path)
    i = 1
    while os.path.exists(output_full_path):
        output_full_path = f"{base}({i}){ext}"
        i += 1

    try:
        if job.start_time and job.end_time:
            try:
                # Try with ffmpeg first for direct clipping
                command = [
                    'ffmpeg',
                    '-i', job.url,
                    '-ss', job.start_time,
                    '-to', job.end_time,
                    '-c', 'copy',
                    output_full_path
                ]
                subprocess.run(command, check=True, capture_output=True)
                if job.progress_hook:
                    job.progress_hook({'status': 'finished', 'info': 'Download finished.'})
                job.status = DownloadStatus.COMPLETED
                return
            except FileNotFoundError:
                raise Exception("ffmpeg not found. Please install ffmpeg and add it to your PATH.")
            except subprocess.CalledProcessError as e:
                # If ffmpeg fails, fall back to yt-dlp
                pass

        # Use yt-dlp
        ydl_opts = {
            'outtmpl': output_full_path,
            'progress_hooks': [job.progress_hook] if job.progress_hook else [],
        }
        if job.start_time or job.end_time:
            postprocessor_args = []
            if job.start_time:
                postprocessor_args.extend(['-ss', job.start_time])
            if job.end_time:
                postprocessor_args.extend(['-to', job.end_time])
            ydl_opts['postprocessor_args'] = postprocessor_args
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([job.url])
        job.status = DownloadStatus.COMPLETED
        if job.progress_hook:
            job.progress_hook({'status': 'finished', 'info': 'Download finished.'})

    except yt_dlp.utils.DownloadError as e:
        job.status = DownloadStatus.FAILED
        if job.progress_hook:
            job.progress_hook({'status': 'error', 'info': str(e)})
    except Exception as e:
        job.status = DownloadStatus.FAILED
        if job.progress_hook:
            job.progress_hook({'status': 'error', 'info': str(e)})