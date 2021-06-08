const http = require('http');

module.exports = {
callNLU : function (reqMessage)
{
  return new Promise ((resolve, reject) => {
    const data = JSON.stringify({
      'sender': 'test_user',
      'message': reqMessage
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
      if(res.statusCode != 200)
        console.log(`statusCode: ${res.statusCode}`)
    
      res.on('data', d => {
        resolve(d);
      })
    });
    
    req.on('error', error => {
      console.error(error)
      reject(error);
    });
    
    req.write(data);
    req.end();
  });
}
}