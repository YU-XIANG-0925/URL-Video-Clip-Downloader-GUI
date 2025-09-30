# URL Video Clip Downloader GUI

A simple GUI application for downloading video clips from various URLs, including YouTube.

## Features

- Download video clips by providing a URL.
- Specify start and end times to download only a segment of the video.
- Choose the output path and filename.
- A simple queue system to handle multiple downloads.
- Progress bar and status updates.
- Error handling for common issues.

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

2.  **Enter the video URL** in the "URL" field.

3.  **Set the time range** (optional) in HH:MM:SS format.

4.  **Choose the output path and filename**.

5.  **Click "Start Download"**.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)