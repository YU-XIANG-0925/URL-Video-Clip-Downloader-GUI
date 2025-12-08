# URL Video Clip Downloader GUI

[繁體中文](README_zh-TW.md) | [简体中文](README_zh-CN.md)

A simple GUI application for downloading video clips from various URLs, re-encoding videos, and merging video clips.

## Features

### 📥 Downloader
- **URL Download**: Download videos from various platforms (via `yt-dlp`).
- **Video Clipping**: Specify start and end times (HH:MM:SS) to download only a segment.
- **Local File Clipping**: Supports clipping local video files.
- **Format Selection**: Choose video codecs (H.264, H.265/HEVC, NVENC, AMF, QSV) and audio codecs.
- **Low VRAM Mode**: Optimization options for low memory environments.

### 🔄 Re-encoder
- **Format Conversion**: Convert videos to different codecs or containers (MP4, MKV, AVI, etc.).
- **Batch Processing**: Support for single file or batch directory processing.
- **Hardware Acceleration**: Support for NVIDIA (NVENC), AMD (AMF), and Intel (QSV).
- **Recycle Bin**: Option to move original files to the recycle bin after successful re-encoding.

### 🎞️ Merger
- **Video Merging**: Losslessly merge multiple video clips into one file.
- **Input Selection**: Select specific files or an entire directory.
- **Recycle Bin**: Option to move original files to the recycle bin after successful merge.

### ⚙️ General
- **Task Control**: **Pause**, **Resume**, and **Stop** tasks.
- **Queue System**: Handles multiple download tasks.
- **Progress Tracking**: Real-time progress bar and status updates.

## Prerequisites

- Python 3.11 or higher.
- `uv` package manager.
- `FFmpeg` installed and available in the system's PATH.

## Installation

1.  **Clone the repository**

    ```bash
    git clone https://github.com/your-username/URL-Video-Clip-Downloader-GUI.git
    cd URL-Video-Clip-Downloader-GUI
    ```

2.  **Create a virtual environment**

    ```bash
    uv venv
    ```

3.  **Activate the virtual environment**

    On Windows:
    ```bash
    .venv\Scripts\activate
    ```

    On macOS and Linux:
    ```bash
    source .venv/bin/activate
    ```

4.  **Install dependencies**

    ```bash
    uv pip install -r requirements.txt
    ```

## Usage

1.  **Run the application**

    ```bash
    python src/main.py
    ```

2.  **Select a Tab**:
    - **Downloader**: Enter URL, set time range/format, and click "Start Download".
    - **Re-encoder**: Choose input file/folder and output settings, click "Start Re-encode".
    - **Merger**: Add files, set output filename, and click "Start Merge".

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
