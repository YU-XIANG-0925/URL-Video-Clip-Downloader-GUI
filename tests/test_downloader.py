import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import subprocess
from unittest.mock import MagicMock
import pytest
import yt_dlp
from src.downloader import DownloadJob, DownloadStatus, start_download

@pytest.fixture
def job():
    return DownloadJob(
        url="https://www.youtube.com/watch?v=test",
        start_time="00:01:00",
        end_time="00:02:00",
        output_path="/tmp",
        output_filename="test.mp4",
    )

def test_start_download_with_ffmpeg(mocker, job):
    """
    Test that start_download calls ffmpeg with the correct arguments
    when start and end times are provided.
    """
    mocker.patch("subprocess.run")
    start_download(job)
    subprocess.run.assert_called_once()
    args, kwargs = subprocess.run.call_args
    assert "ffmpeg" in args[0]
    assert job.url in args[0]
    assert job.start_time in args[0]
    assert job.end_time in args[0]
    assert os.path.join(job.output_path, job.output_filename) in args[0]

def test_start_download_with_yt_dlp(mocker, job):
    """
    Test that start_download calls yt-dlp when ffmpeg fails.
    """
    mocker.patch("subprocess.run", side_effect=[subprocess.CalledProcessError(1, "ffmpeg"), None])
    mocker.patch("yt_dlp.YoutubeDL")
    start_download(job)
    assert subprocess.run.call_count == 1 # only ffmpeg is called via subprocess
    yt_dlp.YoutubeDL.assert_called_once()
