import sys
import numpy
from deepspeech import Model

def load_deepspeech_model():
	N_FEATURES = 25
	N_CONTEXT = 9
	BEAM_WIDTH = 500
	LM_ALPHA = 0.75
	LM_BETA = 1.85

	return Model('stt_models/deepspeech-0.9.3-models.pbmm')

if __name__ == '__main__':
	audio_input = sys.stdin.buffer.read()
	model = load_deepspeech_model()
	predicted_text = model.stt(numpy.frombuffer(buffer=audio_input, dtype=numpy.int16))
	print(predicted_text) # Text output captured by NodeJS
