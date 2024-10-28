from io import BytesIO
import os
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')

openai = OpenAI(api_key=openai_api_key)

from openai import OpenAI
client = OpenAI()

desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "AudioFiles")

async def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
    return transcription.text

async def classify_conversion(transcription: str) -> list:
    lines = transcription.split('. ')

    conversation = []

    for line in lines:
        line = line.strip()
        if line:
            if "나" in line or "내" in line:
                conversation.append({"role"})
            else :
                conversation.append({"role": "assistant", "content" : line})