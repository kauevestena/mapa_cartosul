import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { pointBounds, bufferedBounds, contains, quadkey, bingTileURL, SITE_URL } from '../map-utils.js';
const data = JSON.parse(await readFile(new URL('../Pontos.geojson', import.meta.url)));

test('all original points fit the campus boundary', () => {
  assert.equal(data.features.length, 12);
  const bbox = pointBounds(data), limits = bufferedBounds(bbox);
  assert.deepEqual(bbox, [-52.690779327392519, -26.198034170376577, -52.688759765624965, -26.195555907849418]);
  for (const feature of data.features) assert.ok(contains(limits, ...feature.geometry.coordinates));
  assert.equal(contains(limits, -52.7, -26.2), false);
});
test('buffer is 200 metres at each edge using independently tabulated local degree lengths', () => {
  const bbox = pointBounds(data), limits = bufferedBounds(bbox);
  const latitudeMetresPerDegree = 110790.8, longitudeMetresPerDegree = 99947.7;
  for (const meters of [(bbox[0]-limits[0])*longitudeMetresPerDegree, (limits[2]-bbox[2])*longitudeMetresPerDegree, (bbox[1]-limits[1])*latitudeMetresPerDegree, (limits[3]-bbox[3])*latitudeMetresPerDegree]) assert.ok(Math.abs(meters - 200) < 0.5, String(meters));
});
test('invalid datasets fail clearly', () => {
  assert.throws(() => pointBounds({ type: 'FeatureCollection', features: [] }));
  assert.throws(() => pointBounds({ type: 'FeatureCollection', features: [{ geometry: { type: 'Point', coordinates: [NaN, 0] } }] }));
});
test('Bing uses documented quadkeys, not XYZ URLs', () => {
  assert.equal(quadkey(3, 5, 3), '213');
  assert.equal(bingTileURL('https://{subdomain}.example/a{quadkey}?mkt={culture}', 't0', 3, 5, 3), 'https://t0.example/a213?mkt=pt-BR');
  assert.throws(() => bingTileURL('http://example/{quadkey}', 't0', 3, 5, 3));
});
test('QR destination is the repository Pages URL', () => assert.equal(SITE_URL, 'https://kauevestena.github.io/mapa_cartosul/'));
