const http = require('http');

var myPythonScriptPath = 'MozillaTTSLib/TTS/launch_tts.py';
const {PythonShell} = require('python-shell');

const port = 8083;

http.createServer(function(req, res)
{
	let body = '';
	req.on('data', chunk => { body += chunk });
	req.on('end', () => {
		let reqMessage = JSON.parse(body).message;
		console.log("[MSG]: Received request ("+reqMessage+")");
	
		var pyOptions = {
			mode: 'text',
			args: [reqMessage]
		};
	
		var pysh = new PythonShell(myPythonScriptPath, pyOptions);
	
		let result = '';
		pysh.on('message', function(message) {
			console.log(message);
			result += message;
		});
	
		pysh.end(function(err) {
			if(err){
				throw err;
			};
	
			res.write(result);
			res.end();
	
			console.log('Finished!');
		});
	});

}).listen(port);
