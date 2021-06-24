const http = require('http');
const port = 8080;

const callSTT = require('./helpers/callSTT.js').callSTT;
const callTTS = require('./helpers/callTTS.js').callTTS;
const callNLU = require('./helpers/callNLU.js').callNLU;

http.createServer(function(req, res)
{
	let body = Buffer.alloc(0);
	req.on('data', buffer => {
    body = Buffer.concat([body, buffer], body.length + buffer.length) 
  });

	req.on('end', () => {
    console.log('Request fully received: ' + body.length);

    callSTT('Useless parameter').then((msgstt) =>
    {
      console.log("To process: ["+msgstt+"]");

      msgstt = 'Hi there!'; // TODO:: Don't override
      callNLU(msgstt).then((msgnlu) =>
      {
        console.log('Chatbot said: '+msgnlu);
        
        msgnlu = 'This is a test sentence haha'; // TODO:: Don't override
        callTTS(msgnlu).then((msgtts) =>
        {
          console.log("TTS finished, check the output file");

        }).catch((msgerr) => {console.log(msgerr)});
      }).catch((msgerr) => {console.log(msgerr)});
    }).catch((msgerr) => {console.log(msgerr)});

  });
}).listen(port);
