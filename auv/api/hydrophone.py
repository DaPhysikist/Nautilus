import sounddevice as sd
from scipy.io.wavfile import write
from datetime import datetime

class Hydrophone:
    def __init__(self):
        self.fs = 62000 # Sample rate
        self.audio_recording = None

    def start_record(self, recording_seconds):
        self.audio_recording = sd.rec(int(recording_seconds * self.fs), samplerate=self.fs, channels=2)
        sd.wait()
        self.save_recording()

    def save_recording(self):
        write(f'{datetime.now().isoformat()}.wav', self.fs, self.audio_recording)  # Save as WAV file 

    def get_most_recent_recording(self):
        return self.audio_recording

