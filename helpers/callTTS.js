const http = require('http');

module.exports = {
callTTS : function (reqMessage)
{
  return new Promise ((resolve, reject) => {
    
    const options = {
      hostname: 'localhost',
      port: 8083,
      path: '',
      method: 'POST',
      headers: {
        'Content-Type': 'text/plain',
        'Content-Length': reqMessage.length
      }
    };
    
    const req = http.request(options, res => {
      if(res.statusCode != 200)
        console.log(`statusCode: ${res.statusCode}`);
    
      res.on('data', d => {
        resolve(d);
      })
    });
    
    req.on('error', error => {
      console.error(error);
      reject(error);
    });
    
    req.write(reqMessage);
    req.end();
  });
}
}