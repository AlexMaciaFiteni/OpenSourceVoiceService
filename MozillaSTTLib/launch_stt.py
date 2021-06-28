import sys
import itertools
from deepspeech import Model
import scipy.io.wavfile as wav

def resampleSimplified(pcm, desired_samples, original_samples, dataFormat):

    samples_to_pad = desired_samples - original_samples

    q, r = divmod(desired_samples, original_samples)
    times_to_pad_up = q + int(bool(r))
    times_to_pad_down = q

    pcmList = [pcm[i:i+dataFormat] for i in range(0, len(pcm), dataFormat)]

    if samples_to_pad > 0:
        # extending pcm times_to_pad times
        pcmListPadded = list(itertools.chain.from_iterable(
            itertools.repeat(x, times_to_pad_up) for x in pcmList)
            )
    else:
        # shrinking pcm times_to_pad times
        if times_to_pad_down > 0:
            pcmListPadded = pcmList[::(times_to_pad_down)]
        else:
            pcmListPadded = pcmList

    padded_pcm = ''.join(pcmListPadded[:desired_samples])

    return padded_pcm

def deepspeech_predict(wav_filename):

	N_FEATURES = 25
	N_CONTEXT = 9
	BEAM_WIDTH = 500
	LM_ALPHA = 0.75
	LM_BETA = 1.85

	ds = Model('stt_models/deepspeech-0.9.3-models.pbmm')

	fs, audio = wav.read(wav_filename)
	#resampled = resampleSimplified(audio, ds.sampleRate(), 8000, 4)
	return ds.stt(audio)

if __name__ == '__main__':
	wav_filename = './input/prueba_stt_mono.wav'#sys.argv[1]
	#audio_input = sys.stdin.buffer.read()
	predicted_text = deepspeech_predict(wav_filename)
	print(predicted_text) # Text output captured by NodeJS
