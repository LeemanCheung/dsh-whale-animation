// A dependency-free static server. Run: node server.mjs
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readFile, stat } from 'node:fs/promises';
const root=path.dirname(fileURLToPath(import.meta.url));
const port=Number(process.env.PORT||3000);
const mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.ico':'image/x-icon'};
http.createServer(async(req,res)=>{
  try{
    let p=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    const full=path.resolve(root,'.'+p);
    if(full!==root&&!full.startsWith(root+path.sep)){res.writeHead(403);res.end('Forbidden');return;}
    let file=full;if((await stat(file)).isDirectory())file=path.join(file,'index.html');
    const body=await readFile(file);
    res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-cache'});res.end(body);
  }catch{res.writeHead(404,{'Content-Type':'text/plain; charset=utf-8'});res.end('Not found');}
}).listen(port,'0.0.0.0',()=>console.log(`NOCTURNE — http://localhost:${port}`));
