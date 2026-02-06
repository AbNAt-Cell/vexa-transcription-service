"""
Example integration for Chrome Extension to use RunPod Serverless

This example shows how to adapt your Chrome extension to use the RunPod
serverless endpoint instead of the streaming service.

Note: This is a different pattern than real-time streaming. The extension
will need to:
1. Collect audio chunks
2. Send batch requests every N seconds
3. Display transcriptions as they come back
"""

# Example JavaScript for Chrome Extension

EXAMPLE_CHROME_EXTENSION_CODE = """
// Configuration
const RUNPOD_ENDPOINT_ID = 'your_endpoint_id';
const RUNPOD_API_KEY = 'your_api_key';
const BATCH_INTERVAL_MS = 10000; // Send every 10 seconds

class RunPodTranscriptionClient {
  constructor() {
    this.audioChunks = [];
    this.isRecording = false;
    this.batchTimer = null;
  }

  startRecording() {
    this.isRecording = true;
    this.audioChunks = [];
    
    // Start batch sending timer
    this.batchTimer = setInterval(() => {
      if (this.audioChunks.length > 0) {
        this.sendBatch();
      }
    }, BATCH_INTERVAL_MS);
  }

  stopRecording() {
    this.isRecording = false;
    
    // Send any remaining chunks
    if (this.audioChunks.length > 0) {
      this.sendBatch();
    }
    
    // Clear timer
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
      this.batchTimer = null;
    }
  }

  addAudioChunk(audioBlob) {
    if (!this.isRecording) return;
    this.audioChunks.push(audioBlob);
  }

  async sendBatch() {
    if (this.audioChunks.length === 0) return;

    // Combine all audio chunks into one blob
    const combinedBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
    
    // Convert to base64
    const base64Audio = await this.blobToBase64(combinedBlob);
    
    // Clear chunks
    this.audioChunks = [];
    
    // Send to RunPod
    try {
      const transcription = await this.transcribeAudio(base64Audio);
      
      // Display transcription
      this.displayTranscription(transcription);
    } catch (error) {
      console.error('Transcription error:', error);
    }
  }

  async transcribeAudio(base64Audio) {
    // Submit job to RunPod
    const submitResponse = await fetch(
      `https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/run`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${RUNPOD_API_KEY}`
        },
        body: JSON.stringify({
          input: {
            audio: base64Audio,
            language: 'en',
            return_timestamps: true
          }
        })
      }
    );

    const submitData = await submitResponse.json();
    const jobId = submitData.id;
    
    // Poll for result
    return await this.pollForResult(jobId);
  }

  async pollForResult(jobId, maxAttempts = 60) {
    for (let i = 0; i < maxAttempts; i++) {
      const statusResponse = await fetch(
        `https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/status/${jobId}`,
        {
          headers: {
            'Authorization': `Bearer ${RUNPOD_API_KEY}`
          }
        }
      );

      const statusData = await statusResponse.json();

      if (statusData.status === 'COMPLETED') {
        return statusData.output.transcription;
      }

      if (statusData.status === 'FAILED') {
        throw new Error(statusData.error || 'Transcription failed');
      }

      // Wait 1 second before polling again
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    throw new Error('Transcription timeout');
  }

  async blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        // Remove data URL prefix (e.g., 'data:audio/webm;base64,')
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  displayTranscription(transcription) {
    console.log('Transcription:', transcription.text);
    
    // Display in your UI
    const transcriptElement = document.getElementById('transcript');
    if (transcriptElement) {
      // Append new transcription
      const segment = document.createElement('div');
      segment.className = 'transcript-segment';
      segment.textContent = transcription.text;
      transcriptElement.appendChild(segment);
    }
    
    // Or send to content script to display in meeting
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, {
          type: 'NEW_TRANSCRIPTION',
          transcription: transcription
        });
      }
    });
  }
}

// Usage in your extension
const transcriptionClient = new RunPodTranscriptionClient();

// When user starts recording
document.getElementById('start-button').addEventListener('click', () => {
  transcriptionClient.startRecording();
});

// When user stops recording
document.getElementById('stop-button').addEventListener('click', () => {
  transcriptionClient.stopRecording();
});

// When receiving audio from media stream
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'audio/webm'
    });

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        transcriptionClient.addAudioChunk(event.data);
      }
    };

    // Record in chunks (e.g., every 3 seconds)
    mediaRecorder.start(3000);
  })
  .catch(error => {
    console.error('Error accessing microphone:', error);
  });
"""


# Alternative: Upload to cloud storage and send URL
EXAMPLE_URL_BASED_CODE = """
// Alternative approach: Upload audio to cloud storage and send URL

class RunPodTranscriptionClientWithStorage {
  constructor(uploadFunction) {
    this.uploadFunction = uploadFunction; // Function to upload to S3, GCS, etc.
  }

  async transcribeFromUrl(audioUrl) {
    const submitResponse = await fetch(
      `https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/run`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${RUNPOD_API_KEY}`
        },
        body: JSON.stringify({
          input: {
            audio_url: audioUrl,  // Send URL instead of base64
            language: 'en',
            return_timestamps: true
          }
        })
      }
    );

    const submitData = await submitResponse.json();
    return await this.pollForResult(submitData.id);
  }

  async processAudioBatch(audioBlob) {
    // 1. Upload to cloud storage
    const audioUrl = await this.uploadFunction(audioBlob);
    
    // 2. Send URL to RunPod
    const transcription = await this.transcribeFromUrl(audioUrl);
    
    // 3. Display result
    this.displayTranscription(transcription);
  }
}
"""


if __name__ == "__main__":
    print("RunPod Integration Examples for Chrome Extension")
    print("=" * 60)
    print("\nThis file contains example code for integrating your Chrome")
    print("extension with the RunPod serverless endpoint.")
    print("\nSee the code in this file for:")
    print("  1. Base64-based integration (simpler)")
    print("  2. URL-based integration (better for large files)")
