import { readFile, writeFile } from 'node:fs/promises';
let html=await readFile(new URL('./index.html',import.meta.url),'utf8');
for(const name of ['style','mobile'])html=html.replace(`<link rel="stylesheet" href="./src/${name}.css">`,`<style>${await readFile(new URL(`./src/${name}.css`,import.meta.url),'utf8')}</style>`);
html=html.replace('<script src="./src/app.js"></script>',`<script>${await readFile(new URL('./src/app.js',import.meta.url),'utf8')}</script>`);
await writeFile(new URL('./NOCTURNE.html',import.meta.url),html);
console.log('Built NOCTURNE.html');
