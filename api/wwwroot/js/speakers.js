/**
 * Speaker Management Module
 */
window.speakers = {
    currentSpeakers: [],
    updateIntervals: {},

    /**
     * Initialize speakers
     */
    async init() {
        await this.ensureServerRunning();
        await this.discover();
    },

    /**
     * Ensures the soco-cli server is running
     */
    async ensureServerRunning() {
        try {
            const status = await api.getServerStatus();
            if (!status.isRunning) {
                updateStatus(false, 'Starting server...');
                await api.startServer();
                updateStatus(true, 'Server started');
            } else {
                updateStatus(true, 'Connected');
            }
        } catch (error) {
            console.error('Failed to start server:', error);
            updateStatus(false, 'Server error');
            showToast('Failed to start Sonos server', 'error');
        }
    },

    /**
     * Discovers speakers on the network
     */
    async discover() {
        const grid = document.getElementById('speakers-grid');
        grid.innerHTML = '<div class="loading-message"><div class="spinner"></div><p>Discovering speakers...</p></div>';

        try {
            const speakerNames = await api.getSpeakers();
            this.currentSpeakers = speakerNames;
            
            if (speakerNames.length === 0) {
                grid.innerHTML = `
                    <div class="info-message">
                        <p>No speakers found. Make sure your Sonos speakers are powered on and connected to the network.</p>
                        <button class="btn btn-primary" onclick="speakers.discover()">Try Again</button>
                    </div>
                `;
                return;
            }

            grid.innerHTML = '';
            speakerNames.forEach(name => {
                const card = createSpeakerCard(name);
                grid.appendChild(card);
            });

            // Start updating speaker info
            this.startUpdates();

            showToast(`Found ${speakerNames.length} speaker(s)`, 'success');
        } catch (error) {
            console.error('Failed to discover speakers:', error);
            grid.innerHTML = `
                <div class="info-message">
                    <p>Error discovering speakers: ${error.message}</p>
                    <button class="btn btn-primary" onclick="speakers.discover()">Try Again</button>
                </div>
            `;
            showToast('Failed to discover speakers', 'error');
        }
    },

    /**
     * Starts periodic updates for all speakers
     */
    startUpdates() {
        // Clear existing intervals
        Object.values(this.updateIntervals).forEach(clearInterval);
        this.updateIntervals = {};

        // Update each speaker every 3 seconds
        this.currentSpeakers.forEach(name => {
            this.updateSpeakerInfo(name); // Initial update
            this.updateIntervals[name] = setInterval(() => {
                this.updateSpeakerInfo(name);
            }, 3000);
        });
    },

    /**
     * Updates info for a specific speaker
     */
    async updateSpeakerInfo(speakerName) {
        try {
            const info = await api.getSpeakerInfo(speakerName);
            const card = document.querySelector(`.speaker-card[data-speaker="${speakerName}"]`);
            if (!card) return;

            // Update status
            const status = card.querySelector('.speaker-status');
            const state = formatPlaybackState(info.playbackState);
            status.className = `speaker-status ${state}`;
            status.textContent = state.charAt(0).toUpperCase() + state.slice(1);

            // Update track info
            if (info.currentTrack) {
                const trackDiv = card.querySelector('.speaker-track');
                const lines = info.currentTrack.split('\n');
                const title = lines[0] || 'No track playing';
                const artist = lines[1] || '';
                
                trackDiv.querySelector('.track-title').textContent = truncateText(title, 40);
                trackDiv.querySelector('.track-artist').textContent = truncateText(artist, 40);
            }

            // Update volume
            if (info.volume !== null && info.volume !== undefined) {
                const volumeSlider = card.querySelector('.volume-slider');
                const volumeValue = card.querySelector('.volume-value');
                volumeSlider.value = info.volume;
                volumeValue.textContent = info.volume;
            }

            // Update play/pause button
            const playPauseBtn = card.querySelector('.control-btn.primary');
            if (state === 'playing') {
                playPauseBtn.textContent = '⏸️';
            } else {
                playPauseBtn.textContent = '▶️';
            }
        } catch (error) {
            console.error(`Failed to update speaker ${speakerName}:`, error);
        }
    },

    /**
     * Play/Pause toggle
     */
    async playPause(speakerName) {
        try {
            await api.playPause(speakerName);
            setTimeout(() => this.updateSpeakerInfo(speakerName), 500);
        } catch (error) {
            showToast('Failed to toggle playback', 'error');
        }
    },

    /**
     * Next track
     */
    async next(speakerName) {
        try {
            await api.next(speakerName);
            setTimeout(() => this.updateSpeakerInfo(speakerName), 500);
            showToast('Next track', 'success');
        } catch (error) {
            showToast('Failed to skip track', 'error');
        }
    },

    /**
     * Previous track
     */
    async previous(speakerName) {
        try {
            await api.previous(speakerName);
            setTimeout(() => this.updateSpeakerInfo(speakerName), 500);
            showToast('Previous track', 'success');
        } catch (error) {
            showToast('Failed to go to previous track', 'error');
        }
    },

    /**
     * Set volume (with debouncing)
     */
    setVolume: debounce(async function(speakerName, volume) {
        try {
            await api.setVolume(speakerName, volume);
            const card = document.querySelector(`.speaker-card[data-speaker="${speakerName}"]`);
            if (card) {
                card.querySelector('.volume-value').textContent = volume;
            }
        } catch (error) {
            showToast('Failed to set volume', 'error');
        }
    }, 300),

    /**
     * Toggle mute
     */
    async toggleMute(speakerName) {
        try {
            await api.toggleMute(speakerName);
            setTimeout(() => this.updateSpeakerInfo(speakerName), 500);
            showToast('Mute toggled', 'success');
        } catch (error) {
            showToast('Failed to toggle mute', 'error');
        }
    }
};
