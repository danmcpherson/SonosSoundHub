/**
 * API Client for communicating with the backend
 */
class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    /**
     * Makes an HTTP request
     */
    async request(url, options = {}) {
        const response = await fetch(`${this.baseUrl}${url}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Request failed' }));
            throw new Error(error.message || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Sonos Server Management
    async getServerStatus() {
        return this.request('/api/sonos/status');
    }

    async startServer() {
        return this.request('/api/sonos/start', { method: 'POST' });
    }

    async stopServer() {
        return this.request('/api/sonos/stop', { method: 'POST' });
    }

    // Speakers
    async getSpeakers() {
        return this.request('/api/sonos/speakers');
    }

    async rediscoverSpeakers() {
        return this.request('/api/sonos/rediscover', { method: 'POST' });
    }

    async getSpeakerInfo(speakerName) {
        return this.request(`/api/sonos/speakers/${encodeURIComponent(speakerName)}`);
    }

    // Playback Control
    async executeCommand(speaker, action, args = []) {
        return this.request('/api/sonos/command', {
            method: 'POST',
            body: JSON.stringify({ speaker, action, args })
        });
    }

    async playPause(speakerName) {
        return this.request(`/api/sonos/speakers/${encodeURIComponent(speakerName)}/playpause`, {
            method: 'POST'
        });
    }

    async next(speakerName) {
        return this.request(`/api/sonos/speakers/${encodeURIComponent(speakerName)}/next`, {
            method: 'POST'
        });
    }

    async previous(speakerName) {
        return this.request(`/api/sonos/speakers/${encodeURIComponent(speakerName)}/previous`, {
            method: 'POST'
        });
    }

    async setVolume(speakerName, volume) {
        return this.request(`/api/sonos/speakers/${encodeURIComponent(speakerName)}/volume/${volume}`, {
            method: 'POST'
        });
    }

    async getVolume(speakerName) {
        return this.request(`/api/sonos/speakers/${encodeURIComponent(speakerName)}/volume`);
    }

    async toggleMute(speakerName) {
        return this.request(`/api/sonos/speakers/${encodeURIComponent(speakerName)}/mute`, {
            method: 'POST'
        });
    }

    async getCurrentTrack(speakerName) {
        return this.request(`/api/sonos/speakers/${encodeURIComponent(speakerName)}/track`);
    }

    // Macros
    async getMacros() {
        return this.request('/api/macro');
    }

    async getMacro(name) {
        return this.request(`/api/macro/${encodeURIComponent(name)}`);
    }

    async saveMacro(macro) {
        return this.request('/api/macro', {
            method: 'POST',
            body: JSON.stringify(macro)
        });
    }

    async deleteMacro(name) {
        return this.request(`/api/macro/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
    }

    async executeMacro(macroName, args = []) {
        return this.request('/api/macro/execute', {
            method: 'POST',
            body: JSON.stringify({ macroName, arguments: args })
        });
    }

    async reloadMacros() {
        return this.request('/api/macro/reload', {
            method: 'POST'
        });
    }
}

// Export a singleton instance
const api = new ApiClient();
