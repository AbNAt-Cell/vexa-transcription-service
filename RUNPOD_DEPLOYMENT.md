# RunPod Serverless Deployment Guide

## Overview

This guide will help you deploy the Vexa Transcription Service on RunPod Serverless, enabling GPU-accelerated audio transcription with automatic scaling and pay-per-use pricing.

## Benefits of RunPod Serverless

✅ **Auto-scaling** - Automatically starts when receiving requests
✅ **Auto-stops** - Scales to zero when idle (no charges)
✅ **Pay-per-second** - Only charged during active transcription
✅ **GPU acceleration** - Fast transcription with Whisper models
✅ **Global endpoints** - Low latency worldwide

## Prerequisites

1. **RunPod Account**
   - Sign up at [runpod.io](https://www.runpod.io/)
   - Add payment method (you'll only be charged for usage)

2. **Docker** (for building images)
   - Install Docker Desktop: [docker.com/get-started](https://www.docker.com/get-started)

3. **Git**
   - Ensure you have this repository cloned

## Deployment Options

You have two options for Whisper transcription:

### Option A: External Whisper Service (Recommended)
- Deploy a separate RunPod endpoint for Whisper
- Reference it in this service's configuration
- Better separation of concerns

### Option B: Built-in Whisper Model
- Include Whisper model in the same container
- Simpler deployment but larger container
- Requires GPU allocation

**This guide covers Option A (recommended).** For Option B, see [Advanced Configuration](#advanced-configuration).

---

## Step 1: Build and Push Docker Image

### 1.1 Configure Environment

Edit `.env.runpod` with your configuration:

```bash
# If using external Whisper service
WHISPER_SERVICE_URL=https://your-whisper-service.runpod.io
WHISPER_API_TOKEN=your_whisper_api_token

# If using local Whisper (leave WHISPER_SERVICE_URL empty)
# WHISPER_MODEL=base
```

### 1.2 Build Docker Image

```bash
# Navigate to project directory
cd vexa-transcription-service

# Build the image
docker build -f Dockerfile.runpod -t vexa-transcription:latest .
```

### 1.3 Push to Docker Registry

RunPod supports Docker Hub, GitHub Container Registry, and RunPod's own registry.

**Option A: Docker Hub**

```bash
# Login to Docker Hub
docker login

# Tag your image
docker tag vexa-transcription:latest YOUR_DOCKERHUB_USERNAME/vexa-transcription:latest

# Push
docker push YOUR_DOCKERHUB_USERNAME/vexa-transcription:latest
```

**Option B: GitHub Container Registry (ghcr.io)**

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Tag your image
docker tag vexa-transcription:latest ghcr.io/YOUR_GITHUB_USERNAME/vexa-transcription:latest

# Push
docker push ghcr.io/YOUR_GITHUB_USERNAME/vexa-transcription:latest
```

---

## Step 2: Create RunPod Serverless Endpoint

### 2.1 Access RunPod Dashboard

1. Log in to [runpod.io](https://www.runpod.io/)
2. Navigate to **Serverless** → **Endpoints**
3. Click **+ New Endpoint**

### 2.2 Configure Endpoint

Fill in the following details:

**Basic Configuration:**
- **Endpoint Name**: `vexa-transcription`
- **Docker Image**: `YOUR_DOCKERHUB_USERNAME/vexa-transcription:latest`
  (or your GHCR URL)

**GPU Configuration:**
- **GPU Type**: Select GPU (e.g., RTX 3090, RTX 4090, A4000)
  - For testing: RTX 3090 or A4000
  - For production: A100 or H100 for best performance
- **Active Workers**: 0-3 (starts at 0, scales up to 3)
- **Max Workers**: 5 (adjust based on expected load)

**Advanced Options:**
- **Container Disk**: 5 GB (sufficient for the app without model)
- **Volume Mount**: Not needed for stateless operation

**Environment Variables:**

Add from your `.env.runpod` file:

```
WHISPER_SERVICE_URL=https://your-whisper-service.runpod.io
WHISPER_API_TOKEN=your_whisper_token
AUDIO_CHUNK_DURATION_SEC=3
SEGMENT_SIZE_SEC=30
MAX_AUDIO_LENGTH_SEC=3600
PROCESSING_THREADS=4
```

### 2.3 Create Endpoint

Click **Deploy** and wait for the endpoint to initialize (~2-5 minutes).

Once ready, you'll receive:
- **Endpoint ID**: e.g., `abc123xyz`
- **Endpoint URL**: e.g., `https://api.runpod.ai/v2/abc123xyz/run`
- **API Key**: Your RunPod API key

---

## Step 3: Test the Deployment

### 3.1 Using cURL

**Test with base64 audio:**

```bash
# Convert audio file to base64
BASE64_AUDIO=$(base64 -w 0 your_audio_file.wav)

# Send request
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -d '{
    "input": {
      "audio": "'"$BASE64_AUDIO"'",
      "language": "en",
      "return_timestamps": true
    }
  }'
```

**Test with audio URL:**

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -d '{
    "input": {
      "audio_url": "https://example.com/sample-audio.mp3",
      "language": "en"
    }
  }'
```

### 3.2 Using Python

```python
import runpod
import base64

# Initialize RunPod client
runpod.api_key = "YOUR_RUNPOD_API_KEY"

# Read audio file
with open("audio.wav", "rb") as f:
    audio_bytes = f.read()
    audio_base64 = base64.b64encode(audio_bytes).decode()

# Send transcription request
endpoint = runpod.Endpoint("YOUR_ENDPOINT_ID")
response = endpoint.run({
    "audio": audio_base64,
    "language": "en",
    "return_timestamps": True
})

# Get result
result = response.get("transcription")
print("Transcription:", result["text"])
```

### 3.3 Check Status

RunPod serverless requests are asynchronous. Use the status endpoint:

```bash
curl https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/status/JOB_ID \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY"
```

---

## Step 4: Monitor and Debug

### 4.1 View Logs

1. Go to **RunPod Dashboard** → **Serverless** → **Endpoints**
2. Click on your endpoint
3. Click **Logs** tab
4. View real-time logs from your handler

### 4.2 Common Issues

**Issue: "Handler not found"**
- **Solution**: Ensure `handler.py` is in the root of your Docker image
- Check that the CMD in Dockerfile is correct

**Issue: "Timeout after 300s"**
- **Solution**: Large audio files may need more time. Adjust timeout in RunPod settings
- Split large audio files into chunks

**Issue: "Out of memory"**
- **Solution**: Increase container disk size or reduce audio file size

**Issue: "Cold start is slow"**
- **Solution**: Enable "Keep Warm" option (keeps 1 worker always running, costs more)
- Or accept ~10-30s cold start for cost savings

### 4.3 Performance Monitoring

Monitor these metrics in RunPod dashboard:
- **Execution Time**: How long each request takes
- **Queue Time**: Time waiting for worker to start
- **Active Workers**: Number of currently running instances
- **Total Requests**: Request volume over time

---

## Cost Optimization

### Pricing Model

RunPod Serverless charges based on:
- **Execution time** (per second of GPU usage)
- **GPU type** (more powerful = more expensive)

**Example Costs** (approximate, check RunPod for current pricing):
- RTX 3090: ~$0.0004/second
- A4000: ~$0.0006/second
- A100: ~$0.002/second

**Cost Calculation:**
- 1-minute transcription on RTX 3090: ~$0.024
- 1-hour of audio on RTX 3090: ~$1.44

### Optimization Tips

1. **Choose the right GPU**
   - Start with RTX 3090 or A4000 (cost-effective)
   - Use A100/H100 only for high-volume production

2. **Scale to zero when idle**
   - Set **Min Workers: 0**
   - Accept cold starts to save costs

3. **Batch processing**
   - Process multiple files in one request if possible
   - Reduces overhead from multiple cold starts

4. **Set reasonable timeouts**
   - Don't pay for stuck jobs
   - Default: 300s should be plenty

5. **Monitor usage**
   - Review RunPod billing dashboard regularly
   - Set up budget alerts

---

## Advanced Configuration

### Using Built-in Whisper Model

To include Whisper in the same container:

1. **Modify `Dockerfile.runpod`:**

```dockerfile
# Add after other pip installs
RUN pip install --no-cache-dir openai-whisper

# Download model during build (reduces cold start time)
RUN python -c "import whisper; whisper.load_model('base')"
```

2. **Leave environment variables empty:**

```bash
# .env.runpod
# WHISPER_SERVICE_URL=  # Empty to use local model
WHISPER_MODEL=base  # or medium, large-v3
```

3. **Increase container disk:**
   - Base model: 5 GB
   - Large-v3 model: 10 GB

### Custom Whisper Service

If you want to deploy your own Whisper service on RunPod:

1. Use the [whisper_service repository](https://github.com/Vexa-ai/whisper_service)
2. Deploy it as a separate RunPod serverless endpoint
3. Reference its URL in this service's `WHISPER_SERVICE_URL`

### Webhook Integration

To send transcription results to your backend:

```bash
# Add to .env.runpod
ENGINE_API_URL=https://your-backend.com/api/transcriptions
ENGINE_API_TOKEN=your_backend_token
```

Modify `handler.py` to POST results to your backend after transcription.

---

## Integration with Your Application

### JavaScript/TypeScript Example

```typescript
import axios from 'axios';
import fs from 'fs';

const RUNPOD_ENDPOINT = 'YOUR_ENDPOINT_ID';
const RUNPOD_API_KEY = 'YOUR_RUNPOD_API_KEY';

async function transcribeAudio(audioPath: string) {
  // Read and encode audio
  const audioBuffer = fs.readFileSync(audioPath);
  const audioBase64 = audioBuffer.toString('base64');
  
  // Submit job
  const response = await axios.post(
    `https://api.runpod.ai/v2/${RUNPOD_ENDPOINT}/run`,
    {
      input: {
        audio: audioBase64,
        language: 'en',
        return_timestamps: true
      }
    },
    {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${RUNPOD_API_KEY}`
      }
    }
  );
  
  const jobId = response.data.id;
  
  // Poll for result
  while (true) {
    const statusResponse = await axios.get(
      `https://api.runpod.ai/v2/${RUNPOD_ENDPOINT}/status/${jobId}`,
      {
        headers: {
          'Authorization': `Bearer ${RUNPOD_API_KEY}`
        }
      }
    );
    
    if (statusResponse.data.status === 'COMPLETED') {
      return statusResponse.data.output;
    }
    
    if (statusResponse.data.status === 'FAILED') {
      throw new Error(statusResponse.data.error);
    }
    
    // Wait 1 second before polling again
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}

// Usage
transcribeAudio('./meeting-audio.wav')
  .then(result => {
    console.log('Transcription:', result.transcription.text);
  })
  .catch(error => {
    console.error('Error:', error);
  });
```

### Python Example

```python
import runpod
import base64
import time

runpod.api_key = "YOUR_RUNPOD_API_KEY"
endpoint = runpod.Endpoint("YOUR_ENDPOINT_ID")

def transcribe_audio(audio_path: str):
    # Read and encode audio
    with open(audio_path, 'rb') as f:
        audio_base64 = base64.b64encode(f.read()).decode()
    
    # Submit job
    job = endpoint.run({
        "audio": audio_base64,
        "language": "en",
        "return_timestamps": True
    })
    
    # Wait for result (with timeout)
    max_wait = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status = endpoint.status(job['id'])
        
        if status['status'] == 'COMPLETED':
            return status['output']
        
        if status['status'] == 'FAILED':
            raise Exception(status.get('error', 'Unknown error'))
        
        time.sleep(1)
    
    raise TimeoutError("Transcription timed out")

# Usage
result = transcribe_audio("meeting-audio.wav")
print("Transcription:", result['transcription']['text'])
```

---

## Updating Your Deployment

### Update Code

1. Make changes to your code
2. Rebuild Docker image:
   ```bash
   docker build -f Dockerfile.runpod -t vexa-transcription:latest .
   ```
3. Push to registry:
   ```bash
   docker push YOUR_DOCKERHUB_USERNAME/vexa-transcription:latest
   ```
4. In RunPod dashboard, refresh the endpoint or redeploy

### Update Environment Variables

1. Go to RunPod dashboard → Your endpoint
2. Click **Settings**
3. Update environment variables
4. Click **Save**
5. Changes take effect on next cold start

---

## Troubleshooting

### Enable Debug Logging

Add to environment variables:

```bash
LOG_LEVEL=DEBUG
```

### Test Locally

Before deploying to RunPod, test the handler locally:

```bash
# Install dependencies
pip install -r requirements.txt
pip install runpod

# Set environment variables
export WHISPER_SERVICE_URL=your_whisper_url
export WHISPER_API_TOKEN=your_token

# Run handler
python handler.py --rp_serve_api --rp_api_port=8000
```

Then test with:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "audio_url": "https://example.com/test-audio.mp3"
    }
  }'
```

---

## Support

For issues or questions:

1. **RunPod Documentation**: [docs.runpod.io](https://docs.runpod.io/)
2. **RunPod Discord**: [discord.gg/runpod](https://discord.gg/runpod)
3. **Vexa Community**: [discord.gg/Ga9duGkVz9](https://discord.gg/Ga9duGkVz9)
4. **GitHub Issues**: Open an issue in this repository

---

## Next Steps

- [ ] Scale to production with monitoring
- [ ] Implement caching for repeated transcriptions
- [ ] Add support for speaker diarization
- [ ] Integrate with your application backend
- [ ] Set up CI/CD for automated deployments

**Congratulations! Your Vexa Transcription Service is now running on RunPod Serverless! 🎉**
