import sys
import os
import pytest
from unittest.mock import MagicMock

# Add src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from downloader import DownloadJob, start_download

def test_newline_in_filename_is_sanitized(mocker):
    # Setup
    job = DownloadJob(
        url="https://example.com/video",
        start_time=None,
        end_time=None,
        output_path="C:\\tmp",
        output_filename="bad\nfilename",
        container_format="mp4"
    )

    # Mock yt_dlp.YoutubeDL
    mock_ydl = mocker.patch("yt_dlp.YoutubeDL")
    mock_ydl_instance = mock_ydl.return_value
    mock_ydl_instance.__enter__.return_value.download = MagicMock()

    # Mock os.path.exists to always return False
    mocker.patch("os.path.exists", return_value=False)
    
    # Action
    start_download(job)

    # Assert
    # Check that output_filename no longer contains newline
    assert "\n" not in job.output_filename
    
    # Check what was passed to yt-dlp
    call_args = mock_ydl.call_args
    ydl_opts = call_args[0][0]
    outtmpl = ydl_opts["outtmpl"]
    assert "\n" not in outtmpl
