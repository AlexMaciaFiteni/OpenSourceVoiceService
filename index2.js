const fs = require('fs');
const outputFilepath = './tts_out.wav';
const callTTS = require('./helpers/callTTS.js').callTTS;
      
let msgnlu = "Hola que tal amigo";
callTTS(msgnlu).then((msgtts) =>
{
  print("Finished!!!");
}).catch((msgerr) => {console.log(msgerr)});

