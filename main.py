# Inbound Calling Agent with Twilio & Qwen 2.5 Max (v1)
# Created by @jasmineraj2005

from fastapi import FastAPI, Request
from twilio.twiml.voice_response import VoiceResponse, Connect 
import requests 
import json 
import boto3 
from google.cloud import speech_v1p1beta1 as speech 

# fastapi intialization 
app = FastAPI()

# Google Cloud Speech to Text (STT Model)
def transcribe_audio(audio_data):
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_data)

    config = speech.RecogmitionConfig(
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16, 
        sample_rate_hertz = 8000,
        language_code = "en-US"
    )

    response = client.recognize(config=config, audio=audio)
    return response.results[0].alternatives[0].transcript

# Qwen 2.5 Max API request
def generate_response(user_input):
    QWEN_API_URL = "****" #add
    QWEN_API_KEY = "sk-10d0ff58eda749dbbb1d13a6f9ec6c63"

    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "prompt": user_input,
        "max_tokens": 100,
        "temperature": 0.7
    }

    response = requests.post(QWEN_API_URL, json = data, headers = headers)
    return response.json() ["output"]["text"]

# Amazon Polly Service for Text to Speech (TTS Model)

def text_to_speech(text):
    polly = boto3.client("polly", region_name = "ap-southeast-2") #sydney

    response = polly.synthesize_speech(
        Text = text,
        OutputFormat = "pcm",
        VoiceId = "Nicole" #Female Aussie
    )

    return response["AudioStream"].read()

# Route to handle incoming call and stream audio

@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    response = VoiceResponse()
    response.say("Hello, how can I assit you today.")
    connect = Connect()
    connect.stream(url="****") #replace by ngrok link
    response.append(connect)

    return str(response)

# Route to handle media stream and audio processing 

@app.websocket("/media-stream")
async def handle_media_stream(websocket):
    await websocket.accpet()

    async for message in websocket.iter_text():
        data = json.loads(message)

        if data['event'] == 'media':
            audio_data = data['media']['payload']
            transcribe_text = transcribe_audio(audio_data)

            qwen_response = generate_response(transcribe_text)
            audio_response = text_to_speech(qwen_response)
            audio_base64 = text_to_speech(qwen_response)
            await websocket.sen_json({
                "event": "media",
                "media": {
                    "payload": audio_base64
                }
            })
    await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    




