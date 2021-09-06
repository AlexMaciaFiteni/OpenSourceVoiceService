const http = require('http');

var myPythonScriptPath = 'MozillaSTTLib/launch_stt.py';
const {PythonShell} = require('python-shell');

const port = 8081;

http.createServer(function(req, res)
{
	let body = Buffer.alloc(0);
	req.on('data', chunk => { 
		body = Buffer.concat([body, chunk], body.length + chunk.length)
	});
	req.on('end', () => {
		let access_time = Date.now();
		console.log("[MSG]: Received request of "+body.length+" bytes");

		var pysh = new PythonShell(myPythonScriptPath, { mode:'binary' });
		pysh.send(body);
		
		let result = '';
		pysh.stdout.on('data', function(message) {
			console.log("[MSG]: "+message.toString());
			result += message.toString();
		});
		
		pysh.end(function(err) {
			if(err) { throw err; };
		
			res.write(result);
			res.end();
			console.log('Finished! (in'+(Date.now() - access_time)+' ms)');
		});
	});

}).listen(port);

