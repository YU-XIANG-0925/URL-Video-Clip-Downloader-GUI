"""
Clipper 模組 - 影片裁切功能
支援快速裁切（stream copy）和精確裁切（重新編碼）
"""

import subprocess
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from task_utils import TaskController
from constants import COPY_CODEC_LABEL, PRECISE_CUT_LABEL


class ClipStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ClipJob:
    input_path: str
    start_time: str
    end_time: str
    output_path: str
    output_filename: str
    clip_mode: str = COPY_CODEC_LABEL  # COPY_CODEC_LABEL 或 PRECISE_CUT_LABEL
    container_format: str = "mp4"
    status: ClipStatus = ClipStatus.QUEUED
    progress: int = 0
    progress_hook: Callable = None
    task_controller: TaskController = None


def _run_stoppable_ffmpeg(command, task_controller: TaskController, progress_hook=None):
    """執行 ffmpeg 並支援停止/暫停功能"""
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

    for line in process.stdout:
        if task_controller:
            if task_controller.is_stopped():
                process.terminate()
                return False, "已被使用者停止"

            while task_controller.pause_event.is_set():
                if task_controller.is_stopped():
                    process.terminate()
                    return False, "已被使用者停止"
                time.sleep(0.1)

    process.wait()

    if task_controller and task_controller.is_stopped():
        return False, "已被使用者停止"

    if process.returncode == 0:
        return True, "成功"
    else:
        return False, f"處理失敗，錯誤碼: {process.returncode}"


def start_clip(job: ClipJob):
    """
    執行影片裁切
    - 快速模式 (COPY_CODEC_LABEL): 使用 stream copy，速度快但只能從 keyframe 裁切
    - 精確模式 (PRECISE_CUT_LABEL): 重新編碼，100% 精確裁切
    """
    job.status = ClipStatus.PROCESSING
    if job.progress_hook:
        job.progress_hook({"status": "processing", "info": "開始裁切..."})

    # 構建輸出檔名
    container_ext = job.container_format if job.container_format else "mp4"
    if not container_ext.startswith("."):
        container_ext = "." + container_ext

    if job.output_filename.lower().endswith(container_ext):
        final_filename = job.output_filename
    else:
        final_filename = job.output_filename + container_ext

    output_full_path = os.path.join(job.output_path, final_filename)

    # 處理檔名衝突
    base, ext = os.path.splitext(output_full_path)
    i = 1
    while os.path.exists(output_full_path):
        output_full_path = f"{base}({i}){ext}"
        i += 1

    try:
        if not os.path.exists(job.input_path):
            raise Exception(f"輸入檔案不存在: {job.input_path}")

        if job.clip_mode == PRECISE_CUT_LABEL:
            # === 精確裁切模式 ===
            # 使用 HEVC NVENC 重新編碼，QP 18 確保高品質
            if job.progress_hook:
                job.progress_hook(
                    {"status": "processing", "info": "精確裁切中（重新編碼）..."}
                )

            command = [
                "ffmpeg",
                "-ss",
                job.start_time,
                "-i",
                job.input_path,
                "-to",
                job.end_time,
                "-c:v",
                "hevc_nvenc",
                "-preset",
                "p5",
                "-qp",
                "18",  # 高品質設定（視覺無損）
                "-bf",
                "4",  # B-frame
                "-b_ref_mode",
                "middle",
                "-c:a",
                "aac",
                "-b:a",
                "192k",  # 高品質音訊
                "-avoid_negative_ts",
                "make_zero",
                "-y",
                output_full_path,
            ]
        else:
            # === 快速裁切模式 (Stream Copy) ===
            if job.progress_hook:
                job.progress_hook(
                    {"status": "processing", "info": "快速裁切中（stream copy）..."}
                )

            command = [
                "ffmpeg",
                "-ss",
                job.start_time,
                "-i",
                job.input_path,
                "-to",
                job.end_time,
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                "-y",
                output_full_path,
            ]

        success, msg = _run_stoppable_ffmpeg(
            command, job.task_controller, job.progress_hook
        )

        if not success:
            if "停止" in msg:
                job.status = ClipStatus.STOPPED
                if job.progress_hook:
                    job.progress_hook({"status": "error", "info": msg})
                # 清理未完成的輸出檔
                if os.path.exists(output_full_path):
                    try:
                        os.remove(output_full_path)
                    except:
                        pass
                return False, msg
            else:
                raise Exception(f"ffmpeg 錯誤: {msg}")

        job.status = ClipStatus.COMPLETED
        if job.progress_hook:
            job.progress_hook({"status": "finished", "info": "裁切完成！"})
        return True, f"裁切完成: {output_full_path}"

    except FileNotFoundError:
        error_msg = "找不到 ffmpeg，請確認已安裝並加入 PATH"
        job.status = ClipStatus.FAILED
        if job.progress_hook:
            job.progress_hook({"status": "error", "info": error_msg})
        return False, error_msg

    except Exception as e:
        error_msg = str(e)
        job.status = ClipStatus.FAILED
        if job.progress_hook:
            job.progress_hook({"status": "error", "info": error_msg})
        return False, error_msg
