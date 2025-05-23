import requests
import json

# Base URL of your API
BASE_URL = "http://localhost:5000"

# Example 1: Simple TTS request (returns audio file)
def simple_tts():
    """Convert simple text to speech and download the audio file"""
    payload = {
        "text": "Hello, this is a test of the text-to-speech API."
    }
    
    response = requests.post(f"{BASE_URL}/tts", json=payload)
    
    if response.status_code == 200:
        # Save the audio file
        with open("output.wav", "wb") as f:
            f.write(response.content)
        print("Audio saved as output.wav")
    else:
        print(f"Error: {response.json()}")

# Example 2: Multi-speaker conversation
def multi_speaker_tts():
    """Convert a conversation with multiple speakers"""
    payload = {
        "text": """Joe: How's it going today Jane?
                   Jane: Not too bad, how about you?
                   Joe: Pretty good, thanks for asking!""",
        "speakers": [
            {"name": "Joe", "voice": "Kore"},
            {"name": "Jane", "voice": "Puck"}
        ],
        "save_to_disk": True,
        "filename": "conversation.wav"
    }
    
    response = requests.post(f"{BASE_URL}/tts", json=payload)
    
    if response.status_code == 200:
        print("Response:", response.json())
    else:
        print(f"Error: {response.json()}")

# Example 3: Process text in chunks
def chunked_tts():
    """Process long text in chunks"""
    payload = {
        "chunks": [
            "This is the first part of a long text.",
            "This is the second part that continues the story.",
            "And finally, this is the last part of our text."
        ],
        "speakers": [
            {"name": "Narrator", "voice": "Sage"}
        ]
    }
    
    response = requests.post(f"{BASE_URL}/tts/stream", json=payload)
    
    if response.status_code == 200:
        print("Response:", json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.json()}")

# Example 4: Get available voices
def get_voices():
    """Get list of available voices"""
    response = requests.get(f"{BASE_URL}/voices")
    
    if response.status_code == 200:
        print("Available voices:", response.json())
    else:
        print(f"Error: {response.json()}")

if __name__ == "__main__":
    # Run examples
    print("1. Simple TTS example:")
    simple_tts()
    
    print("\n2. Multi-speaker conversation:")
    multi_speaker_tts()
    
    print("\n3. Chunked text processing:")
    chunked_tts()
    
    print("\n4. Available voices:")
    get_voices()
