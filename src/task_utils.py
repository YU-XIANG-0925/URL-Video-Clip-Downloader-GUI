import threading
import psutil
import subprocess
import time

class TaskController:
    def __init__(self):
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.process = None  # subprocess.Popen object
        self.psutil_process = None

    def set_process(self, process: subprocess.Popen):
        self.process = process
        if process:
            try:
                self.psutil_process = psutil.Process(process.pid)
            except psutil.NoSuchProcess:
                self.psutil_process = None

    def stop(self):
        """Signals the task to stop and terminates the underlying process."""
        self.stop_event.set()
        if self.process:
            try:
                # Terminate the process. 
                # On Windows, terminate() sends SIGTERM.
                self.process.terminate()
            except Exception:
                pass
            
            # If we were paused, we need to resume first to allow termination to handle gracefully if needed,
            # though terminate() is usually abrupt. 
            # However, if the process is suspended, it might not receive the terminate signal immediately/properly on some OSs.
            # Best practice: resume then kill.
            if self.pause_event.is_set():
                self.resume()
                try:
                    self.process.kill() # Force kill if it was suspended
                except Exception:
                    pass

    def pause(self):
        """Pauses the underlying process."""
        if not self.pause_event.is_set() and not self.stop_event.is_set():
            self.pause_event.set()
            if self.psutil_process:
                try:
                    self.psutil_process.suspend()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

    def resume(self):
        """Resumes the underlying process."""
        if self.pause_event.is_set():
            self.pause_event.clear()
            if self.psutil_process:
                try:
                    self.psutil_process.resume()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

    def is_stopped(self):
        return self.stop_event.is_set()
