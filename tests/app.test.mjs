import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';
import { PNG } from 'pngjs';
import jsQR from 'jsqr';
import { SITE_URL } from '../map-utils.js';

const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
const data = JSON.parse(await readFile(new URL('../Pontos.geojson', import.meta.url)));

test('mobile interaction flow: points, styles, terrain, GPS states and safe text', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const dom = new JSDOM(html, { url: 'https://example.test/mapa_cartosul/' });
  const { window } = dom, events = new Map(), markers = [];
  let map, geo, lastPopup, fetches = [], triggerCount = 0, bingValid = false;
  class Evented {
    constructor() { events.set(this, new Map()); }
    on(name, callback) { const list = events.get(this).get(name) || []; list.push(callback); events.get(this).set(name, list); return this; }
    once(name, callback) { return this.on(name, callback); }
    fire(name, value = {}) { for (const callback of events.get(this).get(name) || []) callback(value); }
  }
  class MapMock extends Evented {
    constructor(options) { super(); map = this; this.options = options; this.sources = {}; }
    addControl() {} getCanvas() { return window.document.createElement('canvas'); }
    getSource(id) { return this.sources[id]; } addSource(id, source) { this.sources[id] = source; }
    setTerrain(terrain) { this.terrain = terrain; }
    setStyle(style) { this.style = style; this.sources = {}; this.fire('style.load'); }
    easeTo(camera) { this.camera = camera; }
  }
  class GeoMock extends Evented { constructor(options) { super(); geo = this; this.options = options; } trigger() { triggerCount++; } }
  class MarkerMock { constructor(options) { markers.push(options.element); } setLngLat() { return this; } addTo() { return this; } }
  class PopupMock extends Evented { constructor() { super(); lastPopup = this; } setLngLat() { return this; } setDOMContent(node) { this.content = node; return this; } addTo() { return this; } remove() { this.fire('close'); } }
  for (const name of ['document', 'navigator']) Object.defineProperty(globalThis, name, { value: window[name], configurable: true });
  Object.assign(globalThis, { innerHeight: 568, devicePixelRatio: 3, isSecureContext: true, matchMedia: () => ({ matches: true }), maplibregl: { setWorkerCount() {}, Map: MapMock, GeolocateControl: GeoMock, Marker: MarkerMock, Popup: PopupMock, NavigationControl: class {}, ScaleControl: class {}, AttributionControl: class {} } });
  Object.defineProperty(window.navigator, 'geolocation', { value: {}, configurable: true });
  for (const dialog of window.document.querySelectorAll('dialog')) { dialog.showModal = () => dialog.setAttribute('open', ''); dialog.close = () => dialog.removeAttribute('open'); }
  globalThis.fetch = async input => {
    const url = String(input); fetches.push(url);
    if (url.includes('Pontos.geojson')) return { ok: true, json: async () => data };
    if (url.includes('openfreemap')) return { ok: true, json: async () => ({ version: 8, sources: {}, layers: [] }) };
    if (url.includes('virtualearth')) return bingValid
      ? { ok: true, json: async () => ({ statusCode: 200, resourceSets: [{ resources: [{ imageUrl: 'https://{subdomain}.example.test/a{quadkey}?mkt={culture}', imageUrlSubdomains: ['t0'], zoomMin: 1, zoomMax: 20, imageryProviders: [{ attribution: 'Imagery provider' }] }] }] }) }
      : { ok: false, json: async () => ({ statusCode: 401 }) };
    throw new Error(url);
  };
  const $ = id => window.document.getElementById(id);
  await import(`../app.js?test=${Date.now()}`);
  await new Promise(resolve => setImmediate(resolve));
  map.fire('style.load'); map.fire('load');
  assert.equal(markers.length, 11);
  assert.ok(markers[0].classList.contains('main'));
  assert.equal(map.options.pixelRatio, 2);
  assert.ok(map.options.fitBoundsOptions.padding.top + map.options.fitBoundsOptions.padding.bottom < 568);
  assert.equal(map.terrain.source, 'terrain');
  assert.equal($('locate').disabled, false);
  $('locate').click(); assert.equal(triggerCount, 1);
  geo.fire('error', { code: 1 }); assert.match($('status').textContent, /Permita/);
  geo.fire('outofmaxbounds'); assert.match($('status').textContent, /fora da área/);
  geo.fire('geolocate'); assert.match($('status').textContent, /precisão/);
  markers[0].click(); assert.equal(lastPopup.content.querySelector('h2').textContent, 'Anfiteatro');
  markers[5].click(); assert.equal(lastPopup.content.querySelector('p'), null);
  $('places-toggle').click(); assert.equal($('places-list').hidden, false);
  $('places-list').querySelector('button').click(); assert.equal($('places-list').hidden, true);
  $('basemap').value = 'positron'; await $('basemap').onchange({ target: $('basemap') });
  assert.ok(fetches.some(url => url.includes('/styles/positron'))); assert.equal(map.terrain.source, 'terrain');
  $('terrain').checked = false; $('terrain').onchange(); assert.equal(map.terrain, null);
  $('basemap').value = 'osm'; await $('basemap').onchange({ target: $('basemap') });
  assert.match(map.style.sources.base.tiles[0], /tile.openstreetmap.org/); assert.equal(map.terrain, null);
  $('basemap').value = 'bing'; await $('basemap').onchange({ target: $('basemap') }); assert.ok($('bing-dialog').hasAttribute('open'));
  $('bing-key').value = 'invalid-test-key'; await $('bing-form').onsubmit({ preventDefault() {} });
  assert.match($('bing-error').textContent, /Verifique/); assert.equal($('basemap').value, 'osm');
  bingValid = true; await $('bing-form').onsubmit({ preventDefault() {} });
  assert.equal($('basemap').value, 'bing'); assert.equal($('bing-key').value, '');
  assert.match(map.style.sources.base.attribution, /Imagery provider/);
  assert.equal(map.options.transformRequest('https://cartosul.invalid/bing/3/3/5', 'Tile').url, 'https://t0.example.test/a213?mkt=pt-BR');
  $('share').click(); assert.ok($('share-dialog').hasAttribute('open'));
  assert.equal($('share-dialog').querySelector('a').href, SITE_URL);
  dom.window.close();
});

test('print QR actually decodes to the expected Pages URL', async () => {
  const png = PNG.sync.read(await readFile(new URL('../assets/cartosul-2026-qr.png', import.meta.url)));
  const decoded = jsQR(new Uint8ClampedArray(png.data), png.width, png.height);
  assert.equal(decoded?.data, SITE_URL);
});
