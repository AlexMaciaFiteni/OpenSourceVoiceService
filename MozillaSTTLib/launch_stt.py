import pyaudio
import sys
from deepspeech import Model
import scipy.io.wavfile as wav
import wave

def record_audio(WAVE_OUTPUT_FILENAME):
	CHUNK = 1024
	FORMAT = pyaudio.paInt16
	CHANNELS = 1
	RATE = 16000
	RECORD_SECONDS = 5

	p = pyaudio.PyAudio()

	stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

	print("* recording "+ WAVE_OUTPUT_FILENAME)

	frames = [stream.read(CHUNK) for i in range(0, int(RATE / CHUNK * RECORD_SECONDS))]

	print("* done recording")

	stream.stop_stream()
	stream.close()
	p.terminate()

	wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
	wf.setnchannels(CHANNELS)
	wf.setsampwidth(p.get_sample_size(FORMAT))
	wf.setframerate(RATE)
	wf.writeframes(b''.join(frames))
	wf.close()


def deepspeech_predict(WAVE_OUTPUT_FILENAME):

	N_FEATURES = 25
	N_CONTEXT = 9
	BEAM_WIDTH = 500
	LM_ALPHA = 0.75
	LM_BETA = 1.85


	ds = Model('stt_models/deepspeech-0.9.3-models.pbmm')

	fs, audio = wav.read(WAVE_OUTPUT_FILENAME)
	return ds.stt(audio)

if __name__ == '__main__':
	# TODO: Controlar si hay argumento 1
	WAVE_OUTPUT_FILENAME = sys.argv[1]
	#record_audio(WAVE_OUTPUT_FILENAME)
	predicted_text = deepspeech_predict(WAVE_OUTPUT_FILENAME)
	print(predicted_text)
