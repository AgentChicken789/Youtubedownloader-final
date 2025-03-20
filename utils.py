import os
import logging
import re
import json
import datetime
from functools import wraps
from urllib.parse import urlparse, parse_qs
import yt_dlp

logger = logging.getLogger(__name__)

def is_valid_youtube_url(url):
    """
    Validates if a given URL is a valid YouTube URL.
    
    Args:
        url (str): The URL to validate
        
    Returns:
        bool: True if it's a valid YouTube URL, False otherwise
    """
    if not url:
        return False
    
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Check if the domain is youtube.com or youtu.be
    if parsed_url.netloc not in ('youtube.com', 'www.youtube.com', 'youtu.be', 'www.youtu.be'):
        return False
    
    # Check if it's a video URL
    if parsed_url.netloc in ('youtube.com', 'www.youtube.com'):
        query_params = parse_qs(parsed_url.query)
        
        # Check for video ID in query parameters
        if 'v' in query_params:
            return True
        
        # Check for playlist
        if 'list' in query_params:
            return True
        
        # Check for shorts
        if '/shorts/' in parsed_url.path:
            return True
    
    # Check for youtu.be short URLs
    elif parsed_url.netloc in ('youtu.be', 'www.youtu.be'):
        if parsed_url.path and parsed_url.path != '/':
            return True
    
    return False

def get_available_formats(video_info):
    """
    Extracts available formats from the video info returned by yt-dlp.
    
    Args:
        video_info (dict): The video info dictionary from yt-dlp
        
    Returns:
        dict: A dictionary containing video and audio formats
    """
    video_formats = []
    audio_formats = []
    
    for format_info in video_info.get('formats', []):
        # Skip formats without resolution or with unknown resolution
        format_note = format_info.get('format_note', '')
        
        if format_info.get('vcodec', 'none') != 'none' and format_info.get('acodec', 'none') != 'none':
            # This is a video with audio
            if format_note and 'p' in format_note:  # Only add if it has proper resolution
                video_formats.append({
                    'format_id': format_info.get('format_id', ''),
                    'ext': format_info.get('ext', ''),
                    'resolution': format_note,
                    'filesize': format_info.get('filesize', 0),
                    'vcodec': format_info.get('vcodec', ''),
                    'acodec': format_info.get('acodec', '')
                })
        elif format_info.get('vcodec', '') == 'none' and format_info.get('acodec', 'none') != 'none':
            # This is audio only
            audio_formats.append({
                'format_id': format_info.get('format_id', ''),
                'ext': format_info.get('ext', ''),
                'audio_quality': format_note,
                'filesize': format_info.get('filesize', 0),
                'acodec': format_info.get('acodec', '')
            })
    
    # Remove duplicates based on resolution
    unique_video_formats = {}
    for fmt in video_formats:
        key = fmt['resolution']
        if key not in unique_video_formats or fmt['filesize'] > unique_video_formats[key]['filesize']:
            unique_video_formats[key] = fmt
    
    # Sort video formats by resolution (high to low)
    sorted_video_formats = sorted(
        unique_video_formats.values(),
        key=lambda x: int(x['resolution'].replace('p', '')) if x['resolution'].replace('p', '').isdigit() else 0,
        reverse=True
    )
    
    # Sort audio formats by quality (assuming higher format_id is better quality in this case)
    sorted_audio_formats = sorted(
        audio_formats,
        key=lambda x: int(x['format_id']) if x['format_id'].isdigit() else 0,
        reverse=True
    )
    
    return {
        'video': sorted_video_formats,
        'audio': sorted_audio_formats
    }

def format_duration(seconds):
    """
    Formats duration in seconds to a human-readable string.
    
    Args:
        seconds (int): Duration in seconds
        
    Returns:
        str: Formatted duration string (HH:MM:SS or MM:SS)
    """
    if not seconds:
        return "00:00"
    
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins}:{secs:02d}"

def format_filesize(bytes_size):
    """
    Formats file size in bytes to a human-readable string.
    
    Args:
        bytes_size (int): File size in bytes
        
    Returns:
        str: Formatted file size string
    """
    if not bytes_size:
        return "Unknown size"
    
    # Convert bytes to MB
    mb_size = bytes_size / (1024 * 1024)
    
    if mb_size < 1:
        # If less than 1 MB, show in KB
        kb_size = bytes_size / 1024
        return f"{kb_size:.1f} KB"
    elif mb_size > 1024:
        # If more than 1 GB, show in GB
        gb_size = mb_size / 1024
        return f"{gb_size:.2f} GB"
    else:
        return f"{mb_size:.1f} MB"

def log_download(log_file, video_title, ip_address, user_agent):
    """
    Logs download information to a file.
    
    Args:
        log_file (str): Path to the log file
        video_title (str): Title of the downloaded video
        ip_address (str): IP address of the client
        user_agent (str): User agent string of the client
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Create directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Log the download
    with open(log_file, 'a', encoding='utf-8') as f:
        log_entry = f"[{timestamp}] Video: {video_title} | IP: {ip_address} | Agent: {user_agent}\n"
        f.write(log_entry)
