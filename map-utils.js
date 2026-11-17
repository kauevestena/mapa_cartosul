export const SITE_URL = 'https://kauevestena.github.io/mapa_cartosul/';
// ColorBrewer Paired (12), ordered for distinct adjacent points.
export const COLORS = ['#e31a1c', '#1f78b4', '#33a02c', '#ff7f00', '#6a3d9a', '#b15928', '#a6cee3', '#b2df8a', '#fdbf6f', '#cab2d6', '#ffff99', '#fb9a99'];

export function pointBounds(data) {
  if (data?.type !== 'FeatureCollection' || !data.features?.length) throw new Error('Nenhum ponto disponível.');
  const bounds = [Infinity, Infinity, -Infinity, -Infinity];
  for (const feature of data.features) {
    const [lng, lat] = feature.geometry?.coordinates ?? [];
    if (feature.geometry?.type !== 'Point' || !Number.isFinite(lng) || !Number.isFinite(lat) || Math.abs(lng) > 180 || Math.abs(lat) >= 90) throw new Error('Coordenada inválida.');
    bounds[0] = Math.min(bounds[0], lng); bounds[1] = Math.min(bounds[1], lat);
    bounds[2] = Math.max(bounds[2], lng); bounds[3] = Math.max(bounds[3], lat);
  }
  return bounds;
}

export function bufferedBounds(bounds, meters = 200) {
  // WGS84 local radii of curvature; sub-metre accuracy for this campus buffer.
  const rad = Math.PI / 180, a = 6378137, e2 = 6.69437999014e-3;
  const latitude = (bounds[1] + bounds[3]) / 2 * rad;
  const w = Math.sqrt(1 - e2 * Math.sin(latitude) ** 2);
  const dLat = meters / (a * (1 - e2) / w ** 3) / rad;
  const dLng = meters / (a / w * Math.cos(latitude)) / rad;
  return [bounds[0] - dLng, bounds[1] - dLat, bounds[2] + dLng, bounds[3] + dLat];
}

export const asMapBounds = b => [[b[0], b[1]], [b[2], b[3]]];
export const contains = (bounds, lng, lat) => lng >= bounds[0] && lng <= bounds[2] && lat >= bounds[1] && lat <= bounds[3];
export function quadkey(x, y, z) {
  let key = '';
  for (let level = z; level > 0; level--) {
    const mask = 2 ** (level - 1);
    key += ((x & mask) ? 1 : 0) + ((y & mask) ? 2 : 0);
  }
  return key;
}

export function bingTileURL(template, subdomain, x, y, z) {
  const url = template.replace('{subdomain}', subdomain).replace('{quadkey}', quadkey(x, y, z)).replace('{culture}', 'pt-BR');
  if (!url.startsWith('https://')) throw new Error('Bing não retornou uma URL HTTPS.');
  return url;
}
