import os
import logging
import uuid
import json
import datetime
import re
import zipfile
import time
import threading
from functools import wraps
import yt_dlp
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import shutil
from PIL import Image
from urllib.parse import urlparse
import tempfile
from werkzeug.exceptions import BadRequest

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "youtube_downloader_secret")

# Create downloads and logs directories if they don't exist
if not os.path.exists('downloads'):
    os.makedirs('downloads')
if not os.path.exists('logs'):
    os.makedirs('logs')

# Define log file path
LOG_FILE = 'logs/downloads.txt'

# Validate YouTube URL
def is_valid_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})|'
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(playlist\?list=)([^&=%\?]+)'
    )
    youtube_match = re.match(youtube_regex, url)
    return bool(youtube_match)

# Extract video info using yt-dlp
def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'writeinfojson': True,
        'noplaylist': False,  # Allow playlists
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        ydl_opts['paths'] = {'home': temp_dir}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                
                # Handle both single videos and playlists
                if 'entries' in info:  # It's a playlist
                    is_playlist = True
                    playlist_title = info.get('title', 'Unknown Playlist')
                    entries = info['entries']
                    if entries:
                        first_video = entries[0]
                        video_count = len(entries)
                    else:
                        return None  # Empty playlist
                else:  # It's a single video
                    is_playlist = False
                    first_video = info
                    playlist_title = None
                    video_count = 1
                
                # Parse duration
                duration_secs = first_video.get('duration', 0)
                if duration_secs:
                    mins, secs = divmod(duration_secs, 60)
                    hours, mins = divmod(mins, 60)
                    if hours:
                        duration_str = f"{hours}:{mins:02d}:{secs:02d}"
                    else:
                        duration_str = f"{mins}:{secs:02d}"
                else:
                    duration_str = "Unknown"

                # Format upload date
                upload_date = first_video.get('upload_date', '')
                if upload_date and len(upload_date) == 8:
                    upload_date = f"{upload_date[6:8]}.{upload_date[4:6]}.{upload_date[0:4]}"
                
                # Nur zwei Optionen zur Verfügung stellen: Beste Videoqualität (MP4) und Beste Audioqualität (MP3)
                # Beste Video-Option (MP4)
                best_video_format = {
                    'id': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'note': 'Höchste Qualität',
                    'ext': 'mp4',
                    'type': 'video'
                }
                
                # Beste Audio-Option (MP3)
                best_audio_format = {
                    'id': 'bestaudio/best',
                    'note': 'Beste Audioqualität',
                    'ext': 'mp3',
                    'type': 'audio'
                }
                
                # Erstelle einfache Arrays mit nur je einer Option
                sorted_formats = [best_video_format]
                sorted_audio = [best_audio_format]
                
                return {
                    'title': first_video.get('title', 'Unknown Title'),
                    'uploader': first_video.get('uploader', 'Unknown Uploader'),
                    'upload_date': upload_date,
                    'duration': duration_str,
                    'thumbnail': first_video.get('thumbnail'),
                    'is_playlist': is_playlist,
                    'playlist_title': playlist_title,
                    'video_count': video_count,
                    'formats': sorted_formats,  # Include all available formats
                    'audio_formats': sorted_audio  # Include all available audio formats
                }
            except Exception as e:
                logger.error(f"Error extracting video info: {e}")
                return None

# Log download information
def log_download(video_title, ip_address, user_agent):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] Video: {video_title} | IP: {ip_address} | Agent: {user_agent}\n"
        f.write(log_entry)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_video_info', methods=['POST'])
def fetch_video_info():
    url = request.form.get('url', '')
    
    if not url:
        return jsonify({'error': 'URL wird benötigt'}), 400
    
    if not is_valid_youtube_url(url):
        return jsonify({'error': 'Ungültige YouTube-URL'}), 400
    
    video_info = get_video_info(url)
    
    if not video_info:
        return jsonify({'error': 'Video-Informationen konnten nicht abgerufen werden'}), 400
    
    # Store the URL in the session for later use
    session['video_url'] = url
    
    return jsonify(video_info)

