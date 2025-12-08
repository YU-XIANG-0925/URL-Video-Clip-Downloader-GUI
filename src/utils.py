import os
from send2trash import send2trash

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
