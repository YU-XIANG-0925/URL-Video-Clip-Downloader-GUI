import subprocess
import os
import threading
import re
from send2trash import send2trash

from constants import BEST_CODEC_LABEL, COPY_CODEC_LABEL, STREAMING_CODEC_LABEL
from task_utils import TaskController
from utils import (
    get_low_vram_args,
    parse_time_str,
    recycle_file,
    get_media_info,
    format_size,
)


def _run_ffmpeg_command(
    input_file: str,
    output_file: str,
    video_codec: str,
    audio_codec: str,
    progress_callback=None,
    task_controller: TaskController = None,
    low_vram: bool = False,
    quality: int = 26,
):
    command = ["ffmpeg", "-i", input_file]

    if video_codec == BEST_CODEC_LABEL:
        # Best settings: HEVC NVENC, Preset P7 (Best Quality), CQ {quality}, Audio Copy
        # Adjusted CQ based on user input or default 30
        cq_value = str(quality) if quality is not None else "26"
        command.extend(
            ["-c:v", "hevc_nvenc", "-preset", "p7", "-cq", cq_value, "-c:a", "copy"]
        )
    elif video_codec == STREAMING_CODEC_LABEL:
        # 串流優化設定: HEVC NVENC, Preset P5, Constant QP 模式
        # 啟用 B-frame + Lookahead + AQ 以達到最佳壓縮效率與速度平衡
        qp_value = str(quality) if quality is not None else "30"
        command.extend(
            [
                "-c:v",
                "hevc_nvenc",
                "-preset",
                "p5",  # 速度/品質平衡點
                "-tune",
                "hq",
                "-rc",
                "constqp",  # 恆定品質模式
                "-qp",
                qp_value,  # QP 值（預設 30，適合 1080p）
                "-b:v",
                "0",  # 不限制碼率
                "-bf",
                "4",  # 啟用 4 個 B-frame（提升壓縮 10-15%）
                "-b_ref_mode",
                "middle",  # B-frame 參考模式
                "-spatial-aq",
                "1",  # 空間自適應量化（改善畫質）
                "-temporal-aq",
                "1",  # 時間自適應量化（改善動態場景）
                "-rc-lookahead",
                "32",  # 前瞻分析 32 幀（更好的碼率分配）
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
            ]
        )
    elif video_codec == COPY_CODEC_LABEL:
        command.extend(["-c:v", "copy", "-c:a", "copy"])
    else:
        command.extend(["-c:v", video_codec, "-c:a", audio_codec])

    command.extend(
        [
            "-y",  # Overwrite output files without asking
            "-progress",
            "pipe:1",  # Output progress information to stdout
            "-nostats",  # Suppress standard progress bar to avoid parsing issues
        ]
    )

    if (
        low_vram and video_codec != BEST_CODEC_LABEL
    ):  # logic handles specific codecs, skip for custom preset if not needed or integrated
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
                        progress_callback(
                            percentage, f"Re-encoding... {percentage:.1f}%"
                        )
                else:
                    # If duration couldn't be parsed, just show the raw time
                    if progress_callback:
                        progress_callback(None, f"Re-encoding... {time_str}")
            elif progress_callback and not line.startswith(
                (
                    "frame=",
                    "fps=",
                    "stream_",
                    "bitrate=",
                    "total_size=",
                    "out_time_us=",
                    "out_time_ms=",
                    "dup_frames=",
                    "drop_frames=",
                    "speed=",
                    "progress=",
                )
            ):
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
    recycle_original: bool = False,
    quality: int = 26,
):
    if mode == "single":
        if not output_filename:
            return False, "Output filename is required for single file re-encoding."

        full_output_file = os.path.join(
            output_path, f"{output_filename}.{container_format}"
        )

        # Capture Info Before (Pre-flight)
        orig_info, _ = get_media_info(input_path)

        success, error_msg = _run_ffmpeg_command(
            input_path,
            full_output_file,
            video_codec,
            audio_codec,
            progress_callback,
            task_controller,
            low_vram,
            quality,
        )
        if success:
            # Capture Info After (Post-flight)
            new_info, _ = get_media_info(full_output_file)

            # Construct Comparison Message
            comparison_msg = ""
            if orig_info and new_info:
                try:
                    # Helper to extract first video codec
                    def get_v_codec(info):
                        for s in info["streams"]:
                            if s["codec_type"] == "video":
                                return s["codec_name"]
                        return "unknown"

                    orig_size_str = orig_info["size"]
                    new_size_str = new_info["size"]
                    orig_codec = get_v_codec(orig_info)
                    new_codec = get_v_codec(new_info)
                    orig_bitrate = orig_info["bitrate"]
                    new_bitrate = new_info["bitrate"]

                    # Calculate raw size difference for percentage (parse back or just file size)
                    orig_bytes = (
                        os.path.getsize(input_path) if os.path.exists(input_path) else 0
                    )  # Careful if recycled
                    # Wait, if recycled, input_path is gone. We need to grab size BEFORE recycling.
                    # We can use os.path.getsize on input_path right now if it's not recycled yet.
                    # Logic below handles recycling AFTER this block? No, look at original code.

                    # Correction: We must do this comparison block BEFORE recycling.
                    new_bytes = os.path.getsize(full_output_file)

                    # If we recycle, we can't get orig_bytes via os.path.getsize(input_path) afterwards.
                    # But we called get_media_info earlier which got formatted size.
                    # Let's trust we have the file currently if we haven't recycled yet.

                    if os.path.exists(input_path):
                        orig_bytes = os.path.getsize(input_path)
                    else:
                        orig_bytes = 0  # Should not happen if flow is correct

                    diff_bytes = orig_bytes - new_bytes
                    percent = (diff_bytes / orig_bytes * 100) if orig_bytes > 0 else 0

                    saved_str = format_size(diff_bytes)
                    sign = (
                        "-" if diff_bytes > 0 else "+"
                    )  # - means saved (less size), but for "Space Saved" positive is good.
                    # Let's say: "Compression: -70% (Saved 70MB)" or "+10% (Larger)"

                    comp_text = f"壓縮率: {percent:.1f}%"
                    if diff_bytes > 0:
                        comp_text += f" (節省 {saved_str})"
                    else:
                        comp_text += f" (增加 {format_size(abs(diff_bytes))})"

                    comparison_msg = (
                        f"\n\n[前後對比]\n"
                        f"原始: {orig_size_str} ({orig_codec}, {orig_bitrate})\n"
                        f"輸出: {new_size_str} ({new_codec}, {new_bitrate})\n"
                        f"{comp_text}"
                    )
                except Exception as e:
                    comparison_msg = f"\n(無法產生對比報告: {e})"

            if recycle_original:
                if recycle_file(input_path):
                    return (
                        True,
                        f"Re-encoding completed successfully. Original file moved to Recycle Bin.{comparison_msg}",
                    )
                else:
                    return (
                        True,
                        f"Re-encoding successful, but failed to recycle original.{comparison_msg}",
                    )
            return True, f"Re-encoding completed successfully.{comparison_msg}"
        else:
            return False, f"Single file re-encoding failed: {error_msg}"

    elif mode == "batch":
        if not os.path.isdir(input_path):
            return False, "Input path must be a directory for batch re-encoding."

        allowed_extensions = [
            f".{ext.strip().lower()}" for ext in file_types.split(",") if ext.strip()
        ]
        if not allowed_extensions:
            # Default to common video formats if none specified
            allowed_extensions = [".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm"]

        reencoded_count = 0
        failed_files = []
        recycled_count = 0

        total_orig_bytes = 0
        total_new_bytes = 0

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
                    output_subdir = os.path.join(
                        output_path, os.path.dirname(relative_path)
                    )
                    os.makedirs(output_subdir, exist_ok=True)

                    base_filename = os.path.splitext(file)[0]
                    full_output_file = os.path.join(
                        output_subdir, f"{base_filename}.{container_format}"
                    )

                    if progress_callback:
                        progress_callback(0, f"Processing file: {relative_path}")

                    # Capture size before processing
                    current_orig_size = 0
                    if os.path.exists(input_file):
                        current_orig_size = os.path.getsize(input_file)

                    success, error_msg = _run_ffmpeg_command(
                        input_file,
                        full_output_file,
                        video_codec,
                        audio_codec,
                        progress_callback,
                        task_controller,
                        low_vram,
                        quality,
                    )
                    if success:
                        reencoded_count += 1

                        # Accumulate stats
                        total_orig_bytes += current_orig_size
                        if os.path.exists(full_output_file):
                            total_new_bytes += os.path.getsize(full_output_file)

                        if recycle_original:
                            if recycle_file(input_file):
                                recycled_count += 1
                    else:
                        failed_files.append(f"{relative_path} ({error_msg})")

        if task_controller and task_controller.is_stopped():
            return False, "Batch re-encoding stopped by user."

        # Batch Summary Stats
        stats_msg = ""
        if total_orig_bytes > 0:
            diff_bytes = total_orig_bytes - total_new_bytes
            percent = diff_bytes / total_orig_bytes * 100
            saved_str = format_size(diff_bytes)

            stats_msg = (
                f"\n\n[批次統計]\n"
                f"總原始大小: {format_size(total_orig_bytes)}\n"
                f"總輸出大小: {format_size(total_new_bytes)}\n"
                f"空間節省: {format_size(diff_bytes)} ({percent:.1f}%)"
            )

        result_msg = f"Batch re-encoding completed. {reencoded_count} files re-encoded successfully.{stats_msg}"
        if recycle_original:
            result_msg += f"\n{recycled_count} original files moved to Recycle Bin."

        if not failed_files:
            return True, result_msg
        else:
            return (
                False,
                f"{result_msg}\n{len(failed_files)} failures: {'; '.join(failed_files)}",
            )

    return False, "Invalid re-encoding mode specified."
