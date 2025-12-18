import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from merger import merge_videos
from constants import BEST_CODEC_LABEL

class TestMergerMp3(unittest.TestCase):

    @patch('merger.subprocess.run')
    @patch('merger.subprocess.Popen')
    @patch('merger.os.remove') # Mock remove to avoid errors
    @patch('merger.os.path.exists', return_value=False) # Mock exists
    def test_merge_mp3_forces_copy(self, mock_exists, mock_remove, mock_popen, mock_run):
        # Setup mocks
        # Mock ffprobe duration call
        mock_run.return_value.stdout = "10.0"
        
        # Mock ffmpeg process
        mock_process = MagicMock()
        mock_process.stdout = [] # No output simulation needed for now
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        input_files = ["file1.mp3", "file2.mp3"]
        output_file = "output.mp3"
        
        # Test with BEST_CODEC_LABEL, which usually sets video codecs
        success, msg = merge_videos(input_files, output_file, video_codec=BEST_CODEC_LABEL)

        self.assertTrue(success)
        
        # Check the args passed to Popen
        args, _ = mock_popen.call_args
        command = args[0]
        
        print(f"DEBUG: Command used: {command}")

        # Verify -c copy is present
        self.assertIn("-c", command)
        self.assertIn("copy", command)
        
        # Verify video codec flags are NOT present
        self.assertNotIn("-c:v", command)
        self.assertNotIn("hevc_nvenc", command)

    @patch('merger.subprocess.run')
    @patch('merger.subprocess.Popen')
    @patch('merger.os.remove')
    @patch('merger.os.path.exists', return_value=False)
    def test_merge_mp4_uses_video_codec(self, mock_exists, mock_remove, mock_popen, mock_run):
        # Setup mocks
        mock_run.return_value.stdout = "10.0"
        
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        input_files = ["file1.mp4", "file2.mp4"]
        output_file = "output.mp4"
        
        # Test with BEST_CODEC_LABEL
        success, msg = merge_videos(input_files, output_file, video_codec=BEST_CODEC_LABEL)

        self.assertTrue(success)
        
        args, _ = mock_popen.call_args
        command = args[0]
        
        print(f"DEBUG: Command used: {command}")

        # Verify video codec flags ARE present
        self.assertIn("-c:v", command)
        self.assertIn("hevc_nvenc", command)

if __name__ == '__main__':
    unittest.main()
