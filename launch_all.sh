echo "Lanzando index.js..."
nohup node index.js > index.out 2> index.err < /dev/null &
echo "Lanzando indexSTT.js..."
nohup node indexSTT.js > indexSTT.out 2> indexSTT.err < /dev/null &
echo "Lanzando indexTTS.js..."
nohup node indexTTS.js > indexTTS.out 2> indexTTS.err < /dev/null &
