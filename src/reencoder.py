import subprocess
import os
import threading
import re
from send2trash import send2trash

from constants import BEST_CODEC_LABEL
from task_utils import TaskController
from utils import get_low_vram_args, parse_time_str, recycle_file

def _run_ffmpeg_command(
    input_file: str,
    output_file: str,
    video_codec: str,
    audio_codec: str,
    progress_callback=None,
    task_controller: TaskController = None,
    low_vram: bool = False
):
    command = [
        "ffmpeg",
        "-i", input_file
    ]

    if video_codec == BEST_CODEC_LABEL:
        # Best settings: HEVC NVENC, Preset P7 (Best Quality), CQ 24, Audio Copy
        command.extend(["-c:v", "hevc_nvenc", "-preset", "p7", "-cq", "24", "-c:a", "copy"])
    else:
        command.extend(["-c:v", video_codec, "-c:a", audio_codec])

    command.extend([
        "-y", # Overwrite output files without asking
        "-progress", "pipe:1", # Output progress information to stdout
        "-nostats" # Suppress standard progress bar to avoid parsing issues
    ])
    
    if low_vram and video_codec != BEST_CODEC_LABEL: # logic handles specific codecs, skip for custom preset if not needed or integrated
         # Note: get_low_vram_args likely checks for 'hevc_nvenc'. 
         # Since we are using hevc_nvenc in Best mode, we might still want low vram args if user checked it?
         # The user instruction didn't specify low vram behavior for "Best", but generally P7 uses max resources.
         # If low_vram is true, we might want to avoid P7 or add the delay args.
         # get_low_vram_args(codec) usually returns ['-delay', '20'] etc.
         # If video_codec is BEST, we are using hevc_nvenc.
         command.extend(get_low_vram_args("hevc_nvenc"))
    elif low_vram:
        command.extend(get_low_vram_args(video_codec))
        
    command.append(output_file)

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', errors='ignore')

    if task_controller:
        task_controller.set_process(process)

    total_duration = 0.0
    duration_pattern = re.compile(r"Duration:\s(\d{2}:\d{2}:\d{2}\.\d{2})")
    
    try:
        for line in process.stdout:
            if task_controller and task_controller.is_stopped():
                break

            line = line.strip()
            if not line:
                continue

            # Try to extract duration from stderr (which is merged into stdout)
            if total_duration == 0.0:
                match = duration_pattern.search(line)
                if match:
                    total_duration = parse_time_str(match.group(1))

            # Extract current time from -progress output
            if line.startswith("out_time="):
                time_str = line.split("=")[1]
                current_time = parse_time_str(time_str)
                
                if total_duration > 0:
                    percentage = min(100.0, (current_time / total_duration) * 100)
                    if progress_callback:
                        progress_callback(percentage, f"Re-encoding... {percentage:.1f}%")
                else:
                    # If duration couldn't be parsed, just show the raw time
                    if progress_callback:
                        progress_callback(None, f"Re-encoding... {time_str}")
            elif progress_callback and not line.startswith(("frame=", "fps=", "stream_", "bitrate=", "total_size=", "out_time_us=", "out_time_ms=", "dup_frames=", "drop_frames=", "speed=", "progress=")):
                 # Forward other interesting lines (errors, metadata info) but filter out raw progress keys to reduce noise if needed
                 # For now, we'll be selective to avoid flooding the GUI status
                 pass
    except Exception:
        pass

    process.wait()

    if task_controller and task_controller.is_stopped():
         # Cleanup partial output file if stopped
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except:
                pass
        return False, "Re-encoding stopped by user."

    if process.returncode == 0:
        return True, ""
    else:
        # Since we consumed stdout, we don't have the error message easily available unless we captured it.
        # But 'line' variable might hold the last line which could be an error.
        return False, f"FFmpeg failed with error code: {process.returncode}."

def reencode_video(
    input_path: str,
    output_path: str,
    output_filename: str,
    video_codec: str,
    audio_codec: str,
    container_format: str,
    mode: str,
    file_types: str,
    progress_callback=None,
    task_controller: TaskController = None,
    low_vram: bool = False,
    recycle_original: bool = False
):
    if mode == "single":
        if not output_filename:
            return False, "Output filename is required for single file re-encoding."
        
        full_output_file = os.path.join(output_path, f"{output_filename}.{container_format}")
        success, error_msg = _run_ffmpeg_command(
            input_path, full_output_file, video_codec, audio_codec, progress_callback, task_controller, low_vram
        )
        if success:
            if recycle_original:
                if recycle_file(input_path):
                    return True, "Re-encoding completed successfully. Original file moved to Recycle Bin."
                else:
                    return True, "Re-encoding successful, but failed to recycle original."
            return True, "Re-encoding completed successfully."
        else:
            return False, f"Single file re-encoding failed: {error_msg}"

    elif mode == "batch":
        if not os.path.isdir(input_path):
            return False, "Input path must be a directory for batch re-encoding."

        allowed_extensions = [f".{ext.strip().lower()}" for ext in file_types.split(',') if ext.strip()]
        if not allowed_extensions:
            # Default to common video formats if none specified
            allowed_extensions = [".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm"]

        reencoded_count = 0
        failed_files = []
        recycled_count = 0

        for root, _, files in os.walk(input_path):
            if task_controller and task_controller.is_stopped():
                break

            for file in files:
                if task_controller and task_controller.is_stopped():
                    break
                
                file_extension = os.path.splitext(file)[1].lower()
                if file_extension in allowed_extensions:
                    input_file = os.path.join(root, file)
                    relative_path = os.path.relpath(input_file, input_path)
                    
                    # Create corresponding output directory structure
                    output_subdir = os.path.join(output_path, os.path.dirname(relative_path))
                    os.makedirs(output_subdir, exist_ok=True)

                    base_filename = os.path.splitext(file)[0]
                    full_output_file = os.path.join(output_subdir, f"{base_filename}.{container_format}")

                    if progress_callback:
                        progress_callback(0, f"Processing file: {relative_path}")

                    success, error_msg = _run_ffmpeg_command(
                        input_file, full_output_file, video_codec, audio_codec, progress_callback, task_controller, low_vram
                    )
                    if success:
                        reencoded_count += 1
                        if recycle_original:
                            if recycle_file(input_file):
                                recycled_count += 1
                    else:
                        failed_files.append(f"{relative_path} ({error_msg})")
        
        if task_controller and task_controller.is_stopped():
             return False, "Batch re-encoding stopped by user."

        result_msg = f"Batch re-encoding completed. {reencoded_count} files re-encoded successfully."
        if recycle_original:
            result_msg += f" {recycled_count} original files moved to Recycle Bin."
            
        if not failed_files:
            return True, result_msg
        else:
            return False, f"{result_msg} {len(failed_files)} failures: {'; '.join(failed_files)}"

    return False, "Invalid re-encoding mode specified."