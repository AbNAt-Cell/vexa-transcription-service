# RunPod Serverless - Quick Start

This is a simplified quick-start guide. For full documentation, see [RUNPOD_DEPLOYMENT.md](RUNPOD_DEPLOYMENT.md).

## 🚀 Deploy in 3 Steps

### Step 1: Build & Push Docker Image

```bash
# Build
docker build -f Dockerfile.runpod -t YOUR_USERNAME/vexa-transcription:latest .

# Login to Docker Hub
docker login

# Push
docker push YOUR_USERNAME/vexa-transcription:latest
```

### Step 2: Create RunPod Endpoint

1. Go to [runpod.io](https://www.runpod.io/) → **Serverless** → **+ New Endpoint**
2. Configure:
   - **Name**: `vexa-transcription`
   - **Docker Image**: `YOUR_USERNAME/vexa-transcription:latest`
   - **GPU**: RTX 3090 or A4000
   - **Workers**: Min 0, Max 3
3. **Environment Variables**:
   ```
   WHISPER_SERVICE_URL=https://your-whisper-service.runpod.io
   WHISPER_API_TOKEN=your_token
   ```
4. Click **Deploy**

### Step 3: Test It

```bash
# Get your endpoint details from RunPod dashboard
ENDPOINT_ID="your_endpoint_id"
API_KEY="your_runpod_api_key"

# Test with audio URL
curl -X POST https://api.runpod.ai/v2/$ENDPOINT_ID/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "input": {
      "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars60.wav",
      "language": "en"
    }
  }'
```

## 💰 Pricing

- **Idle**: $0 (auto-scales to zero)
- **Active**: ~$0.0004/second on RTX 3090
- **Example**: 1 minute transcription ≈ $0.024

## 📚 Full Documentation

See [RUNPOD_DEPLOYMENT.md](RUNPOD_DEPLOYMENT.md) for:
- Detailed setup instructions
- Cost optimization tips
- Troubleshooting guide
- Integration examples (Python, TypeScript, etc.)
- Advanced configuration options

## 🧪 Test Locally First

Before deploying:

```bash
pip install -r requirements.txt runpod
python test_handler.py
```

## 🆘 Need Help?

- [RunPod Docs](https://docs.runpod.io/)
- [Vexa Discord](https://discord.gg/Ga9duGkVz9)
- [GitHub Issues](https://github.com/Vexa-ai/vexa-transcription-service/issues)
