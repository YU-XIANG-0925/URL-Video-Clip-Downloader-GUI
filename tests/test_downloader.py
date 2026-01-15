import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import subprocess
from unittest.mock import MagicMock, patch
import pytest
import yt_dlp
from downloader import DownloadJob, DownloadStatus, start_download

@pytest.fixture
def job():
    return DownloadJob(
        url="https://www.youtube.com/watch?v=test",
        start_time="00:01:00",
        end_time="00:02:00",
        output_path="/tmp",
        output_filename="test.mp4",
        container_format="mp4"
    )

def test_start_download_with_ffmpeg(mocker, job):
    """
    Test that start_download calls _run_stoppable_ffmpeg with the correct arguments
    when start and end times are provided.
    """
    mock_run = mocker.patch("downloader._run_stoppable_ffmpeg", return_value=(True, "Success"))
    start_download(job)
    
    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    command = args[0]
    
    assert "ffmpeg" in command
    assert job.url in command
    assert job.start_time in command
    assert job.end_time in command

def test_start_download_with_yt_dlp(mocker, job):
    """
    Test that start_download calls yt-dlp when ffmpeg fails.
    """
    # First call to ffmpeg fails
    mocker.patch("downloader._run_stoppable_ffmpeg", return_value=(False, "ffmpeg failed"))
    mock_ydl = mocker.patch("yt_dlp.YoutubeDL")
    mock_ydl_instance = mock_ydl.return_value
    mock_ydl_instance.__enter__.return_value.download = MagicMock()
    
    start_download(job)
    
    yt_dlp.YoutubeDL.assert_called_once()