@app.route('/download', methods=['POST'])
def download_video():
    url = session.get('video_url')
    if not url:
        return jsonify({'error': 'Keine Video-URL in der Sitzung gefunden'}), 400
    
    format_id = request.form.get('format')
    if not format_id:
        return jsonify({'error': 'Kein Format ausgewählt'}), 400
    
    download_type = request.form.get('type', 'video')
    is_playlist = json.loads(request.form.get('is_playlist', 'false').lower())
    
    # Create a unique download directory
    download_id = str(uuid.uuid4())
    download_dir = os.path.join('downloads', download_id)
    os.makedirs(download_dir, exist_ok=True)
    
    # Prepare download options
    ydl_opts = {
        'paths': {'home': download_dir},
        'format': format_id,
        'outtmpl': '%(title)s.%(ext)s',
        'noplaylist': not is_playlist,
    }
    
    # Add audio-specific options
    if download_type == 'audio':
        ydl_opts.update({
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
        })
    
    # Start download in a way that we can get progress updates
    def download_hook(d):
        if d['status'] == 'downloading':
            progress = {
                'downloaded_bytes': d.get('downloaded_bytes', 0),
                'total_bytes': d.get('total_bytes', 0),
                'total_bytes_estimate': d.get('total_bytes_estimate', 0),
                'elapsed': d.get('elapsed', 0),
                'eta': d.get('eta', 0),
                'speed': d.get('speed', 0),
                'filename': d.get('filename', ''),
                'status': 'downloading',
                'progress': d.get('_percent_str', '0%').strip()
            }
            # For now we just log the progress - in a real app, we might use websockets or polling
            logger.debug(f"Download progress: {progress['progress']}")
        
        elif d['status'] == 'finished':
            logger.debug("Download finished")
    
    ydl_opts['progress_hooks'] = [download_hook]
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Get the downloaded file path
            if 'entries' in info and is_playlist:
                # It's a playlist
                files = []
                for entry in info['entries']:
                    if entry:
                        for file in os.listdir(download_dir):
                            if file.endswith(('.mp4', '.mkv', '.webm', '.mp3')):
                                files.append(os.path.join(download_dir, file))
                download_file = files[0] if files else None
                title = info.get('title', 'Playlist')
            else:
                # Single video
                files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) 
                         if f.endswith(('.mp4', '.mkv', '.webm', '.mp3'))]
                download_file = files[0] if files else None
                title = info.get('title', 'Video')
            
            if not download_file:
                return jsonify({'error': 'Download fehlgeschlagen oder keine Dateien gefunden'}), 500
            
            # Log the download
            log_download(
                title,
                request.remote_addr,
                request.headers.get('User-Agent', 'Unknown')
            )
            
            # Generate a download link with the file name
            filename = os.path.basename(download_file)
            session['download_path'] = download_file
            session['download_filename'] = filename
            
            return jsonify({
                'success': True, 
                'download_link': url_for('serve_download'),
                'filename': filename
            })
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': f'Download fehlgeschlagen: {str(e)}'}), 500

@app.route('/serve_download')
def serve_download():
    download_path = session.get('download_path')
    filename = session.get('download_filename')
    
    if not download_path or not filename or not os.path.exists(download_path):
        return "Datei nicht gefunden oder Download-Link abgelaufen", 404
    
    def remove_after_send(download_dir):
        # Clean up by removing the download directory after serving the file
        parent_dir = os.path.dirname(download_path)
        if os.path.exists(parent_dir) and parent_dir.startswith('downloads/'):
            try:
                shutil.rmtree(parent_dir)
            except Exception as e:
                logger.error(f"Error removing directory {parent_dir}: {e}")
    
    response = send_file(download_path, as_attachment=True, download_name=filename)
    
    # Schedule directory removal for after response is sent
    # This is a hack since Flask doesn't have a post-send hook
    response.call_on_close(lambda: remove_after_send(os.path.dirname(download_path)))
    
    return response

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource nicht gefunden'}), 404

