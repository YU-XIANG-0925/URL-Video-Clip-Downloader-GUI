import subprocess
import os
import re
import tempfile

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

def _get_video_duration(file_path):
    """Gets the duration of a single video file using ffprobe."""
    command = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        file_path
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 0.0

def merge_videos(
    input_files: list,
    output_file: str,
    progress_callback=None
):
    """
    Merges a list of video files into a single file using ffmpeg concat demuxer.
    Assumes files have same codecs/formats (typical for split recordings).
    """
    if not input_files:
        return False, "No input files provided."

    # 1. Calculate total duration for progress estimation
    total_duration = 0.0
    for f in input_files:
        total_duration += _get_video_duration(f)

    # 2. Create the concat list file
    # format: file 'path/to/file'
    # Special characters in paths need escaping for ffmpeg concat file, 
    # but writing absolute paths with forward slashes usually works best on Windows/Cross-platform for ffmpeg.
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
            concat_list_path = tmp_file.name
            for file_path in input_files:
                # Ensure absolute path
                abs_path = os.path.abspath(file_path)
                # Escape single quotes for the concat file format
                safe_path = abs_path.replace("'", "'\\''")
                # Ensure forward slashes
                safe_path = safe_path.replace("\\", "/")
                tmp_file.write(f"file '{safe_path}'\n")
    except Exception as e:
        return False, f"Failed to create temporary concat list: {e}"

    # 3. Run ffmpeg command
    command = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy", # Stream copy (fast, no re-encode)
        "-y",
        "-progress", "pipe:1",
        "-nostats",
        output_file
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', errors='ignore')

    duration_pattern = re.compile(r"Duration:\s(\d{2}:\d{2}:\d{2}\.\d{2})")
    
    # If total_duration calc failed (e.g. ffprobe missing), try to get it from the first few lines of ffmpeg output (it might estimate it)
    
    full_log = []
    for line in process.stdout:
        line = line.strip()
        full_log.append(line)
        if not line:
            continue

        if total_duration == 0.0:
             match = duration_pattern.search(line)
             if match:
                 total_duration = _parse_time_str(match.group(1))

        if line.startswith("out_time="):
            time_str = line.split("=")[1]
            current_time = _parse_time_str(time_str)
            
            if total_duration > 0:
                percentage = min(100.0, (current_time / total_duration) * 100)
                if progress_callback:
                    progress_callback(percentage, f"Merging... {percentage:.1f}%")
            else:
                if progress_callback:
                    progress_callback(None, f"Merging... {time_str}")

    process.wait() 
    
    # Clean up temp file
    if os.path.exists(concat_list_path):
        try:
            os.remove(concat_list_path)
        except:
            pass

    if process.returncode == 0:
        return True, "Merge completed successfully."
    else:
        error_details = "\n".join(full_log[-10:]) # Last 10 lines
        return False, f"Merge failed with error code: {process.returncode}.\nOutput:\n{error_details}"
