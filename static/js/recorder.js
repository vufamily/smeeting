/**
 * Meeting Assistant - Audio Recorder
 * Handles microphone recording with Web Audio API visualization
 */

class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioContext = null;
        this.analyser = null;
        this.audioStream = null;
        this.recordedChunks = [];
        this.isRecording = false;
        this.recordingStartTime = null;
    }

    /**
     * Request microphone access and initialize recorder
     */
    async init() {
        try {
            this.audioStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 16000
                } 
            });

            // Setup Web Audio API for visualization
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            
            const source = this.audioContext.createMediaStreamSource(this.audioStream);
            source.connect(this.analyser);

            this.mediaRecorder = new MediaRecorder(this.audioStream, {
                mimeType: this.getSupportedMimeType()
            });

            this.recordedChunks = [];

            this.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    this.recordedChunks.push(e.data);
                }
            };

            return true;
        } catch (error) {
            console.error('Failed to initialize recorder:', error);
            throw error;
        }
    }

    /**
     * Get supported MIME type for recording
     */
    getSupportedMimeType() {
        const types = [
            'audio/webm',
            'audio/ogg',
            'audio/mp4',
            'audio/wav'
        ];

        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        }

        return 'audio/webm';
    }

    /**
     * Start recording
     */
    start() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'inactive') {
            this.recordedChunks = [];
            this.mediaRecorder.start(100); // Collect data every 100ms
            this.isRecording = true;
            this.recordingStartTime = Date.now();
        }
    }

    /**
     * Stop recording and return audio blob
     */
    stop() {
        return new Promise((resolve, reject) => {
            if (!this.mediaRecorder) {
                reject(new Error('Recorder not initialized'));
                return;
            }

            this.mediaRecorder.onstop = () => {
                const mimeType = this.getSupportedMimeType();
                const blob = new Blob(this.recordedChunks, { type: mimeType });
                this.isRecording = false;
                this.cleanup();
                resolve(blob);
            };

            if (this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            } else {
                reject(new Error('Recorder not recording'));
            }
        });
    }

    /**
     * Get elapsed recording time in seconds
     */
    getElapsedTime() {
        if (!this.recordingStartTime) return 0;
        return Math.floor((Date.now() - this.recordingStartTime) / 1000);
    }

    /**
     * Clean up resources
     */
    cleanup() {
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
        }
        
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }
    }

    /**
     * Check if recording is supported
     */
    static isSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }
}

/**
 * Waveform visualizer for recording
 */
class WaveformVisualizer {
    constructor(canvas, analyser) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.analyser = analyser;
        this.isActive = false;
        this.animationId = null;
    }

    /**
     * Start visualization
     */
    start() {
        if (this.isActive) return;
        this.isActive = true;
        this.draw();
    }

    /**
     * Stop visualization
     */
    stop() {
        this.isActive = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }

    /**
     * Draw waveform
     */
    draw() {
        if (!this.isActive) return;

        this.animationId = requestAnimationFrame(() => this.draw());

        const width = this.canvas.width = this.canvas.offsetWidth;
        const height = this.canvas.height = this.canvas.offsetHeight;

        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        this.analyser.getByteTimeDomainData(dataArray);

        // Clear canvas
        this.ctx.fillStyle = '#f8fafc';
        this.ctx.fillRect(0, 0, width, height);

        // Draw waveform
        this.ctx.lineWidth = 2;
        this.ctx.strokeStyle = '#ef4444';
        this.ctx.beginPath();

        const sliceWidth = width / bufferLength;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0;
            const y = (v * height) / 2;

            if (i === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }

            x += sliceWidth;
        }

        this.ctx.lineTo(width, height / 2);
        this.ctx.stroke();
    }
}

/**
 * Format seconds to MM:SS
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AudioRecorder, WaveformVisualizer };
}