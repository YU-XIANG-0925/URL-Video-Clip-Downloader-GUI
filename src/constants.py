BEST_CODEC_LABEL = "最佳編碼格式 (HEVC_NVENC)"
COPY_CODEC_LABEL = "原始格式 (直接下載/不轉碼)"
VIDEO_CODECS = [COPY_CODEC_LABEL, BEST_CODEC_LABEL, "hevc_nvenc", "hevc_amf", "hevc_qsv", "libx265", "libx264", "vp9", "mpeg4", "copy"]
AUDIO_CODECS = ["aac", "opus", "libmp3lame", "copy"]
CONTAINER_FORMATS = ["mp4", "mkv", "mov", "avi"]
MERGE_CONTAINER_FORMATS = ["mp4", "mkv", "mov", "avi", "ts", "mp3"]
BATCH_VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm"]
MERGE_VIDEO_EXTENSIONS = [".mp4", ".mkv", ".mov", ".avi", ".ts", ".flv", ".webm", ".mp3"]
