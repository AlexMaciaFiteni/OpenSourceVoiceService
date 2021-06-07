const http = require('http');

module.exports = {
callTTS : function (reqMessage)
{
  return new Promise ((resolve, reject) => {
    const data = JSON.stringify({
      'message': reqMessage
    });
    
    const options = {
      hostname: 'localhost',
      port: 8083,
      path: '',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': data.length
      }
    };
    
    const req = http.request(options, res => {
      console.log(`statusCode: ${res.statusCode}`);
    
      res.on('data', d => {
        //process.stdout.write(d)
        //console.log();
        resolve(d);
      })
    });
    
    req.on('error', error => {
      console.error(error);
      reject(error);
    });
    
    req.write(data);
    req.end();
  });
}
}