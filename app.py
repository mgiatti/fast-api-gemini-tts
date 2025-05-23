from flask import Flask, request, jsonify, send_file
from google import genai
from google.genai import types
import wave
import os
import io
import json
import uuid
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Get API key from environment variable
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

# Initialize the client
client = genai.Client(api_key=GEMINI_API_KEY)

# Directory to save audio files (if saving to disk)
AUDIO_OUTPUT_DIR = os.environ.get('AUDIO_OUTPUT_DIR', '/app/audio_output')
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

def create_wave_file(pcm_data, channels=1, rate=24000, sample_width=2):
    """Create a wave file in memory from PCM data"""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)
    buffer.seek(0)
    return buffer

def save_wave_file(filename, pcm_data, channels=1, rate=24000, sample_width=2):
    """Save PCM data to a wave file on disk"""
    filepath = os.path.join(AUDIO_OUTPUT_DIR, filename)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)
    return filepath

def parse_speaker_configs(speakers_data):
    """Parse speaker configuration from request data"""
    speaker_configs = []
    for speaker in speakers_data:
        speaker_configs.append(
            types.SpeakerVoiceConfig(
                speaker=speaker['name'],
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=speaker['voice']
                    )
                )
            )
        )
    return speaker_configs

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "TTS API"})

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """
    Convert text to speech
    
    Request body:
    {
        "text": "Your text here",
        "speakers": [
            {"name": "Speaker1", "voice": "Kore"},
            {"name": "Speaker2", "voice": "Puck"}
        ],
        "save_to_disk": false,  # Optional, default false
        "filename": "custom_name.wav"  # Optional
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' in request body"}), 400
        
        text = data['text']
        speakers = data.get('speakers', [])
        save_to_disk = data.get('save_to_disk', False)
        custom_filename = data.get('filename', None)
        
        # Prepare the configuration
        config_params = {
            "response_modalities": ["AUDIO"]
        }
        
        # Add multi-speaker configuration if speakers are provided
        if speakers:
            speaker_configs = parse_speaker_configs(speakers)
            config_params["speech_config"] = types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=speaker_configs
                )
            )
        
        # Generate audio
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(**config_params)
        )
        
        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        
        if save_to_disk:
            # Save to disk and return file info
            if custom_filename:
                filename = custom_filename
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                filename = f"tts_{timestamp}_{unique_id}.wav"
            
            filepath = save_wave_file(filename, audio_data)
            
            return jsonify({
                "message": "Audio saved successfully",
                "filename": filename,
                "path": filepath,
                "size": os.path.getsize(filepath)
            })
        else:
            # Return the audio file directly
            audio_buffer = create_wave_file(audio_data)
            return send_file(
                audio_buffer,
                mimetype='audio/wav',
                as_attachment=True,
                download_name='tts_output.wav'
            )
            
    except Exception as e:
        logging.error(f"Error in TTS processing: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/tts/stream', methods=['POST'])
def text_to_speech_chunked():
    """
    Process text in chunks for longer content
    
    Request body:
    {
        "chunks": ["chunk1", "chunk2", ...],
        "speakers": [...],  # Optional
        "merge": true  # Optional, whether to merge chunks into one file
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'chunks' not in data:
            return jsonify({"error": "Missing 'chunks' in request body"}), 400
        
        chunks = data['chunks']
        speakers = data.get('speakers', [])
        merge = data.get('merge', False)
        
        audio_files = []
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            config_params = {
                "response_modalities": ["AUDIO"]
            }
            
            if speakers:
                speaker_configs = parse_speaker_configs(speakers)
                config_params["speech_config"] = types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=speaker_configs
                    )
                )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=chunk,
                config=types.GenerateContentConfig(**config_params)
            )
            
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tts_chunk_{i}_{timestamp}.wav"
            filepath = save_wave_file(filename, audio_data)
            
            audio_files.append({
                "chunk_index": i,
                "filename": filename,
                "path": filepath,
                "size": os.path.getsize(filepath)
            })
        
        return jsonify({
            "message": "All chunks processed successfully",
            "audio_files": audio_files,
            "total_chunks": len(chunks)
        })
        
    except Exception as e:
        logging.error(f"Error in chunked TTS processing: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/voices', methods=['GET'])
def list_voices():
    """List available voice names"""
    # Common Google TTS voices
    voices = [
        "Kore", "Puck", "Charon", "Krypton", "Fenrir",
        "Aoede", "Orpheus", "Pegasus", "Sage", "Tamara"
    ]
    return jsonify({"available_voices": voices})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
