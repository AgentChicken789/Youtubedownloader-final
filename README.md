# YouTube Downloader für Cloudflare

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
