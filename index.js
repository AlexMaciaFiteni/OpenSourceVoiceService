const fs = require('fs');
const http = require('http');
const port = 8080;

const outputFilepath = './tts_out.wav';

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
		let access_time = Date.now();
    console.log('Request fully received: ' + body.length);

    callSTT(body).then((msgstt) =>
    {
      console.log("To process: ["+msgstt+"]");

      // TODO:: Don't override
      msgstt = 'Hi there!'; console.log(" > Overriding to ["+msgstt+"]");
      callNLU(msgstt).then((msgnlu) =>
      {
        let parsed = JSON.parse(msgnlu);
        msgnlu = parsed[0].text;
        console.log('Chatbot said: ['+msgnlu+"]");
        
        callTTS(msgnlu).then((msgtts) =>
        {
			    console.log('Finished! (in'+(Date.now() - access_time)+' ms)');
          const readStream = fs.createReadStream(outputFilepath);
          readStream.pipe(res);

        }).catch((msgerr) => {console.log(msgerr)});
      }).catch((msgerr) => {console.log(msgerr)});
    }).catch((msgerr) => {console.log(msgerr)});

  });
}).listen(port);
