# URL Video Clip Downloader GUI (视频片段下载器)

这是一个简单的图形化界面 (GUI) 应用程序，用于从包含 YouTube 在内的各种 URL 下载视频片段，并提供视频转码与合并功能。

## 功能特色

### 📥 下载器 (Downloader)
- **URL 下载**: 支持从各种影音平台 (通过 `yt-dlp`) 下载视频。
- **片段剪辑**: 指定开始与结束时间 (格式：HH:MM:SS)，仅下载所需的视频片段。
- **本地文件剪辑**: 亦支持对本地视频文件进行时间轴剪辑。
- **格式选择**: 可选择视频编码 (如 H.264, H.265/HEVC, NVENC, AMF, QSV) 与音频编码。
- **低 VRAM 模式**: 提供针对低显存环境的优化选项。

### 🔄 重编码器 (Re-encoder)
- **格式转换**: 将视频转换为不同的编码或容器格式 (MP4, MKV, AVI 等)。
- **批量处理**: 支持单一文件或整个目录的批量转码。
- **硬件加速**: 支持 NVIDIA (NVENC), AMD (AMF), Intel (QSV) 等硬件加速编码。
- **资源回收**: 可选择在转码成功后，自动将原始文件移至回收站。

### 🎞️ 合并器 (Merger)
- **视频合并**: 将多个视频片段无损合并为一个文件。
- **输入选择**: 可选择多个特定文件或指定目录下的所有视频进行合并。
- **资源回收**: 可选择在合并成功后，自动将原始文件移至回收站。

### ⚙️ 其他功能
- **任务控制**: 支持下载、转码与合并任务的 **暂停**、**恢复** 与 **停止**。
- **队列系统**: 简单的队列系统来处理多个下载任务。
- **进度显示**: 实时显示处理进度条与状态更新。

## 系统需求

- Python 3.11 或更高版本。
- `uv` 包管理器。
- 系统路径 (PATH) 中需安装并配置 `FFmpeg`。

## 安装说明

1.  **克隆仓库**

    ```bash
    git clone https://github.com/your-username/URL-Video-Clip-Downloader-GUI.git
    cd URL-Video-Clip-Downloader-GUI
    ```

2.  **创建虚拟环境**

    ```bash
    uv venv
    ```

3.  **激活虚拟环境**

    Windows:
    ```bash
    .venv\Scripts\activate
    ```

    macOS 和 Linux:
    ```bash
    source .venv/bin/activate
    ```

4.  **安装依赖包**

    ```bash
    uv pip install -r requirements.txt
    ```

## 使用方法

1.  **运行应用程序**

    ```bash
    python src/main.py
    ```

2.  **选择功能分页**:
    - **Downloader**: 输入 URL、设定时间范围与输出格式后点击 "Start Download"。
    - **Re-encoder**: 选择来源文件/目录与输出设定，点击 "Start Re-encode"。
    - **Merger**: 加入多个视频片段，设定输出文件名，点击 "Start Merge"。

## 贡献

欢迎提交 Pull Request。对于重大变更，请先开启 Issue 讨论您想要更改的内容。

## 授权

[MIT](https://choosealicense.com/licenses/mit/)
