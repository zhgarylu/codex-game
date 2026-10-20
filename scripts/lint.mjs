import { readdir, readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
// Dependency-free syntax and repository hygiene checks (not ESLint).
for (const directory of ['src','scripts','tests']) {
  for (const file of await readdir(directory)) {
    if (!/\.(m?js)$/.test(file)) continue;
    const path = `${directory}/${file}`, check = spawnSync(process.execPath,['--check',path],{encoding:'utf8'});
    assert.equal(check.status,0,`${path}: ${check.stderr}`);
    const source = await readFile(path,'utf8');
    assert(!/\bdebugger\s*;/.test(source),`${path}: debugger statement`);
    assert(!/[ \t]+$/m.test(source),`${path}: trailing whitespace`);
  }
}
const html = await readFile('index.html','utf8');
assert(html.includes('lang="zh-CN"'),'Chinese document language is required');
assert(!/(?:src|href)=["']https?:\/\//.test(html),'Runtime must remain free of third-party requests');
const css = await readFile('src/style.css','utf8');
assert.equal((css.match(/{/g)||[]).length,(css.match(/}/g)||[]).length,'CSS braces must balance');
console.log('Lint passed: JavaScript syntax, source hygiene, CSS braces and offline entrypoint.');
