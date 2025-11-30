import subprocess
import os
import threading
import re

def _parse_time_str(time_str):
    """Parses HH:MM:SS.ms string to seconds."""
    if not time_str:
        return 0.0
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        pass
    return 0.0

def _run_ffmpeg_command(
    input_file: str,
    output_file: str,
    video_codec: str,
    audio_codec: str,
    progress_callback=None
):
    command = [
        "ffmpeg",
        "-i", input_file,
        "-c:v", video_codec,
        "-c:a", audio_codec,
        "-y", # Overwrite output files without asking
        "-progress", "pipe:1", # Output progress information to stdout
        "-nostats", # Suppress standard progress bar to avoid parsing issues
        output_file
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', errors='ignore')

    total_duration = 0.0
    duration_pattern = re.compile(r"Duration:\s(\d{2}:\d{2}:\d{2}\.\d{2})")
    
    for line in process.stdout:
        line = line.strip()
        if not line:
            continue

        # Try to extract duration from stderr (which is merged into stdout)
        if total_duration == 0.0:
            match = duration_pattern.search(line)
            if match:
                total_duration = _parse_time_str(match.group(1))

        # Extract current time from -progress output
        if line.startswith("out_time="):
            time_str = line.split("=")[1]
            current_time = _parse_time_str(time_str)
            
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

    process.wait()

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
    progress_callback=None
):
    if mode == "single":
        if not output_filename:
            return False, "Output filename is required for single file re-encoding."
        
        full_output_file = os.path.join(output_path, f"{output_filename}.{container_format}")
        success, error_msg = _run_ffmpeg_command(
            input_path, full_output_file, video_codec, audio_codec, progress_callback
        )
        if success:
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

        for root, _, files in os.walk(input_path):
            for file in files:
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
                        input_file, full_output_file, video_codec, audio_codec, progress_callback
                    )
                    if success:
                        reencoded_count += 1
                    else:
                        failed_files.append(f"{relative_path} ({error_msg})")
        
        if not failed_files:
            return True, f"Batch re-encoding completed. {reencoded_count} files re-encoded successfully."
        else:
            return False, f"Batch re-encoding finished with {reencoded_count} successes and {len(failed_files)} failures: {'; '.join(failed_files)}"

    return False, "Invalid re-encoding mode specified."