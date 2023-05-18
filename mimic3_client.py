#!/usr/bin/python3.10
import sys
import requests
import subprocess
import io

def say(text):
    base_url = "http://localhost:59125/api/tts"
    params = { 'text': text, "lengthScale": "0.6" }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        audio_data = io.BytesIO(response.content)
        audio_bytes = audio_data.read()
        # Pass the audio data to gstreamer-1.0 for playback
        command = ['gst-launch-1.0', '-q', 'fdsrc', '!', 'wavparse', '!', 'autoaudiosink']
        subprocess.run(command, input=audio_bytes, check=True,
        stdout=subprocess.DEVNULL)
    else:
        print("Error:", response.status_code)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        say(sys.argv[1])
    else:
        print("Import say from mimic3_client or test with `mimic3_client 'this is a test'`")
