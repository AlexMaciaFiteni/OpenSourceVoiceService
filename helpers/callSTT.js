const http = require('http');

module.exports = {
callSTT : function (reqMessage)
{
  return new Promise ((resolve, reject) => {
    const options = {
      hostname: 'localhost',
      port: 8081,
      path: '',
      method: 'POST',
      headers: {
        'Content-Type': 'application/octet-stream',
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