@app.route('/cloudflare_export')
def cloudflare_export():
    """
    Erstellt ein ZIP-Paket mit allen notwendigen Dateien für die Cloudflare-Bereitstellung.
    """
    # Erstelle ein temporäres Verzeichnis für das Export-Paket
    export_id = str(uuid.uuid4())
    export_dir = os.path.join('downloads', f'cloudflare_export_{export_id}')
    os.makedirs(export_dir, exist_ok=True)
    
    try:
        # ZIP-Dateiname
        zip_filename = os.path.join(export_dir, 'youtube_downloader_cloudflare.zip')
        
        # Dateien und Verzeichnisse, die in das ZIP-Paket aufgenommen werden sollen
        files_to_include = []
        
        # Python-Dateien im Hauptverzeichnis
        for file in os.listdir('.'):
            if file.endswith('.py'):
                files_to_include.append((file, file))
        
        # Templates-Verzeichnis
        for file in os.listdir('templates'):
            files_to_include.append((os.path.join('templates', file), os.path.join('templates', file)))
        
        # Static-Verzeichnis
        for root, dirs, files in os.walk('static'):
            for file in files:
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, '.')
                files_to_include.append((source_path, relative_path))
        
        # Wichtige Konfigurationsdateien
        for file in ['.replit', 'requirements.txt', 'pyproject.toml']:
            if os.path.exists(file):
                files_to_include.append((file, file))
        
        # Eine Beispiel-Umgebungsdatei für Cloudflare
        with open(os.path.join(export_dir, '.env.example'), 'w') as f:
            f.write("# Umgebungsvariablen für die Cloudflare-Bereitstellung\n")
            f.write("SESSION_SECRET=ändere_mich_in_einen_sicheren_wert\n")
        
        files_to_include.append((os.path.join(export_dir, '.env.example'), '.env.example'))
        
        # Eine README-Datei mit Anweisungen
        readme_content = """# YouTube Downloader für Cloudflare

## Anleitung zur Bereitstellung

1. Entpacken Sie dieses ZIP-Archiv in ein Verzeichnis
2. Erstellen Sie eine Datei `.env` basierend auf `.env.example` und setzen Sie alle erforderlichen Umgebungsvariablen
3. Stellen Sie die Anwendung auf Cloudflare Workers bereit:
   ```
   wrangler deploy
   ```

## Anforderungen

- Python 3.9 oder höher
- yt-dlp
- Flask
- ffmpeg (für Audio-Konvertierung)

## Hinweise

Diese Anwendung ist als Demonstration gedacht. Bitte beachten Sie die Urheberrechte und Nutzungsbedingungen von YouTube.
"""
        
        with open(os.path.join(export_dir, 'README.md'), 'w') as f:
            f.write(readme_content)
        
        files_to_include.append((os.path.join(export_dir, 'README.md'), 'README.md'))
        
        # Beispiel Cloudflare Workers-Konfiguration
        wrangler_config = """name = "youtube-downloader"
main = "main.py"
compatibility_date = "2025-03-20"

[vars]
# Setzen Sie Umgebungsvariablen in der Datei .env oder in der Cloudflare-Konsole

[env.production]
workers_dev = true
"""
        
        with open(os.path.join(export_dir, 'wrangler.toml'), 'w') as f:
            f.write(wrangler_config)
        
        files_to_include.append((os.path.join(export_dir, 'wrangler.toml'), 'wrangler.toml'))
        
        # Erstelle das ZIP-Archiv
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for source_path, zip_path in files_to_include:
                if os.path.exists(source_path):
                    zipf.write(source_path, zip_path)
        
        # Sende die ZIP-Datei
        return send_file(
            zip_filename,
            as_attachment=True,
            download_name='youtube_downloader_cloudflare.zip'
        )
    
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Cloudflare-Exports: {e}")
        return jsonify({'error': f'Export fehlgeschlagen: {str(e)}'}), 500
    finally:
        # Bereinige das temporäre Verzeichnis nach einer kurzen Verzögerung
        def delayed_cleanup():
            try:
                time.sleep(10)  # Kleine Verzögerung, um sicherzustellen, dass die Datei gesendet wurde
                if os.path.exists(export_dir):
                    shutil.rmtree(export_dir)
            except Exception as e:
                logger.error(f"Fehler beim Bereinigen des Export-Verzeichnisses: {e}")
        
        # In einer Produktionsumgebung würde man hier einen Background-Worker verwenden
        import threading
        threading.Thread(target=delayed_cleanup).start()

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Interner Serverfehler'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
