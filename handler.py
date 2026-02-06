"""
RunPod Serverless Handler for Vexa Transcription Service

This handler provides a simplified, stateless interface for audio transcription
optimized for RunPod's serverless environment. It eliminates the need for Redis
and background workers by processing requests synchronously.

Input Format:
{
    "input": {
        "audio": "base64_encoded_audio_data" OR "audio_url",
        "audio_url": "https://example.com/audio.mp3" (optional, alternative to audio),
        "language": "en" (optional),
        "task": "transcribe" (optional, default: "transcribe"),
        "return_timestamps": true (optional, default: true),
        "model": "large-v3" (optional, default from env)
    }
}

Output Format:
{
    "status": "success",
    "transcription": {
        "text": "Full transcription text...",
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 5.2,
                "text": "Segment text...",
                "words": [...]
            }
        ],
        "language": "en"
    },
    "processing_time": 2.5
}
"""

import runpod
import base64
import httpx
import io
import os
import tempfile
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Handles transcription using external Whisper service or local model."""
    
    def __init__(self):
        self.whisper_service_url = os.getenv("WHISPER_SERVICE_URL")
        self.whisper_api_token = os.getenv("WHISPER_API_TOKEN")
        self.use_external_service = bool(self.whisper_service_url)
        
        logger.info(f"Initialized WhisperTranscriber (external_service={self.use_external_service})")
        
        if not self.use_external_service:
            logger.warning("No WHISPER_SERVICE_URL provided. Will attempt to use local Whisper model.")
    
    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        task: str = "transcribe",
        return_timestamps: bool = True
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper service or local model.
        
        Args:
            audio_bytes: Raw audio data
            language: Language code (e.g., 'en', 'es', 'fr')
            task: 'transcribe' or 'translate'
            return_timestamps: Whether to return word-level timestamps
            
        Returns:
            Dictionary containing transcription results
        """
        start_time = time.time()
        
        if self.use_external_service:
            result = await self._call_whisper_service(
                audio_bytes, language, task, return_timestamps
            )
        else:
            result = await self._use_local_whisper(
                audio_bytes, language, task, return_timestamps
            )
        
        processing_time = time.time() - start_time
        logger.info(f"Transcription completed in {processing_time:.2f}s")
        
        return result
    
    async def _call_whisper_service(
        self,
        audio_bytes: bytes,
        language: Optional[str],
        task: str,
        return_timestamps: bool
    ) -> Dict[str, Any]:
        """Call external Whisper service."""
        logger.info(f"Calling Whisper service at {self.whisper_service_url}")
        
        # Prepare the request payload
        payload = {
            "task": task,
            "return_timestamps": return_timestamps
        }
        
        if language:
            payload["language"] = language
        
        # Prepare audio file
        files = {
            "audio": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")
        }
        
        headers = {}
        if self.whisper_api_token:
            headers["Authorization"] = f"Bearer {self.whisper_api_token}"
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                response = await client.post(
                    f"{self.whisper_service_url}/transcribe",
                    files=files,
                    data=payload,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Whisper service error: {e}")
                raise Exception(f"Failed to call Whisper service: {str(e)}")
    
    async def _use_local_whisper(
        self,
        audio_bytes: bytes,
        language: Optional[str],
        task: str,
        return_timestamps: bool
    ) -> Dict[str, Any]:
        """Use local Whisper model (fallback if no external service)."""
        logger.info("Using local Whisper model")
        
        try:
            import whisper
            import torch
            
            # Load model (consider caching this)
            model_name = os.getenv("WHISPER_MODEL", "base")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading Whisper model '{model_name}' on {device}")
            
            model = whisper.load_model(model_name, device=device)
            
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name
            
            try:
                # Transcribe
                result = model.transcribe(
                    tmp_path,
                    language=language,
                    task=task,
                    word_timestamps=return_timestamps
                )
                
                return {
                    "text": result["text"],
                    "segments": result.get("segments", []),
                    "language": result.get("language", language)
                }
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except ImportError:
            raise Exception(
                "Whisper not installed locally and no WHISPER_SERVICE_URL provided. "
                "Please install openai-whisper or configure WHISPER_SERVICE_URL."
            )


async def download_audio(url: str) -> bytes:
    """Download audio from URL."""
    logger.info(f"Downloading audio from {url}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as e:
            logger.error(f"Failed to download audio: {e}")
            raise Exception(f"Failed to download audio from URL: {str(e)}")


async def process_audio_input(job_input: Dict[str, Any]) -> bytes:
    """
    Process audio input from various sources.
    
    Supports:
    - Base64 encoded audio data
    - Audio URL for download
    """
    if "audio" in job_input:
        # Base64 encoded audio
        audio_data = job_input["audio"]
        
        if isinstance(audio_data, str):
            # Decode base64
            try:
                return base64.b64decode(audio_data)
            except Exception as e:
                raise ValueError(f"Invalid base64 audio data: {str(e)}")
        elif isinstance(audio_data, bytes):
            return audio_data
        else:
            raise ValueError("Audio data must be base64 string or bytes")
    
    elif "audio_url" in job_input:
        # Download from URL
        return await download_audio(job_input["audio_url"])
    
    else:
        raise ValueError("No audio input provided. Use 'audio' (base64) or 'audio_url'")


async def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod handler function for audio transcription.
    
    Args:
        job: RunPod job dictionary containing 'input' with audio data
        
    Returns:
        Dictionary with transcription results
    """
    job_input = job.get("input", {})
    
    try:
        logger.info("Processing transcription job")
        logger.info(f"Job input keys: {list(job_input.keys())}")
        
        # Extract parameters
        language = job_input.get("language")
        task = job_input.get("task", "transcribe")
        return_timestamps = job_input.get("return_timestamps", True)
        
        # Process audio input
        audio_bytes = await process_audio_input(job_input)
        logger.info(f"Processed audio input: {len(audio_bytes)} bytes")
        
        # Initialize transcriber
        transcriber = WhisperTranscriber()
        
        # Perform transcription
        transcription_result = await transcriber.transcribe_audio(
            audio_bytes=audio_bytes,
            language=language,
            task=task,
            return_timestamps=return_timestamps
        )
        
        return {
            "status": "success",
            "transcription": transcription_result
        }
        
    except Exception as e:
        logger.error(f"Error processing job: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


# Start the RunPod serverless worker
if __name__ == "__main__":
    logger.info("Starting RunPod serverless worker for Vexa Transcription Service")
    runpod.serverless.start({"handler": handler})
