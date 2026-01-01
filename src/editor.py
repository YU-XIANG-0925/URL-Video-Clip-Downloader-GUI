"""
Editor 模組 - 進階影片編輯功能
支援影片預覽、時間軸、關鍵幀裁切系統
"""

import cv2
import subprocess
import os
import json
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable
from PIL import Image, ImageTk

# 預設輸出比例選項
ASPECT_RATIOS = {
    "自由": None,
    "1:1 (正方形)": (1, 1),
    "4:3 (傳統)": (4, 3),
    "16:9 (寬螢幕)": (16, 9),
    "9:16 (直式)": (9, 16),
    "21:9 (超寬)": (21, 9),
}

# 預覽視窗大小
PREVIEW_SIZE = (960, 540)


@dataclass
class CropRegion:
    """裁切區域資料結構"""

    x: int  # 左上角 X
    y: int  # 左上角 Y
    width: int  # 寬度
    height: int  # 高度


@dataclass
class Keyframe:
    """關鍵幀資料結構"""

    time_ms: int  # 時間（毫秒）
    crop: CropRegion  # 裁切區域


@dataclass
class EditorProject:
    """編輯專案資料"""

    video_path: str
    video_width: int = 0
    video_height: int = 0
    video_fps: float = 30.0
    video_duration_ms: int = 0
    keyframes: List[Keyframe] = field(default_factory=list)
    output_width: int = 600
    output_height: int = 400
    aspect_ratio: Optional[Tuple[int, int]] = None


class VideoFrameReader:
    """影片幀讀取器"""

    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = None
        self.width = 0
        self.height = 0
        self.fps = 30.0
        self.total_frames = 0
        self.duration_ms = 0
        self._open()

    def _open(self):
        """開啟影片"""
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise Exception(f"無法開啟影片: {self.video_path}")

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_ms = (
            int((self.total_frames / self.fps) * 1000) if self.fps > 0 else 0
        )

    def get_frame_at_ms(self, time_ms: int) -> Optional[Image.Image]:
        """取得指定時間的幀（PIL Image）"""
        if not self.cap:
            return None

        self.cap.set(cv2.CAP_PROP_POS_MSEC, time_ms)
        ret, frame = self.cap.read()

        if not ret:
            return None

        # BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)

    def get_frame_for_preview(
        self, time_ms: int, preview_size: Tuple[int, int] = PREVIEW_SIZE
    ) -> Optional[Image.Image]:
        """取得縮放後的預覽幀"""
        frame = self.get_frame_at_ms(time_ms)
        if frame:
            # 保持比例縮放
            frame.thumbnail(preview_size, Image.Resampling.LANCZOS)
        return frame

    def close(self):
        """關閉影片"""
        if self.cap:
            self.cap.release()
            self.cap = None

    def __del__(self):
        self.close()


class KeyframeManager:
    """關鍵幀管理器"""

    def __init__(self):
        self.keyframes: List[Keyframe] = []

    def add_keyframe(self, time_ms: int, crop: CropRegion) -> Keyframe:
        """新增關鍵幀"""
        # 移除同一時間點的舊關鍵幀
        self.keyframes = [kf for kf in self.keyframes if kf.time_ms != time_ms]

        kf = Keyframe(time_ms=time_ms, crop=crop)
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda x: x.time_ms)
        return kf

    def remove_keyframe(self, time_ms: int):
        """移除指定時間的關鍵幀"""
        self.keyframes = [kf for kf in self.keyframes if kf.time_ms != time_ms]

    def get_keyframe_at(self, time_ms: int) -> Optional[Keyframe]:
        """取得指定時間的關鍵幀（如果存在）"""
        for kf in self.keyframes:
            if kf.time_ms == time_ms:
                return kf
        return None

    def interpolate_crop(self, time_ms: int) -> Optional[CropRegion]:
        """計算指定時間的插值裁切區域"""
        if not self.keyframes:
            return None

        if len(self.keyframes) == 1:
            return self.keyframes[0].crop

        # 找到前後關鍵幀
        prev_kf = None
        next_kf = None

        for kf in self.keyframes:
            if kf.time_ms <= time_ms:
                prev_kf = kf
            if kf.time_ms >= time_ms and next_kf is None:
                next_kf = kf

        # 如果在第一個關鍵幀之前
        if prev_kf is None:
            return self.keyframes[0].crop

        # 如果在最後一個關鍵幀之後
        if next_kf is None:
            return self.keyframes[-1].crop

        # 如果剛好在關鍵幀上
        if prev_kf.time_ms == time_ms:
            return prev_kf.crop

        # 線性插值
        t = (time_ms - prev_kf.time_ms) / (next_kf.time_ms - prev_kf.time_ms)

        return CropRegion(
            x=int(prev_kf.crop.x + t * (next_kf.crop.x - prev_kf.crop.x)),
            y=int(prev_kf.crop.y + t * (next_kf.crop.y - prev_kf.crop.y)),
            width=int(
                prev_kf.crop.width + t * (next_kf.crop.width - prev_kf.crop.width)
            ),
            height=int(
                prev_kf.crop.height + t * (next_kf.crop.height - prev_kf.crop.height)
            ),
        )

    def clear(self):
        """清除所有關鍵幀"""
        self.keyframes.clear()


def export_video_with_keyframes(
    input_path: str,
    output_path: str,
    keyframe_manager: KeyframeManager,
    output_width: int,
    output_height: int,
    start_time_ms: int = 0,
    end_time_ms: int = None,
    progress_callback: Callable[[int], None] = None,
) -> Tuple[bool, str]:
    """
    使用關鍵幀匯出裁切影片

    由於 FFmpeg 的 crop 濾鏡不支援動態參數，
    對於有多個關鍵幀的情況，需要使用其他方法。

    簡化版本：使用第一個關鍵幀的固定裁切。
    進階版本需要逐幀處理或使用 FFmpeg 的 sendcmd 濾鏡。
    """
    if not keyframe_manager.keyframes:
        return False, "沒有設定任何關鍵幀"

    # 取得第一個關鍵幀的裁切區域（簡化版本）
    # TODO: 進階版本需要支援動態裁切
    crop = keyframe_manager.keyframes[0].crop

    # 構建 FFmpeg 命令
    filter_complex = f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y},scale={output_width}:{output_height}"

    command = ["ffmpeg", "-y"]

    # 時間範圍
    if start_time_ms > 0:
        command.extend(["-ss", str(start_time_ms / 1000)])

    command.extend(["-i", input_path])

    if end_time_ms:
        duration = (end_time_ms - start_time_ms) / 1000
        command.extend(["-t", str(duration)])

    # 濾鏡
    command.extend(
        [
            "-vf",
            filter_complex,
            "-c:v",
            "hevc_nvenc",
            "-preset",
            "p5",
            "-qp",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            output_path,
        ]
    )

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore",
        )

        for line in process.stdout:
            pass  # 可解析進度

        process.wait()

        if process.returncode == 0:
            return True, f"匯出成功: {output_path}"
        else:
            return False, f"FFmpeg 錯誤，返回碼: {process.returncode}"

    except Exception as e:
        return False, str(e)


def format_time(ms: int) -> str:
    """格式化時間（毫秒轉 HH:MM:SS.mmm）"""
    seconds = ms // 1000
    milliseconds = ms % 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def format_time_short(ms: int) -> str:
    """格式化時間（毫秒轉 MM:SS）"""
    seconds = ms // 1000
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"
