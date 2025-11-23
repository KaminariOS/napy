"""Run a command in a shell, daemonize, log to database, and send notifications."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from daemon import DaemonContext
from daemon.pidfile import TimeoutPIDLockFile

from .config import AppConfig
from .database import save_command
from .notifications import send_email, send_telegram_message


def _execute_command_direct(cfg: AppConfig, command: str, shell: str) -> None:
    """Execute the command directly (non-daemonized) and handle logging/notifications."""
    # Get current working directory
    cwd = Path.cwd()
    
    # Setup PID file
    config_dir = Path.home() / ".config" / "napy"
    config_dir.mkdir(parents=True, exist_ok=True)
    pidfile_path = config_dir / "napy.pid"
    pidfile = TimeoutPIDLockFile(str(pidfile_path), timeout=5)
    
    # Daemonize
    with DaemonContext(
        pidfile=pidfile,
        working_directory=str(cwd),
        stdout=sys.stdout,
        stderr=sys.stderr,
        stdin=sys.stdin,
    ):
        # Now we're in the daemonized child process
        _execute_command(cfg, command, shell)


def _execute_command(cfg: AppConfig, command: str, shell: str) -> None:
    """Execute the command and handle logging/notifications."""
    import subprocess
    import threading
    from io import StringIO
    
    start_time = datetime.now()
    exit_code = None
    stdout_output = ""
    stderr_output = ""
    
    try:
        # Capture output while mirroring to the real stdout/stderr to preserve
        # live feedback and ANSI escape sequences.
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        def _reader(pipe, original_stream, capture_buffer):
            for chunk in iter(pipe.readline, ""):
                original_stream.write(chunk)
                original_stream.flush()
                capture_buffer.write(chunk)
            pipe.close()

        # Use Popen with pipes because subprocess.run expects file-like objects
        # with a real file descriptor; our tee approach is implemented manually.
        process = subprocess.Popen(
            [shell, "-c", command],
            stdin=sys.stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd(),
            text=True,
            bufsize=1,  # line-buffered
        )

        # Fan out stdout/stderr to both console and capture buffers.
        threads = [
            threading.Thread(target=_reader, args=(process.stdout, sys.stdout, stdout_capture)),
            threading.Thread(target=_reader, args=(process.stderr, sys.stderr, stderr_capture)),
        ]
        for t in threads:
            t.daemon = True
            t.start()

        exit_code = process.wait()
        for t in threads:
            t.join()

        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
    except Exception as e:
        error_msg = f"Failed to execute command: {e}"
        stderr_output = error_msg
        print(error_msg, file=sys.stderr)
        exit_code = 1
    finally:
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Save to database
        try:
            save_command(command, start_time, end_time, exit_code)
        except Exception as e:
            print(f"Failed to save to database: {e}", file=sys.stderr)
        
        # Send notifications
        success = exit_code == 0
        
        # Telegram notification
        if cfg.telegram.api_key and cfg.telegram.chat_id:
            try:
                asyncio.run(send_telegram_message(
                    cfg.telegram, command, success, exit_code,
                    stdout_output, stderr_output, start_time, end_time, duration
                ))
            except Exception as e:
                print(f"Failed to send Telegram message: {e}", file=sys.stderr)
        
        # Email notification
        if cfg.email.smtp_host and cfg.email.sender and cfg.email.recipient:
            try:
                send_email(
                    cfg.email, command, success, exit_code,
                    stdout_output, stderr_output, start_time, end_time, duration
                )
            except Exception as e:
                print(f"Failed to send email: {e}", file=sys.stderr)
        
        # if exit_code != 0:
        #     print(
        #         f"Command exited with non-zero status: {exit_code}",
        #         file=sys.stderr
        #     )
