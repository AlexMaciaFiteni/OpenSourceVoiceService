TMPDATE=`date +%F-%T`
LOGFLD=logs

CMD_VS="node index.js"
CMD_ASR="node indexSTT.js"
CMD_TTS="node indexTTS.js"
CMD_NLP="rasa run --enable-api -p 8082"

mkdir -p ${LOGFLD}

echo "Lanzando todo, fecha = "${TMPDATE}
echo "Lanzando index.js..."
nohup ${CMD_VS} > ${LOGFLD}/${TMPDATE}-index.out 2> ${LOGFLD}/${TMPDATE}-index.err < /dev/null &
echo "Lanzando indexSTT.js..."
nohup ${CMD_ASR} > ${LOGFLD}/${TMPDATE}-stt.out 2> ${LOGFLD}/${TMPDATE}-stt.err < /dev/null &
echo "Lanzando indexTTS.js..."
nohup ${CMD_TTS} > ${LOGFLD}/${TMPDATE}-tts.out 2> ${LOGFLD}/${TMPDATE}-tts.err < /dev/null &
echo "Lanzando Rasa..."
cd Rasa
nohup ${CMD_NLP} > ../${LOGFLD}/${TMPDATE}-nlp.out 2> ../${LOGFLD}/${TMPDATE}-nlp.err < /dev/null &
cd ..