var myPythonScriptPath = 'MozillaTTSLib/TTS/launch_tts.py';
const {PythonShell} = require('python-shell');

var pyOptions = {
	mode: 'text',
	args: ['This is a test sentence']
};

var pysh = new PythonShell(myPythonScriptPath, pyOptions);

pysh.on('message', function(message) {
	console.log(message);
});

pysh.end(function(err) {
	if(err){
		throw err;
	};

	console.log('Finished!');
});
