# Inbound Calling Agent with Twilio & Qwen 2.5 Max (v1)
# Created by @jasmineraj2005

from fastapi import FastAPI, Request
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.rest import Client
import requests
import json
from google.cloud import speech_v1p1beta1 as speech
import os
from dotenv import load_dotenv
import base64
import time

# Load environment variables
load_dotenv()

# FastAPI initialization
app = FastAPI()

# Twilio Client Setup
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Routes to handle incoming call and stream audio
@app.get("/")
def read_root():
    start_time = time.time()
    response = {"message": "Welcome to the AI Voice System!"}
    end_time = time.time()
    print(f"Root route response time: {end_time - start_time} seconds")
    return response

@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    response = VoiceResponse()
    response.say("Hello, how can I assist you today.")
    connect = Connect()

    # Use the CODESPACE_URL environment variable or fallback to local URL
    BASE_URL = os.getenv("CODESPACE_URL", "http://localhost:8000")
    connect.stream(url=f"{BASE_URL}/media-stream")  # Stream URL for media processing
    response.append(connect)

    return str(response)

@app.websocket("/media-stream")
async def handle_media_stream(websocket):
    await websocket.accept()

    async for message in websocket.iter_text():
        data = json.loads(message)

        if data['event'] == 'media':
            audio_data = data['media']['payload']
            transcribe_text = transcribe_audio(audio_data)

            # Use Qwen or OpenAI (can switch between them using `model` argument)
            refined_text = generate_response(transcribe_text, model="qwen", emotion="happy")  # Set emotion (e.g., "happy", "sad", "neutral")

            # Convert the refined text to speech using 11 Labs TTS
            audio_response = text_to_speech(refined_text, emotion="happy")  # This now uses 11 Labs TTS and emotion

            # Send back audio in base64 format
            audio_base64 = base64.b64encode(audio_response).decode('utf-8')

            await websocket.send_json({
                "event": "media",
                "media": {
                    "payload": audio_base64
                }
            })
    await websocket.close()

# Route to make a call to a given number
@app.post("/make-call")
async def make_call(request: Request):
    data = await request.json()
    to = data.get("to")

    if not to:
        return {"error": "Phone number is required"}

    # Initiate the call using Twilio's REST API
    try:
        call = client.calls.create(
            to=to,  # The phone number to dial
            from_=TWILIO_PHONE_NUMBER,  # Your Twilio number
            url="http://demo.twilio.com/docs/voice.xml"  # This XML file is for a simple voice response
        )
        return {"message": "Call initiated", "sid": call.sid}
    except Exception as e:
        return {"error": str(e)}

# Helper functions for speech-to-text and text-to-speech (as defined earlier)

# Google Cloud Speech to Text (STT Model)
def transcribe_audio(audio_data):
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_data)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=8000,
        language_code="en-US"
    )

    response = client.recognize(config=config, audio=audio)
    return response.results[0].alternatives[0].transcript

# Unified API function for OpenAI or Qwen
def generate_response(user_input, model="qwen", emotion="neutral"):
    if model == "openai":
        return f"OpenAI response for: {user_input} with emotion: {emotion}"
    elif model == "qwen":
        QWEN_API_URL = os.getenv("QWEN_API_URL")
        QWEN_API_KEY = os.getenv("QWEN_API_KEY")
        if not QWEN_API_KEY:
            raise EnvironmentError("Environment variable 'QWEN_API_KEY' is not defined. Please check your .env file.")

        headers = {
            "Authorization": f"Bearer {QWEN_API_KEY}",
            "Content-Type": "application/json"
        }

        emotional_prompt = f"Respond with a {emotion} tone and include conversational gestures like 'ahh', 'wow', 'hmm', 'yay', etc when appropriate: {user_input}"

        data = {
            "prompt": emotional_prompt,
            "max_tokens": 100,
            "temperature": 0.7
        }

        response = requests.post(QWEN_API_URL, json=data, headers=headers)
        return response.json()["output"]["text"]
    else:
        raise ValueError("Invalid model specified, Use 'openai' or 'qwen'.")

# 11 Labs (TTS Model)
def text_to_speech(text, emotion="neutral"):
    ELEVEN_LABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/generate"
    ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")

    headers = {
        "Authorization": f"Bearer {ELEVEN_LABS_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "text": text,
        "voice": "en-au-female",  # Australian female voice
        "emotion": emotion
    }

    response = requests.post(ELEVEN_LABS_API_URL, json=data, headers=headers)

    if response.status_code == 200:
        audio_content = response.content
        return audio_content
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
