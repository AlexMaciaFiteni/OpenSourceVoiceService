mkdir stt_models
cd stt_models
wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1q9HhT8IYx5sFEcADjtLLLZ_PsrrsyYQE' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1q9HhT8IYx5sFEcADjtLLLZ_PsrrsyYQE" -O modelo_stt.pbmm && rm -rf /tmp/cookies.txt
cd ..

mkdir tts_models
cd tts_models
wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1WXSmsl_eO4BGtJfah-nY8ARKDcsEwpW9' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1WXSmsl_eO4BGtJfah-nY8ARKDcsEwpW9" -O best_model.pth.tar && rm -rf /tmp/cookies.txt
wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1s7g4n-B73ChCB48AQ88_DV_8oyLth8r0' -O config.json
cd ..
