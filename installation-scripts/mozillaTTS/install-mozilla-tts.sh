# Clone repository and get to desired branch
git clone https://github.com/mozilla/TTS.git 
cd TTS 
git checkout db7f3d3

# Install the package and dependencies
python3 setup.py develop
pip install -e .
sudo apt-get install espeak #optional?

# Add download to folder: tts_model

# Run the example
python3 test_tts.py
