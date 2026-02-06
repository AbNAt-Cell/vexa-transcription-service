"""
Test script for RunPod handler (local testing)

This script allows you to test the handler locally before deploying to RunPod.
"""

import asyncio
import base64
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from handler import handler


async def test_handler():
    """Test the handler with a sample audio file."""
    
    print("RunPod Handler Test Script")
    print("=" * 50)
    
    # Option 1: Test with a local audio file
    test_audio_path = input("\nEnter path to test audio file (or press Enter to test with URL): ").strip()
    
    if test_audio_path:
        # Test with local file
        audio_path = Path(test_audio_path)
        if not audio_path.exists():
            print(f"Error: File not found: {audio_path}")
            return
        
        print(f"\nReading audio file: {audio_path}")
        with open(audio_path, 'rb') as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode()
        
        print(f"Audio size: {len(audio_bytes)} bytes")
        print(f"Base64 size: {len(audio_base64)} characters")
        
        job_input = {
            "input": {
                "audio": audio_base64,
                "language": "en",
                "return_timestamps": True
            }
        }
    else:
        # Test with URL
        test_url = input("Enter audio URL (or use default test URL): ").strip()
        if not test_url:
            test_url = "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars60.wav"
        
        job_input = {
            "input": {
                "audio_url": test_url,
                "language": "en",
                "return_timestamps": True
            }
        }
        
        print(f"\nUsing audio URL: {test_url}")
    
    print("\n" + "=" * 50)
    print("Processing transcription...")
    print("=" * 50)
    
    # Call handler
    result = await handler(job_input)
    
    print("\n" + "=" * 50)
    print("RESULT")
    print("=" * 50)
    
    if result.get("status") == "success":
        print("\n✅ Success!")
        transcription = result.get("transcription", {})
        
        print(f"\nLanguage: {transcription.get('language', 'unknown')}")
        print(f"\nFull Text:\n{transcription.get('text', '')}")
        
        segments = transcription.get('segments', [])
        if segments:
            print(f"\n\nSegments ({len(segments)} total):")
            for i, segment in enumerate(segments[:5]):  # Show first 5
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                text = segment.get('text', '')
                print(f"  [{start:.2f}s - {end:.2f}s]: {text}")
            
            if len(segments) > 5:
                print(f"  ... and {len(segments) - 5} more segments")
    else:
        print("\n❌ Error!")
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(test_handler())
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
