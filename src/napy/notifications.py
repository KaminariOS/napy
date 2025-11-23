"""Notification modules for Telegram and Email notifications."""

from __future__ import annotations

import re
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ansi2html import Ansi2HTMLConverter
from telegram import Bot
from telegram.error import TelegramError

from .config import TelegramConfig, EmailConfig


def _format_duration(duration: timedelta) -> str:
    """Format a timedelta into a human-readable duration string."""
    total_seconds = int(duration.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    else:
        return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def _format_datetime(dt: datetime) -> str:
    """Format a datetime into a human-readable string."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text."""
    # Remove ANSI escape sequences including:
    # - ESC [ ... m (SGR - Select Graphic Rendition)
    # - ESC ] ... (OSC - Operating System Command)
    # - ESC [ ... q (cursor styles)
    # - ESC [ ... ; ... H (cursor position)
    # - ESC [ ... K (erase in line)
    # - ESC [ ... J (erase in display)
    # - ESC [ ... A/B/C/D (cursor movement)
    # - ESC [ ... f (cursor position)
    # - ESC [ ... s/u (save/restore cursor)
    # - ESC [ ... ? ... h/l (mode settings)
    # - ESC [ ... r (set scrolling region)
    # - ESC [ ... ; ... r (set scrolling region)
    # - ESC [ ... ; ... ; ... m (color codes)
    # - ESC ] ... BEL (OSC sequences)
    # - ESC [ ... ; ... ; ... ; ... ; ... m (extended color codes)
    # - ESC [ ... ; ... ; ... ; ... ; ... ; ... m (more extended codes)
    # - ESC [ ... ; ... ; ... ; ... ; ... ; ... ; ... m (even more)
    # - ESC [ ... ; ... ; ... ; ... ; ... ; ... ; ... ; ... m (RGB color codes)
    
    # Pattern to match ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))


def _format_output_html(text: str) -> str:
    """Format command output as HTML with ANSI codes converted to HTML."""
    if not text:
        return '<span class="empty-output">(empty)</span>'
    
    # Convert ANSI codes to HTML using ansi2html
    # inline=True uses inline styles, full=False returns just the body content
    conv = Ansi2HTMLConverter(inline=True, dark_bg=False)
    html_output = conv.convert(text, full=False)
    
    # ansi2html may wrap content in <pre> or <span> tags
    # We want to ensure it's properly formatted for our output-box div
    # The output should already be properly escaped by ansi2html
    return html_output


async def send_telegram_message(
    config: TelegramConfig,
    command: str,
    success: bool,
    exit_code: int | None,
    stdout: str,
    stderr: str,
    start_time: datetime,
    end_time: datetime,
    duration: timedelta,
) -> None:
    """Send a Telegram message notification with full command details."""
    if not config.api_key or not config.chat_id:
        return
    
    try:
        bot = Bot(token=config.api_key)
        status = "✅ completed successfully" if success else f"❌ failed with exit code {exit_code}"
        
        # Build the message
        message_parts = [
            f"*Command Execution Report*",
            "",
            f"*Command:* `{command}`",
            f"*Status:* {status}",
            f"*Start Time:* {_format_datetime(start_time)}",
            f"*End Time:* {_format_datetime(end_time)}",
            f"*Duration:* {_format_duration(duration)}",
        ]
        
        if stdout:
            message_parts.extend([
                "",
                "*STDOUT:*",
                "```",
                stdout[:4000] if len(stdout) > 4000 else stdout,  # Telegram has message limits
                "```",
            ])
        
        if stderr:
            message_parts.extend([
                "",
                "*STDERR:*",
                "```",
                stderr[:4000] if len(stderr) > 4000 else stderr,
                "```",
            ])
        
        message = "\n".join(message_parts)
        
        # Telegram has a 4096 character limit, truncate if needed
        if len(message) > 4096:
            message = message[:4000] + "\n\n... (message truncated)"
        
        await bot.send_message(
            chat_id=config.chat_id,
            text=message,
            parse_mode="Markdown"
        )
    except TelegramError as e:
        print(f"Failed to send Telegram message: {e}")
    except Exception as e:
        print(f"Unexpected error sending Telegram message: {e}")


def send_email(
    config: EmailConfig,
    command: str,
    success: bool,
    exit_code: int | None,
    stdout: str,
    stderr: str,
    start_time: datetime,
    end_time: datetime,
    duration: timedelta,
) -> None:
    """Send an email notification with full command details."""
    if not all([config.smtp_host, config.sender, config.recipient]):
        return
    
    try:
        # Subject is just the command
        subject = command
        
        status = "completed successfully" if success else f"failed with exit code {exit_code}"
        status_icon = "✅" if success else "❌"
        
        # Build HTML email body
        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 150px 1fr;
            gap: 10px 20px;
            margin: 20px 0;
        }}
        .info-label {{
            font-weight: bold;
            color: #555;
        }}
        .info-value {{
            color: #333;
        }}
        .status-success {{
            color: #27ae60;
        }}
        .status-failure {{
            color: #e74c3c;
        }}
        .section {{
            margin: 30px 0;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid #ecf0f1;
        }}
        .output-box {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            white-space: pre-wrap;
            word-wrap: break-word;
            border-left: 4px solid #3498db;
        }}
        .empty-output {{
            color: #95a5a6;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Command Execution Report</h1>
        
        <div class="info-grid">
            <div class="info-label">Command:</div>
            <div class="info-value"><code>{_escape_html(command)}</code></div>
            
            <div class="info-label">Status:</div>
            <div class="info-value">
                <span class="{'status-success' if success else 'status-failure'}">
                    {status_icon} {status}
                </span>
            </div>
            
            <div class="info-label">Exit Code:</div>
            <div class="info-value">{exit_code}</div>
            
            <div class="info-label">Start Time:</div>
            <div class="info-value">{_format_datetime(start_time)}</div>
            
            <div class="info-label">End Time:</div>
            <div class="info-value">{_format_datetime(end_time)}</div>
            
            <div class="info-label">Duration:</div>
            <div class="info-value">{_format_duration(duration)}</div>
        </div>
        
        <div class="section">
            <div class="section-title">STDOUT</div>
            <div class="output-box">{_format_output_html(stdout)}</div>
        </div>
        
        <div class="section">
            <div class="section-title">STDERR</div>
            <div class="output-box">{_format_output_html(stderr)}</div>
        </div>
    </div>
</body>
</html>"""
        
        # Also create a plain text version for email clients that don't support HTML
        plain_body_parts = [
            "Command Execution Report",
            "=" * 70,
            "",
            f"Command: {command}",
            f"Status: {status}",
            f"Exit Code: {exit_code}",
            f"Start Time: {_format_datetime(start_time)}",
            f"End Time: {_format_datetime(end_time)}",
            f"Duration: {_format_duration(duration)}",
            "",
            "STDOUT:",
            "-" * 70,
            _strip_ansi_codes(stdout) if stdout else "(empty)",
            "",
            "STDERR:",
            "-" * 70,
            _strip_ansi_codes(stderr) if stderr else "(empty)",
        ]
        plain_body = "\n".join(plain_body_parts)
        
        msg = MIMEMultipart("alternative")
        msg["From"] = config.sender
        msg["To"] = config.recipient
        msg["Subject"] = subject
        
        # Attach both plain text and HTML versions
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        
        port = config.smtp_port or 465
        use_tls = port == 587
        
        if use_tls:
            server = smtplib.SMTP(config.smtp_host, port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(config.smtp_host, port)
        
        if config.smtp_user and config.smtp_pass:
            server.login(config.smtp_user, config.smtp_pass)
        
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")
        import traceback
        traceback.print_exc()

