# Start rasa voice service
cd rasa-voice-interface
npm run serve

# Start Rasa server
rasa run --enable-api -p 5005

# Start Rasa's custom action server
rasa run actions --actions actions.actions

# Start DucklingHTTPExtractor (an external component)
sudo docker run -p 8000:8000 rasa/duckling

# Start a server
python3 -m http.server 8888

