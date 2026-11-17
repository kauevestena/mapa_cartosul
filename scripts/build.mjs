import { mkdir, cp, rm, writeFile, readFile } from 'node:fs/promises';
import QRCode from 'qrcode';
import { SITE_URL, pointBounds } from '../map-utils.js';

// Explicit allowlist: Pontos.geojson is the only repository dataset published.
pointBounds(JSON.parse(await readFile('Pontos.geojson', 'utf8')));
await mkdir('assets', { recursive: true });
const options = { errorCorrectionLevel: 'M', margin: 4, width: 1024, color: { dark: '#000000', light: '#ffffff' } };
await writeFile('assets/cartosul-2026-qr.svg', await QRCode.toString(SITE_URL, { ...options, type: 'svg' }));
await QRCode.toFile('assets/cartosul-2026-qr.png', SITE_URL, options);
await rm('dist', { recursive: true, force: true });
await mkdir('dist/vendor', { recursive: true });
for (const path of ['index.html', 'style.css', 'app.js', 'map-utils.js', 'Pontos.geojson', 'assets']) await cp(path, `dist/${path}`, { recursive: true });
for (const file of ['maplibre-gl.js', 'maplibre-gl.css']) await cp(`node_modules/maplibre-gl/dist/${file}`, `dist/vendor/${file}`);
await cp('node_modules/maplibre-gl/LICENSE.txt', 'dist/vendor/maplibre-LICENSE.txt');
await writeFile('dist/.nojekyll', '');
console.log(`Built dist/; QR code points to ${SITE_URL}`);
