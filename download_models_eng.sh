mkdir -p stt_models
cd stt_models
wget https://github.com/mozilla/DeepSpeech/releases/download/v0.9.3/deepspeech-0.9.3-models.pbmm
wget https://github.com/mozilla/DeepSpeech/releases/download/v0.9.3/deepspeech-0.9.3-models.scorer
cd ..

mkdir -p tts_models
cd tts_models
wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1I8m6fIJTzQ3UkayhAVQAXgpWXLAcSLFY' -O best_model_en.pth.tar
wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1pr0UHD7YKs3BIhf9UO4xsDW1wyiIZF8J' -O config_en.json
cd ..
