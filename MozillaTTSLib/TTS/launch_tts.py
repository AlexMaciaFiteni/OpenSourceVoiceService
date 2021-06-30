import os
import sys
import io
import torch
from collections import OrderedDict

from TTS.models.tacotron import Tacotron
from TTS.layers import *
from TTS.utils.data import *
from TTS.utils.audio import AudioProcessor
from TTS.utils.generic_utils import load_config
from TTS.utils.text import text_to_sequence
from TTS.utils.synthesis import synthesis
from utils.text.symbols import symbols, phonemes
from TTS.utils.visual import visualize

# Set constants
MODEL_PATH = './tts_models/best_model.pth.tar'
CONFIG_PATH = './tts_models/config.json'
OUT_FILE = 'tts_out.wav'
CONFIG = load_config(CONFIG_PATH)
use_cuda = False

def tts(model, text, CONFIG, use_cuda, ap, OUT_FILE):
    waveform, alignment, spectrogram, mel_spectrogram, stop_tokens = synthesis(model, text, CONFIG, use_cuda, ap)
    ap.save_wav(waveform, OUT_FILE)
    return waveform

def load_model(MODEL_PATH, sentence, CONFIG, use_cuda, OUT_FILE):
	# load the model
	num_chars = len(phonemes) if CONFIG.use_phonemes else len(symbols)
	model = Tacotron(num_chars, CONFIG.embedding_size, CONFIG.audio['num_freq'], CONFIG.audio['num_mels'], CONFIG.r, attn_windowing=False)

	# load the audio processor
	# CONFIG.audio["power"] = 1.3
	CONFIG.audio["preemphasis"] = 0.97
	ap = AudioProcessor(**CONFIG.audio)

	# load model state
	if use_cuda:
		cp = torch.load(MODEL_PATH)
	else:
		cp = torch.load(MODEL_PATH, map_location=lambda storage, loc: storage)

	# load the model
	model.load_state_dict(cp['model'])
	if use_cuda:
		model.cuda()
	model.eval()

	model.eval()
	model.decoder.max_decoder_steps = 1000
	waveform = tts(model, sentence, CONFIG, use_cuda, ap, OUT_FILE)

if __name__ == '__main__':
	# TODO: Controlar si hay argumento 1
	sentence =  sys.argv[1]
	load_model(MODEL_PATH, sentence, CONFIG, use_cuda, OUT_FILE)
	print('finished')
