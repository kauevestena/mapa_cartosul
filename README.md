# CartoSul 2026

Mapa móvel dos 11 locais em `Pontos.geojson`, a única fonte de dados do evento. Os demais arquivos originais não são utilizados nem publicados.

URL após a aprovação e o merge: https://kauevestena.github.io/mapa_cartosul/

## Uso

- **Minha localização**: solicita permissão ao tocar, mostra a posição e a precisão do GPS; o controle de GPS também permite ativar/desativar o acompanhamento. HTTPS é necessário. Fora da área do evento, o mapa não sai do câmpus.
- Pontos numerados e lista acessível com os nomes e as anotações originais. Anfiteatro tem marcador maior. Cores: ColorBrewer Paired.
- Zoom +/−, bússola, escala métrica e relevo Mapzen Terrarium no AWS, sem chave, com exagero 1×. O botão Relevo 3D permite inclinar a câmera; o terreno já está ativo na vista inicial vertical.
- OpenStreetMap padrão e Positron/OpenFreeMap sem chave; camadas externas exigem conexão.
- Bing aérea usa a API oficial de metadados e quadkeys. Ao selecionar, informe uma chave Bing Maps Enterprise autorizada. A chave não é salva em disco/localStorage; é enviada ao Bing via HTTPS. O acesso Basic gratuito foi encerrado. Não incluímos endpoints não documentados nem credenciais de terceiros. Referência: https://learn.microsoft.com/en-us/bingmaps/rest-services/imagery/get-imagery-metadata
- QR code disponível no menu Camadas e em `assets/cartosul-2026-qr.svg` / `.png` (1024 px, margem de 4 módulos).

## Limite de navegação

O BBOX é calculado em tempo de execução a partir do GeoJSON: oeste −52.6907793274°, sul −26.1977017003°, leste −52.6887597656°, norte −26.1955559078°. Cada lado recebe 200 m usando os raios locais do elipsoide WGS84 (aproximação local com erro inferior a 1 m nesta área). `maxBounds` do MapLibre limita a navegação e o afastamento; não é uma máscara de recorte de pixels, e perspectivas inclinadas podem mostrar contexto além das bordas.

## Desenvolvimento e publicação

Requer Node.js 22 ou posterior:

```sh
npm ci --ignore-scripts
npm run check
npm test
npm run build
```

Sirva `dist/` por HTTP local ou HTTPS. O build publica apenas uma lista explícita de arquivos, inclui MapLibre GL JS 5.13.0 localmente e regenera os QR codes para a URL acima. Sem framework, fontes externas, rastreadores ou service worker. Razão de pixels limitada a 2, dois workers e cache de tiles limitado para reduzir o custo em celulares.

O workflow valida PRs e envia um artefato Pages; o deploy ocorre somente no `main` (push ou execução manual). Um PR não publica nem altera o site em produção. Não faça merge antes de revisar. O destino do QR só estará disponível depois do primeiro deploy.

Terreno: https://registry.opendata.aws/terrain-tiles/ · atribuições: https://github.com/tilezen/joerd/blob/master/docs/attribution.md
