const http = require('http');

var myPythonScriptPath = 'MozillaSTTLib/launch_stt.py';
const {PythonShell} = require('python-shell');

const port = 8081;

http.createServer(function(req, res)
{
	let body = '';
	req.on('data', chunk => { body += chunk });
	req.on('end', () => {
		console.log("[MSG]: Received request of "+body.length+" bytes");

		var pyOptions = {
			mode: 'text',
			args: ['./input/prueba_stt_mono.wav']
		};
		/*
		var pyOptions = { 
			mode: 'binary',
			args: [body]
		};
		*/
		
		var pysh = new PythonShell(myPythonScriptPath, pyOptions);
		
		let result = '';
		pysh.on('message', function(message) {
			console.log("[MSG]: "+message);
			result += message;
		});
		
		pysh.end(function(err) {
			if(err) { throw err; };
		
			res.write(result);
			//if(result=='') res.write('Hello there!');
			res.end();
			console.log('Finished!');
		});
	});

}).listen(port);

