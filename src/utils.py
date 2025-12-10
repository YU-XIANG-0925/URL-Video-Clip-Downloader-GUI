import os
import subprocess
import json
import math
from send2trash import send2trash

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

def get_media_info(file_path):
    if not os.path.exists(file_path):
        return None, "File not found."

    try:
        # Get file size
        file_size = os.path.getsize(file_path)
        formatted_size = format_size(file_size)

        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        
        # Use subprocess to call ffprobe
        # Creationflags for Windows to avoid popping up a window if not strictly necessary, 
        # though standard run usually doesn't if captured.
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            return None, "Failed to probe file. Ensure ffprobe is installed."

        data = json.loads(result.stdout)
        
        info = {
            "filename": os.path.basename(file_path),
            "size": formatted_size,
            "duration": data.get("format", {}).get("duration", "N/A"),
            "bitrate": f"{int(data.get('format', {}).get('bit_rate', 0)) // 1000} kb/s",
            "streams": []
        }

        for stream in data.get("streams", []):
            s_info = {
                "index": stream.get("index"),
                "codec_type": stream.get("codec_type"),
                "codec_name": stream.get("codec_name"),
                "profile": stream.get("profile", "N/A"),
            }
            
            if stream.get("codec_type") == "video":
                s_info["resolution"] = f"{stream.get('width')}x{stream.get('height')}"
                fps = stream.get("r_frame_rate", "N/A")
                # Try to simplify FPS fraction
                try:
                    if '/' in fps:
                        num, den = map(int, fps.split('/'))
                        if den > 0:
                            fps = f"{num/den:.2f}"
                except:
                    pass
                s_info["fps"] = fps
                
            elif stream.get("codec_type") == "audio":
                s_info["channels"] = stream.get("channels", "N/A")
                s_info["sample_rate"] = f"{stream.get('sample_rate')} Hz"

            info["streams"].append(s_info)

        return info, None

    except Exception as e:
        return None, str(e)

def get_low_vram_args(codec: str) -> list[str]:
    """Returns ffmpeg arguments to minimize VRAM usage for hardware encoders."""
    if not codec:
        return []
    
    args = []
    if codec == 'hevc_nvenc' or codec == 'h264_nvenc':
        # NVIDIA: P1 (fastest), no lookahead, limit surfaces
        args.extend(['-preset', 'p1', '-rc-lookahead', '0', '-surfaces', '0', '-delay', '0'])
    elif codec == 'hevc_amf' or codec == 'h264_amf':
        # AMD: Speed preset
        args.extend(['-quality', 'speed', '-rc', 'cbr'])
    elif codec == 'hevc_qsv' or codec == 'h264_qsv':
        # Intel: Veryfast preset
        args.extend(['-preset', 'veryfast'])
    return args

def recycle_file(file_path: str) -> bool:
    """
    Moves a file to the recycle bin.
    Returns True if successful, False otherwise.
    """
    try:
        if os.path.exists(file_path):
            # Ensure path is absolute and normalized for Windows
            abs_path = os.path.abspath(file_path)
            send2trash(abs_path)
            return True
        else:
            print(f"Recycle Error: File not found: {file_path}")
    except Exception as e:
        print(f"Recycle Error for {file_path}: {e}")
    return False

def parse_time_str(time_str):
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
