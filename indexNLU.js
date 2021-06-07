const http = require('http');

const data = JSON.stringify({
	'sender': 'test_user',
	'message': 'Hi there!'
});

const options = {
  hostname: 'localhost',
  port: 5005,
  path: '/webhooks/rest/webhook',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': data.length
  }
};

const req = http.request(options, res => {
  console.log(`statusCode: ${res.statusCode}`)

  res.on('data', d => {
    process.stdout.write(d)
	  console.log();
  })
});

req.on('error', error => {
  console.error(error)
});

req.write(data);
req.end();
