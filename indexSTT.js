var myPythonScriptPath = 'MozillaSTTLib/launch_stt.py';
const {PythonShell} = require('python-shell');

var pyOptions = {
	mode: 'text',
	args: ['./input/prueba_stt_mono.wav']
};

var pysh = new PythonShell(myPythonScriptPath, pyOptions);

pysh.on('message', function(message) {
	console.log("[MSG]: "+message);
});

pysh.end(function(err) {
	if(err){
		throw err;
	};

	console.log('Finished!');

	require('child_process').fork('indexTTS.js');
});
