const http = require('http');

var myPythonScriptPath = 'MozillaSTTLib/launch_stt.py';
const {PythonShell} = require('python-shell');

const port = 8081;

http.createServer(function(req, res) {
	console.log("[MSG]: Received request");

	var pyOptions = {
		mode: 'text',
		args: ['./input/prueba_stt_mono.wav']
	};
	
	var pysh = new PythonShell(myPythonScriptPath, pyOptions);
	
	let result = '';
	pysh.on('message', function(message) {
		console.log("[MSG]: "+message);
		result += message;
	});
	
	pysh.end(function(err) {
		if(err){
			throw err;
		};
	
		res.write(result);
		res.end();
		console.log('Finished!');
	
		//require('child_process').fork('indexTTS.js');
	});


}).listen(port);

