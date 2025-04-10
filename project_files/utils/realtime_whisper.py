from openai import OpenAI
import io
from dotenv import load_dotenv
import os


def audio_processing(file_buffer, filename="audio.webm"):
    """
    Transcribes an audio file using whisper-1 and returns the detected text.
    """
    # Reset the file buffer so we read from the beginning.
    file_buffer.seek(0)
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    client = OpenAI(api_key=api_key)

    # Determine the MIME type based on the file extension. this helps to run on more browsers and potentially on mobile(needs further testing)
    if filename.lower().endswith(".ogg"):
        mime_type = "audio/ogg"
    elif filename.lower().endswith(".wav"):
        mime_type = "audio/wav"
    else:
        mime_type = "audio/webm"

    # Create transcription using the audio file.
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, file_buffer, mime_type)
    )
    
    print(transcript)
    print("Recording complete")
    return transcript
