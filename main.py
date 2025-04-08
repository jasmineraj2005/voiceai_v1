# Inbound Calling Agent with Twilio & Qwen 2.5 Max (v1)
# Created by @jasmineraj2005

from fastapi import FastAPI, Request
from twilio.twiml.voice_response import VoiceResponse, Connect 
import requests 
import json 
from google.cloud import speech_v1p1beta1 as speech 
import os
from dotenv import load_dotenv

load_dotenv()

# fastapi intialization 
app = FastAPI()

# Google Cloud Speech to Text (STT Model)
def transcribe_audio(audio_data):
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_data)

    config = speech.RecognitionConfig(
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16, 
        sample_rate_hertz = 8000,
        language_code = "en-US"
    )

    response = client.recognize(config=config, audio=audio)
    return response.results[0].alternatives[0].transcript

# Unified API function 
def generate_response(user_input, model = "qwem", emotion = "neutral"): 
    """
    Unified function to call OpenAI or Qwen API based on 'model' argument.
    Default is Qwen. 

    :param user_input: Input text to generate a response for. 
    :param model: The model to use ("openai" or "qwen").
    :param emotion: The emotion to convey("happy", "sad", "neutral", etc.)
    :return: Generated text response.
    """

    if model == "openai":
        # Placeholder for OpenAI response generation logic
        return f"OpenAI response for: {user_input} with emotion: {emotion}"
    elif model == "qwen":
        # Placeholder for Qwen response generation logic
        return f"Qwen response for: {user_input} with emotion: {emotion}"
    else: raise ValueError("Invalis model specified, Use 'openai' or 'qwen'.")
  
# Qwen 2.5 Max API request
def generate_response(user_input, emotion="neutral"):
    QWEN_API_URL = os.getenv("QWEN_API_URL")
    QWEN_API_KEY = os.getenv("QWEN_API_KEY")
    if not QWEN_API_KEY:
        raise EnvironmentError("Environment variable 'QWEN_API_KEY' is not defined. Please check your .env file.")

    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }

    emotional_promopt = f"Respond with a {emotion} tone and include conversational gestures like 'ahh', 'wow', 'hmm', 'yay', etc when appropriate: {user_input}"

    data = {
        "prompt": emotional_promopt,
        "max_tokens": 100,
        "temperature": 0.7
    }

    response = requests.post(QWEN_API_URL, json = data, headers = headers)
    return response.json() ["output"]["text"]

# 11 Labs (TTS Model)
def text_to_speech(text, emotion="neutral"):
    ELEVEN_LABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/generate"
    ELEVEN_LABS_API_KEY = os.getenv(" ELEVEN_LABS_API_KEY")

    headers = {
        "Authorization": f"Bearer { ELEVEN_LABS_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "text": text, 
        "voice": "en-au-female", 
        "emotion": emotion
    }

    response = requests.post(ELEVEN_LABS_API_URL, json = data, headers = headers)

    if response.status_code == 200:
        audio_content = response.content 
        return audio_content 
    else: 
        raise Exception(f"Error: {response.status_code}, {response.text}")

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

           # Use Qwen or OpenAI (can switch between them using `model` argument)
            refined_text = generate_response(transcribe_text, model="qwen", emotion="happy")  # Set emotion (e.g., "happy", "sad", "neutral")

            # Convert the refined text to speech using 11 Labs TTS
            audio_response = text_to_speech(refined_text, emotion="happy")  # This now uses 11 Labs TTS and emotion

            # Send back audio in base64 format (if required, can be adjusted)
            audio_base64 = audio_response.encode("base64")  # This is just for illustration; adjust as necessary

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
    




