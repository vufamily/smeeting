/**
 * Meeting Assistant - Audio Processor
 * Handles processing status polling and step tracking
 */

class MeetingProcessor {
    constructor(meetingId) {
        this.meetingId = meetingId;
        this.jobId = null;
        this.status = null;
        
        // Callbacks
        this.onStatusUpdate = null;
        this.onComplete = null;
        this.onError = null;
    }

    /**
     * Start processing for a meeting
     */
    async startProcessing() {
        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ meeting_id: this.meetingId })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to start processing');
            }

            const result = await response.json();
            this.jobId = result.job_id;
            
            return result;
        } catch (error) {
            if (this.onError) {
                this.onError(error.message);
            }
            throw error;
        }
    }

    /**
     * Check processing status
     */
    async checkStatus(jobId = this.jobId) {
        if (!jobId) {
            throw new Error('No job ID available');
        }

        try {
            const response = await fetch(`/api/status/${jobId}`);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to get status');
            }

            const status = await response.json();
            this.status = status;

            if (this.onStatusUpdate) {
                this.onStatusUpdate(status);
            }

            return status;
        } catch (error) {
            if (this.onError) {
                this.onError(error.message);
            }
            throw error;
        }
    }

    /**
     * Get result for completed meeting
     */
    async getResult(meetingId = this.meetingId) {
        try {
            const response = await fetch(`/api/result/${meetingId}`);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to get results');
            }

            const result = await response.json();

            if (this.onComplete) {
                this.onComplete(result);
            }

            return result;
        } catch (error) {
            if (this.onError) {
                this.onError(error.message);
            }
            throw error;
        }
    }

    /**
     * Simulate processing step advancement (for demo)
     */
    async simulateStep(jobId = this.jobId) {
        try {
            const response = await fetch(`/api/simulate-processing/${jobId}`);
            
            if (!response.ok) {
                throw new Error('Failed to simulate step');
            }

            const status = await response.json();
            this.status = status;

            if (this.onStatusUpdate) {
                this.onStatusUpdate(status);
            }

            return status;
        } catch (error) {
            console.error('Simulate step error:', error);
        }
    }

    /**
     * Get current step name formatted for display
     */
    getStepDisplayName(step) {
        const names = {
            'upload': 'Uploading audio file',
            'validate': 'Validating audio format',
            'transcribe': 'Converting speech to text',
            'speakers': 'Identifying speakers',
            'decisions': 'Extracting key decisions',
            'tasks': 'Identifying action items',
            'summary': 'Generating meeting summary',
            'complete': 'Processing complete'
        };
        
        return names[step] || step;
    }

    /**
     * Get step progress percentage
     */
    getStepProgress(step) {
        const stepOrder = [
            'upload', 'validate', 'transcribe', 'speakers',
            'decisions', 'tasks', 'summary', 'complete'
        ];
        
        const idx = stepOrder.indexOf(step);
        if (idx === -1) return 0;
        
        return Math.round((idx / (stepOrder.length - 1)) * 100);
    }
}

/**
 * Processing UI Manager
 * Helper class to manage processing page UI updates
 */
class ProcessingUIManager {
    constructor() {
        this.steps = [
            { id: 'upload', name: 'Upload', icon: '📤' },
            { id: 'validate', name: 'Validation', icon: '✅' },
            { id: 'transcribe', name: 'Transcription', icon: '🎯' },
            { id: 'speakers', name: 'Speaker Detection', icon: '👥' },
            { id: 'decisions', name: 'Extract Decisions', icon: '📋' },
            { id: 'tasks', name: 'Extract Tasks', icon: '✅' },
            { id: 'summary', name: 'Generate Summary', icon: '📝' },
            { id: 'complete', name: 'Complete', icon: '🎉' }
        ];
        
        this.stepMap = {};
        this.steps.forEach(s => {
            this.stepMap[s.id] = s;
        });
    }

    /**
     * Update UI based on status
     */
    update(status) {
        if (!status || !status.steps) return;

        const currentIdx = this.steps.findIndex(s => s.id === status.step);

        // Update each step
        Object.keys(status.steps).forEach(stepId => {
            const stepEl = document.getElementById(`step-${stepId}`);
            if (!stepEl) return;

            const stepStatus = status.steps[stepId];
            const statusEl = stepEl.querySelector('.step-status');

            // Update status indicator
            if (stepStatus.status === 'complete') {
                stepEl.classList.remove('active');
                stepEl.classList.add('complete');
                statusEl.textContent = 'Complete';
            } else if (stepStatus.status === 'processing') {
                stepEl.classList.add('active');
                statusEl.textContent = 'Processing...';
            } else {
                stepEl.classList.remove('active', 'complete');
                statusEl.textContent = 'Waiting...';
            }
        });

        // Update progress bar
        const progressFill = document.getElementById('progressFill');
        const progressPercent = document.getElementById('progressPercent');
        const currentStepText = document.getElementById('currentStepText');

        if (progressFill) {
            progressFill.style.width = `${status.progress}%`;
        }
        if (progressPercent) {
            progressPercent.textContent = `${status.progress}%`;
        }
        if (currentStepText && status.step) {
            currentStepText.textContent = `Current: ${this.stepMap[status.step]?.name || status.step}`;
        }
    }

    /**
     * Show results button
     */
    showResultsButton() {
        const btn = document.getElementById('viewResultsBtn');
        if (btn) {
            btn.style.display = 'inline-block';
        }
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MeetingProcessor, ProcessingUIManager };
}