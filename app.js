import { COLORS, pointBounds, bufferedBounds, asMapBounds, bingTileURL } from './map-utils.js';

const $ = id => document.getElementById(id);
let statusTimer;
function notify(message, persistent = false) {
  clearTimeout(statusTimer); $('status').textContent = message;
  if (!persistent) statusTimer = setTimeout(() => { $('status').textContent = ''; }, 6500);
}
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
function dismissLocateHint() {
  $('locate-hint').hidden = true;
  $('locate').removeAttribute('aria-describedby');
}
$('locate-hint-close').onclick = dismissLocateHint;
for (const button of document.querySelectorAll('[data-close]')) button.onclick = () => button.closest('dialog').close();
$('share').onclick = () => { $('options').open = false; $('share-dialog').showModal(); };
function setPlacesOpen(open) {
  $('places-list').hidden = !open; $('places-toggle').setAttribute('aria-expanded', String(open));
  document.querySelector('.places').classList.toggle('open', open); $('list-arrow').textContent = open ? '↓' : '↑';
}
$('places-toggle').onclick = () => setPlacesOpen($('places-list').hidden);

async function start() {
  const response = await fetch('./Pontos.geojson');
  if (!response.ok) throw new Error('Não foi possível carregar os locais. Recarregue a página.');
  const data = await response.json();
  const bounds = pointBounds(data), limits = bufferedBounds(bounds);
  if (!globalThis.maplibregl) throw new Error('Não foi possível carregar o mapa. Recarregue a página.');
  const ml = globalThis.maplibregl;
  ml.setWorkerCount(2);
  const terrainSource = {
    type: 'raster-dem', tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
    tileSize: 256, encoding: 'terrarium', maxzoom: 15,
    attribution: '<a href="https://registry.opendata.aws/terrain-tiles/">Terreno: Mapzen / AWS</a> · <a href="https://github.com/tilezen/joerd/blob/master/docs/attribution.md">Fontes de elevação</a>'
  };
  const rasterStyle = (source, maxzoom = 19) => ({
    version: 8, sources: { base: { type: 'raster', tileSize: 256, maxzoom, ...source } },
    layers: [{ id: 'base', type: 'raster', source: 'base' }]
  });
  const osmStyle = () => rasterStyle({ tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' });
  let bingMetadata, activeBasemap = 'osm';
  let map;
  try { map = new ml.Map({
    container: 'map', style: osmStyle(), bounds: asMapBounds(bounds),
    fitBoundsOptions: { padding: { top: Math.min(185, innerHeight * .25), bottom: Math.min(180, innerHeight * .25), left: 52, right: 62 }, maxZoom: 18 },
    maxBounds: asMapBounds(limits), maxZoom: 21, maxPitch: 55, pitch: 0,
    attributionControl: false, renderWorldCopies: false, maxTileCacheSize: 64,
    locale: { 'NavigationControl.ZoomIn': 'Aumentar zoom', 'NavigationControl.ZoomOut': 'Diminuir zoom', 'NavigationControl.ResetBearing': 'Orientar para o norte', 'GeolocateControl.FindMyLocation': 'Minha localização', 'GeolocateControl.LocationNotAvailable': 'Localização indisponível' },
    pixelRatio: Math.min(devicePixelRatio || 1, 2),
    transformRequest: (url, type) => {
      if (type === 'Tile' && url.startsWith('https://cartosul.invalid/bing/')) {
        const [z, x, y] = url.split('/').slice(-3).map(Number);
        return { url: bingTileURL(bingMetadata.imageUrl, bingMetadata.imageUrlSubdomains[0], x, y, z) };
      }
      return { url };
    }
  }); } catch {
    $('point-count').textContent = `${data.features.length} locais`;
    for (const [index, feature] of data.features.entries()) {
      const item = document.createElement('li');
      item.className = 'fallback-place';
      item.textContent = `${index + 1}. ${feature.properties.Nome}${feature.properties['Anotação'] ? ` — ${feature.properties['Anotação']}` : ''}`;
      $('places-list').append(item);
    }
    setPlacesOpen(true);
    throw new Error('Seu navegador não conseguiu iniciar o mapa 3D. Tente outro navegador com WebGL. A lista de locais continua disponível.');
  }
  map.addControl(new ml.NavigationControl({ showCompass: true, visualizePitch: true }), 'top-right');
  map.addControl(new ml.ScaleControl({ maxWidth: 100, unit: 'metric' }), 'bottom-left');
  map.addControl(new ml.AttributionControl({ compact: true }), 'bottom-right');
  const geolocate = new ml.GeolocateControl({
    positionOptions: { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 },
    trackUserLocation: true, showAccuracyCircle: true,
    fitBoundsOptions: { maxZoom: 19, duration: reducedMotion ? 0 : 700 }
  });
  map.addControl(geolocate, 'top-right');
  // The larger, labelled button triggers MapLibre's native tracking control.
  $('locate').onclick = () => {
    dismissLocateHint();
    if (geolocate.trigger() === false) notify('Localização indisponível. Tente novamente em alguns instantes.');
  };
  geolocate.on('geolocate', () => { notify('Localização atualizada. O círculo azul indica a precisão do GPS.'); });
  geolocate.on('outofmaxbounds', () => notify('Você está fora da área do evento. O mapa permanece no câmpus.'));
  geolocate.on('error', event => {
    notify(event.code === 1 ? 'Permita o acesso à localização nas configurações do navegador.' : 'Não foi possível obter o GPS. Tente novamente em uma área aberta.');
  });
  geolocate.on('trackuserlocationend', () => { $('locate').setAttribute('aria-pressed', 'false'); notify('Mapa livre para explorar. Toque em Minha localização para centralizar novamente.'); });
  geolocate.on('trackuserlocationstart', () => { dismissLocateHint(); $('locate').setAttribute('aria-pressed', 'true'); notify('Buscando sua localização…'); });

  let popup;
  const markerButtons = [];
  data.features.forEach((feature, index) => {
    const name = feature.properties.Nome, note = feature.properties['Anotação'];
    const color = COLORS[index % COLORS.length];
    const button = document.createElement('button'); button.type = 'button';
    button.className = `point${name === 'Anfiteatro' ? ' main' : ''}`;
    button.style.setProperty('--point-color', color); button.setAttribute('aria-label', `${index + 1}. ${name}`);
    button.setAttribute('aria-pressed', 'false');
    const dot = document.createElement('span'); dot.className = 'dot'; dot.textContent = index + 1; button.append(dot);
    markerButtons.push(button);
    const select = () => {
      setPlacesOpen(false);
      popup?.remove(); markerButtons.forEach(b => b.setAttribute('aria-pressed', 'false')); button.setAttribute('aria-pressed', 'true');
      const content = document.createElement('div'), title = document.createElement('h2'); title.textContent = name; content.append(title);
      if (note) { const paragraph = document.createElement('p'); paragraph.textContent = note; content.append(paragraph); }
      popup = new ml.Popup({ offset: 29, maxWidth: '285px' }).setLngLat(feature.geometry.coordinates).setDOMContent(content).addTo(map);
      popup.on('close', () => button.setAttribute('aria-pressed', 'false'));
      map.easeTo({ center: feature.geometry.coordinates, duration: reducedMotion ? 0 : 500 });
    };
    button.onclick = event => {
      // Keep this same click from reaching the map and immediately closing the new popup.
      event.stopPropagation();
      select();
    };
    new ml.Marker({ element: button }).setLngLat(feature.geometry.coordinates).addTo(map);
    const item = document.createElement('li'), listButton = document.createElement('button'); listButton.type = 'button';
    const swatch = document.createElement('span'); swatch.className = 'swatch'; swatch.style.backgroundColor = color; swatch.textContent = index + 1;
    const text = document.createElement('span'); text.textContent = name;
    if (note) { const small = document.createElement('span'); small.className = 'place-note'; small.textContent = note; text.append(small); }
    listButton.append(swatch, text); listButton.onclick = select;
    item.append(listButton); $('places-list').append(item);
  });
  $('point-count').textContent = `${data.features.length} locais · toque em um local`;

  function restoreTerrain() {
    if (!map.getSource('terrain')) map.addSource('terrain', terrainSource);
    map.setTerrain($('terrain').checked ? { source: 'terrain', exaggeration: 1 } : null);
  }
  map.on('style.load', restoreTerrain);
  map.on('error', event => {
    if (event.sourceId === 'terrain') {
      map.setTerrain(null); $('terrain').checked = false;
      notify('Relevo indisponível agora. O mapa continua disponível.');
    } else if (event.sourceId === 'base' || event.error?.message?.includes('openfreemap')) {
      notify('O mapa de fundo não carregou. Tente outra camada ou verifique sua conexão.');
    }
  });
  $('terrain').onchange = () => {
    restoreTerrain(); map.easeTo({ pitch: $('terrain').checked ? 40 : 0, duration: reducedMotion ? 0 : 500 });
  };
  async function switchBasemap(value) {
    $('basemap').disabled = true;
    try {
      let style;
      if (value === 'positron') {
        const res = await fetch('https://tiles.openfreemap.org/styles/positron', { signal: AbortSignal.timeout(15000) });
        if (!res.ok) throw new Error('Positron indisponível. Tente novamente.');
        style = await res.json();
      } else if (value === 'bing') {
        if (!bingMetadata) { $('basemap').value = activeBasemap; $('bing-dialog').showModal(); return; }
        const providers = bingMetadata.imageryProviders?.map(provider => provider.attribution) ?? [];
        style = rasterStyle({ tiles: ['https://cartosul.invalid/bing/{z}/{x}/{y}'], minzoom: bingMetadata.zoomMin, attribution: ['© Microsoft Bing', ...providers].join(' · ') }, bingMetadata.zoomMax);
      } else style = osmStyle();
      map.setStyle(style); activeBasemap = value; $('basemap').value = value; $('options').open = false;
    } catch (error) { $('basemap').value = activeBasemap; notify(error.message || 'Não foi possível trocar a camada.'); }
    finally { $('basemap').disabled = false; }
  }
  $('basemap').onchange = event => switchBasemap(event.target.value);
  $('bing-form').onsubmit = async event => {
    event.preventDefault(); $('bing-error').textContent = '';
    const submit = $('bing-form').querySelector('button'); submit.disabled = true;
    try {
      const url = new URL('https://dev.virtualearth.net/REST/v1/Imagery/Metadata/Aerial');
      url.search = new URLSearchParams({ key: $('bing-key').value.trim(), uriScheme: 'https', include: 'ImageryProviders', centerPoint: `${(bounds[1] + bounds[3]) / 2},${(bounds[0] + bounds[2]) / 2}`, zoomLevel: '18' });
      const result = await fetch(url, { signal: AbortSignal.timeout(15000) });
      const json = await result.json(), resource = json.resourceSets?.[0]?.resources?.[0];
      if (!result.ok || json.statusCode !== 200 || !resource?.imageUrl || !resource.imageUrlSubdomains?.length) throw new Error('Chave recusada ou serviço Bing indisponível.');
      bingMetadata = resource; $('bing-key').value = ''; $('bing-dialog').close(); await switchBasemap('bing');
    } catch { $('bing-error').textContent = 'Não foi possível acessar o Bing. Verifique a chave Enterprise e a conexão.'; }
    finally { submit.disabled = false; }
  };
  map.once('load', () => {
    $('basemap').disabled = false; $('terrain').disabled = false;
    $('locate').disabled = !navigator.geolocation || !isSecureContext;
    $('locate-hint').hidden = $('locate').disabled;
    if (!$('locate').disabled) $('locate').setAttribute('aria-describedby', 'locate-hint-text');
    notify($('locate').disabled ? 'A localização exige HTTPS e um navegador com GPS.' : '');
  });
  map.getCanvas().addEventListener('webglcontextlost', () => notify('O mapa foi interrompido. Recarregue a página para continuar.', true));
}
start().catch(error => notify(error.message || 'Não foi possível iniciar o mapa. Recarregue a página.', true));
