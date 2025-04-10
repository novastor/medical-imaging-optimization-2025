
from openai import OpenAI
import os
from dotenv import load_dotenv
import sounddevice as sd
from scipy.io.wavfile import write
def audio_capture(filename):

    fs = 44100
    seconds = 5
    recording = sd.rec(int(seconds * fs), samplerate=fs, channels=2)
    sd.wait()
    output = str(filename)+'.wav'
    write(output,fs,recording)
def audio_mockup(filename):
    return "mockup.txt"
def audio_processing(filename):
        """
        audio file processing and text generation function 
        returns .txt file
        """
    
        audio_file_path = filename

        # Remove quotation marks from the file path if present
        audio_file_path = audio_file_path.strip('\"')

        # Ask user for the desired response format (text or vtt)
        response_format ='text'

        # load env keys
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        # If the API key is not provided as an environment variable, ask the user to input it
        if not api_key:
            api_key = input("Enter your OpenAI API key: ")

        # Initialize 
        client = OpenAI(api_key=api_key)

        # handle file buffer to do dynamic reading
        with open(audio_file_path, "rb") as audio_file:
            # Perform speech-to-text transcription
            print('transcribing')
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format=response_format
            )

        print("recording complete")
        return transcript