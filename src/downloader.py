from dataclasses import dataclass, field
from enum import Enum
import subprocess
import yt_dlp
from yt_dlp.utils import sanitize_filename
import os
from typing import Callable
import datetime
import time

# Import TaskController from task_utils but handle circular import if necessary or use typing only
# Since task_utils is separate, it should be fine.
from task_utils import TaskController
from utils import get_low_vram_args
from constants import BEST_CODEC_LABEL, COPY_CODEC_LABEL


def log_error(error_message: str):
    """Appends a timestamped error message to the .error_log/errors.log file."""
    log_dir = ".error_log"
    log_file = os.path.join(log_dir, "errors.log")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # Ensure the log directory exists
        os.makedirs(log_dir, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {error_message}\n")
    except Exception as e:
        # If logging itself fails, print to stderr as a fallback
        print(f"Failed to write to log file: {e}")


class DownloadStatus(Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class DownloadJob:
    url: str
    start_time: str
    end_time: str
    output_path: str
    output_filename: str
    video_codec: str | None = None
    audio_codec: str | None = None
    container_format: str | None = None
    status: DownloadStatus = DownloadStatus.QUEUED
    progress: int = 0
    progress_hook: Callable = None
    task_controller: TaskController = None
    low_vram: bool = False
    quality: int = 30


def _run_stoppable_ffmpeg(
    command,
    task_controller: TaskController,
    progress_hook=None,
    info_prefix="Processing",
):
    """Helper to run ffmpeg with stop/pause support via TaskController."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding="utf-8",
        errors="ignore",
    )

    if task_controller:
        task_controller.set_process(process)

    # We can parse output to check for errors, but for 'copy' operations progress info is limited.
    # Still, we need to loop to allow checking for stop/pause events.
    for line in process.stdout:
        if task_controller:
            # Check Stop
            if task_controller.is_stopped():
                process.terminate()
                return False, "Stopped by user"

            # Check Pause (Wait loop)
            while task_controller.pause_event.is_set():
                if task_controller.is_stopped():
                    process.terminate()
                    return False, "Stopped by user"
                time.sleep(0.1)

        # Optional: Parse progress if needed, but for simple clipping usually unnecessary
        # to show percentage unless we calculate duration.
        pass

    process.wait()

    if task_controller and task_controller.is_stopped():
        return False, "Stopped by user"

    if process.returncode == 0:
        return True, "Success"
    else:
        return False, f"Process failed with code {process.returncode}"


def start_download(job: DownloadJob):
    job.status = DownloadStatus.DOWNLOADING
    if job.progress_hook:
        job.progress_hook({"status": "downloading", "info": "Starting process..."})

    job.output_filename = sanitize_filename(job.output_filename)

    # Construct filename with correct extension based on container format
    container_ext = job.container_format if job.container_format else "mp4"
    if not container_ext.startswith("."):
        container_ext = "." + container_ext

    if job.output_filename.lower().endswith(container_ext):
        final_filename = job.output_filename
    else:
        final_filename = job.output_filename + container_ext

    output_full_path = os.path.join(job.output_path, final_filename)

    # Handle existing files
    base, ext = os.path.splitext(output_full_path)
    i = 1
    while os.path.exists(output_full_path):
        output_full_path = f"{base}({i}){ext}"
        i += 1

    try:
        # Check if the URL is a local file path
        is_local_file = os.path.exists(job.url)

        if is_local_file:
            # --- LOGIC FOR LOCAL FILES ---
            if not (job.start_time and job.end_time):
                raise Exception(
                    "For local files, both start and end time are required for clipping."
                )

            job.status = DownloadStatus.PROCESSING
            if job.progress_hook:
                job.progress_hook(
                    {"status": "processing", "info": "Clipping local file..."}
                )

            try:
                # Use ffmpeg to clip the local file
                # 使用 input seeking (-ss 在 -i 之前) 以獲得精確的裁切點並避免音影不同步
                command = [
                    "ffmpeg",
                    "-ss",
                    job.start_time,  # Input seeking: 放在 -i 之前
                    "-i",
                    job.url,
                    "-to",
                    job.end_time,
                    "-avoid_negative_ts",
                    "make_zero",  # 修正時間戳偏移問題
                ]

                if job.video_codec == BEST_CODEC_LABEL:
                    cq_value = str(job.quality) if job.quality is not None else "30"
                    command.extend(
                        [
                            "-c:v",
                            "hevc_nvenc",
                            "-preset",
                            "p7",
                            "-cq",
                            cq_value,
                            "-c:a",
                            "copy",
                        ]
                    )
                    if job.low_vram:
                        command.extend(get_low_vram_args("hevc_nvenc"))
                elif job.video_codec == COPY_CODEC_LABEL:
                    command.extend(["-c", "copy"])
                else:
                    command.extend(["-c", "copy"])  # Default to copy for local clips

                command.extend(["-y", output_full_path])

                success, msg = _run_stoppable_ffmpeg(command, job.task_controller)

                if not success:
                    if "Stopped" in msg:
                        job.status = DownloadStatus.STOPPED
                        if job.progress_hook:
                            job.progress_hook(
                                {"status": "error", "info": "Stopped by user"}
                            )
                        # Cleanup
                        if os.path.exists(output_full_path):
                            try:
                                os.remove(output_full_path)
                            except:
                                pass
                        return
                    else:
                        raise Exception(f"ffmpeg error: {msg}")

                job.status = DownloadStatus.COMPLETED
                if job.progress_hook:
                    job.progress_hook(
                        {"status": "finished", "info": "Clipping finished."}
                    )
                return

            except FileNotFoundError:
                raise Exception(
                    "ffmpeg not found. Please install ffmpeg and add it to your PATH."
                )
            except Exception as e:
                raise Exception(f"ffmpeg error during clipping: {e}")

        else:
            # --- LOGIC FOR URLS (Original Logic) ---
            if job.start_time and job.end_time:
                try:
                    # Try with ffmpeg first for direct stream clipping
                    # 使用 input seeking (-ss 在 -i 之前) 以獲得精確的裁切點並避免音影不同步
                    command = [
                        "ffmpeg",
                        "-ss",
                        job.start_time,  # Input seeking: 放在 -i 之前
                        "-i",
                        job.url,
                        "-to",
                        job.end_time,
                        "-c",
                        "copy",
                        "-avoid_negative_ts",
                        "make_zero",  # 修正時間戳偏移問題
                        "-y",
                        output_full_path,
                    ]

                    success, msg = _run_stoppable_ffmpeg(command, job.task_controller)

                    if success:
                        if job.progress_hook:
                            job.progress_hook(
                                {"status": "finished", "info": "Download finished."}
                            )
                        job.status = DownloadStatus.COMPLETED
                        return
                    elif "Stopped" in msg:
                        job.status = DownloadStatus.STOPPED
                        if job.progress_hook:
                            job.progress_hook(
                                {"status": "error", "info": "Stopped by user"}
                            )
                        if os.path.exists(output_full_path):
                            try:
                                os.remove(output_full_path)
                            except:
                                pass
                        return
                    else:
                        # Fallback to yt-dlp if ffmpeg failed (likely due to URL type)
                        pass
                except Exception:
                    pass

            # Use yt-dlp for downloading and/or clipping

            # Hook wrapper to inject stop/pause logic into yt-dlp
            def wrapped_hook(d):
                if job.task_controller:
                    if job.task_controller.is_stopped():
                        raise Exception("Stopped by user")

                    # Pause logic: loop sleep
                    while job.task_controller.pause_event.is_set():
                        if job.task_controller.is_stopped():
                            raise Exception("Stopped by user")
                        time.sleep(0.5)

                if job.progress_hook:
                    job.progress_hook(d)

            ydl_opts = {
                "outtmpl": output_full_path,
                "progress_hooks": [wrapped_hook],
            }

            postprocessor_args = []
            if job.start_time:
                postprocessor_args.extend(["-ss", job.start_time])
            if job.end_time:
                postprocessor_args.extend(["-to", job.end_time])

            # Add codec options if they are not 'copy'
            if job.video_codec == BEST_CODEC_LABEL:
                cq_value = str(job.quality) if job.quality is not None else "30"
                postprocessor_args.extend(
                    [
                        "-c:v",
                        "hevc_nvenc",
                        "-preset",
                        "p7",
                        "-cq",
                        cq_value,
                        "-c:a",
                        "copy",
                    ]
                )
                if job.low_vram:
                    postprocessor_args.extend(get_low_vram_args("hevc_nvenc"))
            elif job.video_codec == COPY_CODEC_LABEL:
                postprocessor_args.extend(["-c:v", "copy", "-c:a", "copy"])
            elif job.video_codec and job.video_codec != "copy":
                postprocessor_args.extend(["-c:v", job.video_codec])
                if job.low_vram:
                    postprocessor_args.extend(get_low_vram_args(job.video_codec))

            elif job.video_codec == "copy":
                postprocessor_args.extend(["-c:v", "copy"])

            if (
                job.video_codec != BEST_CODEC_LABEL
            ):  # Only handle audio separately if not using "Best" preset which enforces audio copy
                if job.audio_codec and job.audio_codec != "copy":
                    postprocessor_args.extend(["-c:a", job.audio_codec])
                elif job.audio_codec == "copy":
                    postprocessor_args.extend(["-c:a", "copy"])

            if postprocessor_args:
                ydl_opts["postprocessors"] = [
                    {
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": job.container_format or "mp4",
                    }
                ]
                ydl_opts["postprocessor_args"] = postprocessor_args

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([job.url])
            job.status = DownloadStatus.COMPLETED
            if job.progress_hook:
                job.progress_hook({"status": "finished", "info": "Download finished."})

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Stopped by user" in error_msg:
            job.status = DownloadStatus.STOPPED
            if job.progress_hook:
                job.progress_hook({"status": "error", "info": "Stopped by user"})
        else:
            log_error(error_msg)
            job.status = DownloadStatus.FAILED
            if job.progress_hook:
                job.progress_hook({"status": "error", "info": error_msg})
    except Exception as e:
        error_msg = str(e)
        if "Stopped by user" in error_msg:
            job.status = DownloadStatus.STOPPED
            if job.progress_hook:
                job.progress_hook({"status": "error", "info": "Stopped by user"})
        else:
            log_error(error_msg)
            job.status = DownloadStatus.FAILED
            if job.progress_hook:
                job.progress_hook({"status": "error", "info": error_msg})
