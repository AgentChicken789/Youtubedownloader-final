document.addEventListener('DOMContentLoaded', function() {
    const urlForm = document.getElementById('url-form');
    const urlInput = document.getElementById('youtube-url');
    const previewContainer = document.getElementById('preview-container');
    const formatContainer = document.getElementById('format-container');
    const downloadForm = document.getElementById('download-form');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const downloadContainer = document.getElementById('download-container');
    const downloadLink = document.getElementById('download-link');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const loadingSpinner = document.getElementById('loading-spinner');
    
    // Store video info globally
    let currentVideoInfo = null;
    
    // Add event listener to URL form
    urlForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const url = urlInput.value.trim();
        
        if (!url) {
            showError('Please enter a YouTube URL');
            return;
        }
        
        // Reset UI
        resetUI();
        showLoading(true);
        
        // Fetch video info
        const formData = new FormData();
        formData.append('url', url);
        
        fetch('/get_video_info', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to fetch video info');
                });
            }
            return response.json();
        })
        .then(data => {
            showLoading(false);
            currentVideoInfo = data;
            displayVideoPreview(data);
        })
        .catch(error => {
            showLoading(false);
            showError(error.message);
        });
    });
    
    // Display video preview
    function displayVideoPreview(data) {
        // Set the video title
        document.getElementById('video-title').textContent = data.title;
        
        // Set the uploader
        document.getElementById('video-uploader').textContent = data.uploader;
        
        // Set upload date
        document.getElementById('video-date').textContent = data.upload_date || 'Unknown date';
        
        // Set duration
        document.getElementById('video-duration').textContent = data.duration;
        
        // Set thumbnail
        const thumbnailImg = document.getElementById('video-thumbnail');
        thumbnailImg.src = data.thumbnail;
        thumbnailImg.alt = data.title;
        
        // Display playlist info if it's a playlist
        const playlistBadge = document.getElementById('playlist-badge');
        if (data.is_playlist) {
            playlistBadge.textContent = `Playlist: ${data.playlist_title} (${data.video_count} videos)`;
            playlistBadge.style.display = 'inline-block';
        } else {
            playlistBadge.style.display = 'none';
        }
        
        // Show the preview container
        previewContainer.style.display = 'block';
        
        // Display format options
        displayFormatOptions(data);
    }
    
    // Display format options
    function displayFormatOptions(data) {
        formatContainer.innerHTML = '';
        
        // Vereinfachte Ansicht mit nur 2 Optionen: MP4-Video oder MP3-Audio
        const optionsRow = document.createElement('div');
        optionsRow.className = 'row g-4 mb-4 justify-content-center';
        
        let videoCard = null; // Speichern für automatische Auswahl
        
        // 1. Option: MP4 Video in höchster Qualität
        if (data.formats && data.formats.length > 0) {
            const videoFormat = data.formats[0]; // Wir nehmen einfach das erste Format
            
            const videoCol = document.createElement('div');
            videoCol.className = 'col-md-5 col-sm-12';
            
            videoCard = document.createElement('div');
            videoCard.className = 'card format-option h-100';
            videoCard.dataset.formatId = videoFormat.id;
            videoCard.dataset.type = 'video';
            
            const videoCardBody = document.createElement('div');
            videoCardBody.className = 'card-body text-center';
            
            const videoIcon = document.createElement('div');
            videoIcon.className = 'mb-3 format-card-icon';
            videoIcon.innerHTML = '<i class="bi bi-film"></i>';
            
            const videoTitle = document.createElement('h4');
            videoTitle.className = 'card-title';
            videoTitle.textContent = 'MP4 Video';
            
            const videoDesc = document.createElement('p');
            videoDesc.className = 'card-text';
            videoDesc.textContent = 'Höchste Qualität';
            
            // Zeige Dateigröße wenn verfügbar
            const fileSizeInfo = document.createElement('p');
            fileSizeInfo.className = 'card-text text-muted mt-2 small';
            if (videoFormat.filesize_approx) {
                const sizeInMB = (videoFormat.filesize_approx / (1024 * 1024)).toFixed(1);
                fileSizeInfo.textContent = `Geschätzte Größe: ${sizeInMB} MB`;
            } else {
                fileSizeInfo.textContent = 'Größe wird beim Download berechnet';
            }
            
            // Resolution info
            const resInfo = document.createElement('p');
            resInfo.className = 'card-text text-info small mb-0';
            if (videoFormat.height) {
                resInfo.textContent = `${videoFormat.height}p`;
                if (videoFormat.fps) resInfo.textContent += ` ${videoFormat.fps}fps`;
            }
            
            videoCardBody.appendChild(videoIcon);
            videoCardBody.appendChild(videoTitle);
            videoCardBody.appendChild(videoDesc);
            videoCardBody.appendChild(resInfo);
            videoCardBody.appendChild(fileSizeInfo);
            videoCard.appendChild(videoCardBody);
            videoCol.appendChild(videoCard);
            optionsRow.appendChild(videoCol);
            
            // Add click event
            videoCard.addEventListener('click', function() {
                selectFormat(this);
            });
        }
        
        // 2. Option: MP3 Audio in höchster Qualität
        if (data.audio_formats && data.audio_formats.length > 0) {
            const audioFormat = data.audio_formats[0]; // Wir nehmen einfach das erste Audio-Format
            
            const audioCol = document.createElement('div');
            audioCol.className = 'col-md-5 col-sm-12';
            
            const audioCard = document.createElement('div');
            audioCard.className = 'card format-option h-100';
            audioCard.dataset.formatId = audioFormat.id;
            audioCard.dataset.type = 'audio';
            
            const audioCardBody = document.createElement('div');
            audioCardBody.className = 'card-body text-center';
            
            const audioIcon = document.createElement('div');
            audioIcon.className = 'mb-3 format-card-icon';
            audioIcon.innerHTML = '<i class="bi bi-music-note-beamed"></i>';
            
            const audioTitle = document.createElement('h4');
            audioTitle.className = 'card-title';
            audioTitle.textContent = 'MP3 Audio';
            
            const audioDesc = document.createElement('p');
            audioDesc.className = 'card-text';
            audioDesc.textContent = 'Beste Audioqualität';
            
            // Zeige Dateigröße wenn verfügbar
            const fileSizeInfo = document.createElement('p');
            fileSizeInfo.className = 'card-text text-muted mt-2 small';
            if (audioFormat.filesize_approx) {
                const sizeInMB = (audioFormat.filesize_approx / (1024 * 1024)).toFixed(1);
                fileSizeInfo.textContent = `Geschätzte Größe: ${sizeInMB} MB`;
            } else {
                fileSizeInfo.textContent = 'Größe wird beim Download berechnet';
            }
            
            // Audio quality info
            const audioInfo = document.createElement('p');
            audioInfo.className = 'card-text text-info small mb-0';
            if (audioFormat.abr) {
                audioInfo.textContent = `${audioFormat.abr}kbps`;
            }
            
            audioCardBody.appendChild(audioIcon);
            audioCardBody.appendChild(audioTitle);
            audioCardBody.appendChild(audioDesc);
            audioCardBody.appendChild(audioInfo);
            audioCardBody.appendChild(fileSizeInfo);
            audioCard.appendChild(audioCardBody);
            audioCol.appendChild(audioCard);
            optionsRow.appendChild(audioCol);
            
            // Add click event
            audioCard.addEventListener('click', function() {
                selectFormat(this);
            });
        }
        
        formatContainer.appendChild(optionsRow);
        
        // Add download button
        const downloadButtonContainer = document.createElement('div');
        downloadButtonContainer.className = 'text-center mt-4';
        
        const downloadButton = document.createElement('button');
        downloadButton.className = 'btn btn-primary';
        downloadButton.textContent = 'Ausgewähltes Format herunterladen';
        downloadButton.disabled = true;
        downloadButton.id = 'download-button';
        
        downloadButtonContainer.appendChild(downloadButton);
        formatContainer.appendChild(downloadButtonContainer);
        
        // Show the format container
        formatContainer.style.display = 'block';
        
        // Automatisch Video-Option auswählen, wenn verfügbar
        if (videoCard) {
            // Kleine Verzögerung für besseren visuellen Effekt
            setTimeout(() => {
                selectFormat(videoCard);
            }, 100);
        }
        
        // Add click event to download button
        downloadButton.addEventListener('click', function() {
            const selectedFormat = document.querySelector('.format-option.selected');
            if (!selectedFormat) {
                showError('Bitte wählen Sie zuerst ein Format aus');
                return;
            }
            
            startDownload(
                selectedFormat.dataset.formatId, 
                selectedFormat.dataset.type,
                currentVideoInfo.is_playlist
            );
        });
    }
    
    // Select a format
    function selectFormat(formatElement) {
        // Remove selected class from all formats
        document.querySelectorAll('.format-option').forEach(el => {
            el.classList.remove('selected');
        });
        
        // Add selected class to clicked format
        formatElement.classList.add('selected');
        
        // Enable download button
        document.getElementById('download-button').disabled = false;
    }
    
    // Start download
    function startDownload(formatId, type, isPlaylist) {
        // Show progress
        formatContainer.style.display = 'none';
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
        progressBar.textContent = '0%';
        
        // Playlist info anzeigen wenn nötig
        const progressStatus = document.getElementById('progress-status');
        if (isPlaylist) {
            progressStatus.innerHTML = `<div class="text-info mb-2">
                <i class="bi bi-collection-play"></i> 
                Playlist wird heruntergeladen... 
                <span id="playlist-progress">(0/${currentVideoInfo.video_count || '?'})</span>
            </div>`;
        } else {
            progressStatus.innerHTML = '';
        }
        
        // Reset download container
        downloadContainer.style.display = 'none';
        
        // Prepare form data
        const formData = new FormData();
        formData.append('format', formatId);
        formData.append('type', type);
        formData.append('is_playlist', isPlaylist);
        
        // Start download
        fetch('/download', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Download failed');
                });
            }
            return response.json();
        })
        .then(data => {
            // Angepasste Simulation basierend auf Playlist oder einzelnes Video
            if (isPlaylist) {
                simulatePlaylistProgress(currentVideoInfo.video_count || 5, () => {
                    completeDownload(data);
                });
            } else {
                simulateProgress(() => {
                    completeDownload(data);
                });
            }
        })
        .catch(error => {
            progressContainer.style.display = 'none';
            showError(error.message);
        });
    }
    
    // Komplettes Download-Ergebnis anzeigen
    function completeDownload(data) {
        // When complete, show download link
        progressContainer.style.display = 'none';
        downloadContainer.style.display = 'block';
        
        // Passender Download-Text je nach Typ
        const fileType = data.filename.toLowerCase().endsWith('.mp3') ? 'Audio' : 'Video';
        
        // Die Download-Schaltfläche aktualisieren
        downloadLink.href = data.download_link;
        downloadLink.className = 'btn btn-success btn-lg';
        downloadLink.innerHTML = `<i class="bi bi-download"></i> ${data.filename} herunterladen`;
        
        // Add file info
        const fileInfo = document.createElement('p');
        fileInfo.className = 'text-muted mt-2';
        fileInfo.innerHTML = `<small>${fileType} erfolgreich verarbeitet. Klicken Sie auf die Schaltfläche, um die Datei zu speichern.</small>`;
        
        // Entfernen aller vorherigen Informationen
        while (downloadContainer.childNodes.length > 1) {
            downloadContainer.removeChild(downloadContainer.lastChild);
        }
        
        downloadContainer.appendChild(fileInfo);
    }
    
    // Simulate progress (in a real app, you would use WebSockets or Server-Sent Events)
    function simulateProgress(callback) {
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.floor(Math.random() * 10) + 1;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                
                if (callback) {
                    setTimeout(callback, 500);
                }
            }
            
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
            progressBar.textContent = `${progress}%`;
        }, 300);
    }
    
    // Simulate playlist progress
    function simulatePlaylistProgress(videoCount, callback) {
        let currentVideo = 0;
        let totalProgress = 0;
        
        const updateProgress = () => {
            currentVideo++;
            const playlistProgressEl = document.getElementById('playlist-progress');
            if (playlistProgressEl) {
                playlistProgressEl.textContent = `(${currentVideo}/${videoCount})`;
            }
            
            totalProgress = Math.min(Math.round((currentVideo / videoCount) * 100), 100);
            progressBar.style.width = `${totalProgress}%`;
            progressBar.setAttribute('aria-valuenow', totalProgress);
            progressBar.textContent = `${totalProgress}%`;
            
            if (currentVideo >= videoCount) {
                if (callback) {
                    setTimeout(callback, 500);
                }
                return;
            }
            
            // Zufällige Zeit für den "Download" des nächsten Videos
            const nextVideoTime = 500 + Math.random() * 2000;
            setTimeout(updateProgress, nextVideoTime);
        };
        
        // Starte mit dem ersten Video
        setTimeout(updateProgress, 800);
    }
    
    // Show error message
    function showError(message) {
        errorMessage.textContent = message;
        errorContainer.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorContainer.style.display = 'none';
        }, 5000);
    }
    
    // Show/hide loading spinner
    function showLoading(show) {
        loadingSpinner.style.display = show ? 'block' : 'none';
    }
    
    // Reset UI state
    function resetUI() {
        previewContainer.style.display = 'none';
        formatContainer.style.display = 'none';
        progressContainer.style.display = 'none';
        downloadContainer.style.display = 'none';
        errorContainer.style.display = 'none';
    }
    
    // Close error message when clicking the close button
    document.getElementById('close-error').addEventListener('click', function() {
        errorContainer.style.display = 'none';
    });
    
    // URL validation helper for quick feedback
    urlInput.addEventListener('input', function() {
        const url = this.value.trim();
        const isValid = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/i.test(url);
        
        if (url && !isValid) {
            this.classList.add('is-invalid');
        } else {
            this.classList.remove('is-invalid');
        }
    });
});
