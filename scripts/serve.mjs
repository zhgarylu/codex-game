import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
const root = resolve(process.argv.includes('--dist') ? 'dist' : '.');
const port = Number(process.env.PORT || 4173);
const types = { '.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.json':'application/json' };
const server = http.createServer(async (request,response) => {
  try {
    const path = decodeURIComponent(new URL(request.url,'http://localhost').pathname);
    const target = resolve(root,'.' + path);
    if (target !== root && !target.startsWith(root + sep)) { response.writeHead(403);response.end('Forbidden');return; }
    const info = await stat(target);
    const file = info.isDirectory() ? resolve(target,'index.html') : target;
    const relative = file.slice(root.length + 1);
    if (relative.split(/[\\/]/).some(part=>part.startsWith('.')) || /^(tests|scripts|artifacts)(\/|$)/.test(relative) || /^(package.*\.json|README\.md)$/.test(relative)) { response.writeHead(403);response.end('Forbidden');return; }
    response.writeHead(200,{'Content-Type':types[extname(file)]||'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}); response.end(await readFile(file));
  } catch { response.writeHead(404); response.end('Not found'); }
});
server.listen(port,'0.0.0.0',()=>console.log(`RAMEN GATE ready: http://localhost:${port} (local environment only)`));
