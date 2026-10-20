import { mkdir, readFile, writeFile, rm } from 'node:fs/promises';
// Bundle the three dependency-free modules into one portable offline HTML file.
await rm('dist',{recursive:true,force:true});
await mkdir('dist',{recursive:true});
const [html,css,engine,art,app] = await Promise.all(['index.html','src/style.css','src/engine.mjs','src/art.js','src/app.js'].map(file=>readFile(file,'utf8')));
const script = [engine.replace(/^export /gm,''),art.replace(/^export /gm,''),app.replace(/^import .*;\n/gm,'')].join('\n');
const bundled = html.replace('<link rel="stylesheet" href="./src/style.css">',`<style>${css}</style>`).replace('<script type="module" src="./src/app.js"></script>',`<script type="module">${script}</script>`);
await writeFile('dist/index.html',bundled);
console.log(`Built dist/index.html (${Buffer.byteLength(bundled)} bytes), no runtime dependencies or network requests.`);
