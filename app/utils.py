# app/utils.py
import re

def parse_vtt(vtt_content: str) -> str:
    """
    Parses raw VTT content to extract clean subtitle text.
    This version is robust enough for both platforms.
    """
    lines = vtt_content.strip().split('\n')
    transcript_lines = []
    seen_lines = set()

    for line in lines:
        if not line.strip() or "WEBVTT" in line or "-->" in line or line.strip().isdigit():
            continue
        
        # Clean announcer tags from Granicus and extra whitespace
        cleaned_line = re.sub(r'>>\s*', '', line).strip()
        
        if cleaned_line and cleaned_line not in seen_lines:
            transcript_lines.append(cleaned_line)
            seen_lines.add(cleaned_line)
            
    return "\n".join(transcript_lines)

def sanitize_filename(name: str) -> str:
    """Removes characters that are invalid in filenames."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return (sanitized[:150] + '...') if len(sanitized) > 150 else sanitized

def extract_youtube_video_id(url: str) -> str | None:
    """
    Extracts the 11-character YouTube video ID from a URL.
    Handles standard, short, and embed URLs.
    """
    # Standard and short URLs (and others)
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|embed\/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None