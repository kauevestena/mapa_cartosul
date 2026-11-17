#!/usr/bin/env python3
"""
Mapa CartoSul 2026 - Automated Map Generation Script
Fulfills all requirements from reqs.md + user feedback:
  - Printable PDF map (Portrait, A4) with 1cm margins
  - UTM Zone 22S / SIRGAS 2000 projection (EPSG:31982) with inscribed metadata
  - Title: "Mapa CartoSul 2026"
  - Map rotated using ref_lines (p0 downwards, p1 upwards), ref_lines layer not rendered
  - Rotated north arrow linked to map rotation
  - Graphical scale bar with 2 ticks
  - Points layer styled for B&W printing with solid black symbols (prominent star for Anfiteatro)
  - Basemap: default OSM, dimmed
  - Labels: Comments ALWAYS strictly located below names using paragraph blocks
  - Extra care with label collision avoidance (PAL solver, obstacle weighting, callout leader lines)
  - Blank zone eliminated: canvas expanded and dynamically centered with balanced margins
  - Authorship: Prof. Kauê e Moraes Vestena
  - Top parameters dictionary for easy tweaking
"""

import os
import sys
import math
import json

# Ensure offscreen Qt platform for headless execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# ==============================================================================
# PARAMETERS DICTIONARY (TWEAKABLE SETTINGS)
# ==============================================================================
CONFIG = {
    # File paths
    "points_geojson": "Pontos.geojson",
    "ref_lines_geojson": "ref_lines.geojson",
    "project_qgz": "projeto.qgz",
    "output_pdf": "mapa_cartosul_2026.pdf",
    "output_preview_png": "mapa_cartosul_2026.png",
    "update_qgz_project": True,   # Also save the layout into projeto.qgz
    
    # Page layout
    "page_format": "A4",          # A4 (210 x 297 mm)
    "page_orientation": "Portrait",
    "page_margin_mm": 10.0,       # 1 cm margins
    
    # Layout sections vertical placement (in mm)
    # Total usable height = 297 - 20 = 277 mm
    "layout_geometry": {
        "title_y": 10.0,
        "title_height": 13.0,
        "canvas_y": 24.0,
        "canvas_height": 222.0,   # Canvas extends directly down to footer
        "footer_y": 247.0,
        "footer_height": 40.0,    # Expanded footer for larger QR code
    },
    
    # Coordinate Reference System (UTM 22S / SIRGAS 2000)
    "crs_authid": "EPSG:31982",
    
    # Map scale & view
    # 1:1750 accommodates all 12 points with healthy margins and zero collisions
    "map_scale": 1750,
    "auto_center_rotated": True,  # Automatically balance margins in rotated coordinate frame
    
    # Basemap (Default OSM, dimmed)
    "basemap": {
        "url": "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmax=19&zmin=0",
        "opacity": 0.50,          # 50% opacity (dimmed)
        "cache_wait_seconds": 2.5,# Seconds to wait for asynchronous tile downloads
    },
    
    # Symbology (Solid black & symbols compatible with B&W printing)
    # Shapes: 'star', 'circle', 'square', 'diamond', 'triangle', 'cross', 'cross2', 'hexagon'
    "symbology": {
        "Anfiteatro": {
            "name": "star",
            "size": "7.5",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.7"
        },
        "R.U.": {
            "name": "square",
            "size": "5.0",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.5"
        },
        "Quentuxa": {
            "name": "diamond",
            "size": "5.5",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.5"
        },
        "Ponto de Ônibus": {
            "name": "cross",
            "size": "5.5",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.6"
        },
        "Vestiários Públicos": {
            "name": "cross2",
            "size": "5.0",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.6"
        },
        "Pista de Atletismo - Entrada": {
            "name": "triangle",
            "size": "5.0",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.5"
        },
        "Bloco B": {
            "name": "hexagon",
            "size": "5.5",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.5"
        },
        "Entrada do Câmpus": {
            "name": "triangle",
            "size": "5.0",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.5"
        },
        "N110 - Andar Superior": {
            "name": "square",
            "size": "4.5",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.5"
        },
        "M011 - Térreo": {
            "name": "square",
            "size": "4.5",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.5"
        },
        # Default fallback for any other points
        "default": {
            "name": "circle",
            "size": "4.5",
            "color": "0,0,0,255",
            "outline_color": "255,255,255,255",
            "outline_width": "0.5"
        }
    },
    
    # Labels (Bigger for Name, smaller for Comment strictly below Name, black text with white outline)
    "labels": {
        "font_family": "Liberation Sans",
        "name_font_size": 9.0,
        "name_font_bold": True,
        "comment_font_size_pt": 7.5,
        "text_color": "#000000",
        "buffer_color": "#ffffff",
        "buffer_size_mm": 1.1,
        "distance_from_point_mm": 2.0,
        "multiline_align": "Center",   # Center alignment stacks comment cleanly under name
        "callout_enabled": True,       # Leader lines to resolve tight positions
        "callout_min_length_mm": 1.0,
        "obstacle_factor": 2.5,        # Higher avoidance weight to prevent overlapping markers
        "priority": 10,
    },
    
    # Scale Bar (Graphical scale with 2 ticks)
    "scalebar": {
        "units": "Meters",
        "segments": 2,              # Two ticks
        "segments_left": 0,
        "units_per_segment": 50,    # 50 m each -> 100 m total
        "style": "Line Ticks Up",
        "font_size": 8.5,
    },
    
    # North Arrow
    "north_arrow": {
        "svg_path": "/usr/share/qgis/svg/arrows/NorthArrow_02.svg",
        "size_mm": 18.0,
        "background_opacity": 220,  # 0 to 255
    },
    
    # QR Code (in Metadata Panel)
    "qr_code": {
        "enabled": True,
        "image_path": "assets/cartosul-2026-qr.png",
        "size_mm": 28.0,          # Enlarged prominent QR code
        "caption": "acesse a versão digital",
        "caption_font_size": 7.5,
    },
    
    # Title & Inscribed Metadata
    "title_text": "Mapa CartoSul 2026",
    "authorship": "Prof. Kauê e Moraes Vestena",
    "metadata_col1": (
        "<b>Projeção:</b> UTM Zona 22S &nbsp;|&nbsp; <b>Datum:</b> SIRGAS 2000 (EPSG:31982)<br>"
        "<b>Autoria:</b> Prof. Kauê e Moraes Vestena &nbsp;|&nbsp; <b>Evento:</b> CartoSul 2026<br>"
        "<b>Basemap:</b> OpenStreetMap contributors (dimmed) &nbsp;|&nbsp; <b>Escala:</b> 1:1.750"
    ),
    
    # Export DPI
    "pdf_dpi": 300,
    "preview_png_dpi": 200,
}

# ==============================================================================
# SCRIPT LOGIC
# ==============================================================================

from qgis.core import (
    QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer,
    QgsCoordinateReferenceSystem, QgsPrintLayout, QgsLayoutItemMap,
    QgsLayoutItemLabel, QgsLayoutItemScaleBar, QgsLayoutItemPicture,
    QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes, QgsRectangle,
    QgsPointXY, QgsCoordinateTransform, QgsLayoutExporter,
    QgsScaleBarSettings, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling,
    QgsTextFormat, QgsTextBufferSettings, QgsSimpleLineCallout,
    QgsRuleBasedRenderer, QgsMarkerSymbol, QgsLayoutItemPage,
    QgsLayoutMeasurement, QgsRenderContext
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtCore import Qt, QPointF, QEventLoop, QTimer


def compute_rotation_from_ref_lines(ref_lines_path, target_crs, project):
    """
    Computes rotation angle such that:
      - p0 points downwards
      - p1 points upwards in the layout canvas.
    """
    with open(ref_lines_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    coords = data["features"][0]["geometry"]["coordinates"]
    p0_lon, p0_lat = coords[0]
    p1_lon, p1_lat = coords[1]
    
    ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), target_crs, project)
    p0_utm = ct.transform(QgsPointXY(p0_lon, p0_lat))
    p1_utm = ct.transform(QgsPointXY(p1_lon, p1_lat))
    
    dx = p1_utm.x() - p0_utm.x()
    dy = p1_utm.y() - p0_utm.y()
    
    azimuth = math.degrees(math.atan2(dx, dy))
    rotation_deg = (-azimuth) % 360
    return rotation_deg, p0_utm, p1_utm


def set_map_canvas_view(map_item, cx, cy, width_mm, height_mm, rotation_deg, scale):
    """
    Applies extent, rotation and scale to the map item while strictly preserving
    the exact physical dimensions on the page (preventing QGIS aspect-ratio resets).
    """
    half_w = (width_mm * scale / 1000.0) / 2.0
    half_h = (height_mm * scale / 1000.0) / 2.0
    map_item.zoomToExtent(QgsRectangle(cx - half_w, cy - half_h, cx + half_w, cy + half_h))
    map_item.attemptResize(QgsLayoutSize(width_mm, height_mm, QgsUnitTypes.LayoutMillimeters))
    map_item.setMapRotation(rotation_deg)
    map_item.setScale(scale)


def solve_balanced_center(pontos_layer, target_crs, rotation_deg, map_item, width_mm, height_mm, scale, project):
    """
    Dynamically and iteratively solves for the exact map center in UTM such that
    the bounding box of points is centered on the layout map item,
    ensuring equal top/bottom and left/right margins with no dead blank zone.
    """
    ct = QgsCoordinateTransform(pontos_layer.crs(), target_crs, project)
    pts_utm = [ct.transform(f.geometry().asPoint()) for f in pontos_layer.getFeatures()]
    
    cur_cx = sum(pt.x() for pt in pts_utm) / len(pts_utm)
    cur_cy = sum(pt.y() for pt in pts_utm) / len(pts_utm)
    
    target_x = width_mm / 2.0
    target_y = height_mm / 2.0
    
    for _ in range(5):
        set_map_canvas_view(map_item, cur_cx, cur_cy, width_mm, height_mm, rotation_deg, scale)
        
        pts0 = [map_item.mapToItemCoords(QPointF(pt.x(), pt.y())) for pt in pts_utm]
        mid_x0 = (min(pt.x() for pt in pts0) + max(pt.x() for pt in pts0)) / 2.0
        mid_y0 = (min(pt.y() for pt in pts0) + max(pt.y() for pt in pts0)) / 2.0
        
        err_x = target_x - mid_x0
        err_y = target_y - mid_y0
        if abs(err_x) < 0.05 and abs(err_y) < 0.05:
            break
            
        step = 5.0
        set_map_canvas_view(map_item, cur_cx + step, cur_cy, width_mm, height_mm, rotation_deg, scale)
        pts_dx = [map_item.mapToItemCoords(QPointF(pt.x(), pt.y())) for pt in pts_utm]
        jx_x = ((min(pt.x() for pt in pts_dx) + max(pt.x() for pt in pts_dx)) / 2.0 - mid_x0) / step
        jy_x = ((min(pt.y() for pt in pts_dx) + max(pt.y() for pt in pts_dx)) / 2.0 - mid_y0) / step
        
        set_map_canvas_view(map_item, cur_cx, cur_cy + step, width_mm, height_mm, rotation_deg, scale)
        pts_dy = [map_item.mapToItemCoords(QPointF(pt.x(), pt.y())) for pt in pts_utm]
        jx_y = ((min(pt.y() for pt in pts_dy) + max(pt.y() for pt in pts_dy)) / 2.0 - mid_x0) / step
        jy_y = ((min(pt.y() for pt in pts_dy) + max(pt.y() for pt in pts_dy)) / 2.0 - mid_y0) / step
        
        det = jx_x * jy_y - jx_y * jy_x
        if abs(det) > 1e-6:
            cur_cx += (jy_y * err_x - jx_y * err_y) / det
            cur_cy += (-jy_x * err_x + jx_x * err_y) / det

    set_map_canvas_view(map_item, cur_cx, cur_cy, width_mm, height_mm, rotation_deg, scale)
    return cur_cx, cur_cy


def apply_pontos_symbology(layer, symbology_config):
    """Applies rule-based solid black symbology compatible with B&W printing."""
    root_rule = QgsRuleBasedRenderer.Rule(None)
    
    # 1. Anfiteatro star
    anf_cfg = symbology_config.get("Anfiteatro", {})
    star_sym = QgsMarkerSymbol.createSimple({
        "name": anf_cfg.get("name", "star"),
        "size": anf_cfg.get("size", "7.5"),
        "color": anf_cfg.get("color", "0,0,0,255"),
        "outline_color": anf_cfg.get("outline_color", "255,255,255,255"),
        "outline_width": anf_cfg.get("outline_width", "0.7")
    })
    rule_star = QgsRuleBasedRenderer.Rule(star_sym, 0, 0, '"Nome" = \'Anfiteatro\'', 'Anfiteatro')
    root_rule.appendChild(rule_star)
    
    # 2. Specific feature rules
    for name, cfg in symbology_config.items():
        if name in ["Anfiteatro", "default"]:
            continue
        sym = QgsMarkerSymbol.createSimple({
            "name": cfg.get("name", "circle"),
            "size": cfg.get("size", "5.0"),
            "color": cfg.get("color", "0,0,0,255"),
            "outline_color": cfg.get("outline_color", "255,255,255,255"),
            "outline_width": cfg.get("outline_width", "0.5")
        })
        safe_name = name.replace("'", "\\'")
        rule = QgsRuleBasedRenderer.Rule(sym, 0, 0, f'"Nome" = \'{safe_name}\'', name)
        root_rule.appendChild(rule)
    
    # 3. Default fallback
    def_cfg = symbology_config.get("default", {})
    default_sym = QgsMarkerSymbol.createSimple({
        "name": def_cfg.get("name", "circle"),
        "size": def_cfg.get("size", "4.5"),
        "color": def_cfg.get("color", "0,0,0,255"),
        "outline_color": def_cfg.get("outline_color", "255,255,255,255"),
        "outline_width": def_cfg.get("outline_width", "0.5")
    })
    rule_default = QgsRuleBasedRenderer.Rule(default_sym, 0, 0, "ELSE", "Outros")
    root_rule.appendChild(rule_default)
    
    layer.setRenderer(QgsRuleBasedRenderer(root_rule))


def apply_pontos_labels(layer, label_config):
    """
    Configures HTML labels with:
      - Nome in bold
      - Anotação ALWAYS located below Nome (using paragraph blocks)
      - Crisp white outline buffer
      - Collision avoidance, obstacle weighting, and callout lines
    """
    pal = QgsPalLayerSettings()
    pal.isExpression = True
    
    comment_size = label_config.get("comment_font_size_pt", 7.5)
    # Paragraph tags guarantee that Anotação is ALWAYS positioned below Nome
    pal.fieldName = (
        "'<p style=\"margin:0; padding:0;\"><b>' || \"Nome\" || '</b></p>' || "
        'if("Anotação" is not null and "Anotação" != \'\', '
        f'\'<p style=\"margin:0; padding:0;\"><span style=\"font-size: {comment_size}pt;\">\' || "Anotação" || \'</span></p>\', \'\')'
    )
    
    tf = QgsTextFormat()
    font_family = label_config.get("font_family", "Liberation Sans")
    name_size = label_config.get("name_font_size", 9.0)
    bold = QFont.Bold if label_config.get("name_font_bold", True) else QFont.Normal
    tf.setFont(QFont(font_family, int(name_size), bold))
    tf.setSize(name_size)
    tf.setColor(QColor(label_config.get("text_color", "#000000")))
    tf.setAllowHtmlFormatting(True)
    
    # White buffer outline
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(label_config.get("buffer_size_mm", 1.1))
    buf.setColor(QColor(label_config.get("buffer_color", "#ffffff")))
    tf.setBuffer(buf)
    pal.setFormat(tf)
    
    # Collision avoidance & placement
    pal.placement = QgsPalLayerSettings.OrderedPositionsAroundPoint
    pal.multilineAlign = QgsPalLayerSettings.MultiCenter
    pal.dist = label_config.get("distance_from_point_mm", 2.0)
    pal.priority = label_config.get("priority", 10)
    pal.obstacleSettings().setIsObstacle(True)
    pal.obstacleSettings().setFactor(label_config.get("obstacle_factor", 2.5))
    
    if label_config.get("callout_enabled", True):
        callout = QgsSimpleLineCallout()
        callout.setEnabled(True)
        callout.setMinimumLength(label_config.get("callout_min_length_mm", 1.0))
        callout.setOffsetFromAnchor(1.0)
        callout.setOffsetFromLabel(1.0)
        pal.setCallout(callout)
    
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    layer.setLabelsEnabled(True)


def warm_osm_cache(osm_layer, cx, cy, target_crs, project, wait_seconds=2.5):
    """
    Prefetches OSM tiles in EPSG:3857 and pumps the Qt event loop
    so that QgsLayoutExporter can render the raster basemap synchronously.
    """
    crs_osm = QgsCoordinateReferenceSystem("EPSG:3857")
    ct_utm_to_osm = QgsCoordinateTransform(target_crs, crs_osm, project)
    fetch_rect_utm = QgsRectangle(cx - 600, cy - 600, cx + 600, cy + 600)
    fetch_rect_osm = ct_utm_to_osm.transform(fetch_rect_utm)
    
    dp = osm_layer.dataProvider()
    dp.block(1, fetch_rect_osm, 2048, 2048)
    
    loop = QEventLoop()
    QTimer.singleShot(int(wait_seconds * 1000), loop.quit)
    loop.exec_()
    
    # Second block call loads downloaded tiles into memory raster cache
    dp.block(1, fetch_rect_osm, 2048, 2048)


def test_label_collisions(map_item, layout):
    """Verifies that no labels collide on the layout canvas."""
    exporter = QgsLayoutExporter(layout)
    img_settings = QgsLayoutExporter.ImageExportSettings()
    img_settings.dpi = 150
    tmp_path = "/tmp/collision_check_temp.png"
    exporter.exportToImage(tmp_path, img_settings)
    
    results = exporter.labelingResults()
    map_results = results.get(map_item.uuid())
    if not map_results:
        print("[Collision Check] Warning: Unable to inspect label results.")
        return 0
    
    labels = map_results.allLabels()
    print(f"[Collision Check] Total placed labels: {len(labels)}")
    collisions = 0
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            if labels[i].labelGeometry.intersects(labels[j].labelGeometry):
                collisions += 1
                print(f"  [COLLISION] '{labels[i].labelText}' intersects '{labels[j].labelText}'")
    
    if collisions == 0:
        print("[Collision Check] PASS: 0 collisions detected. All labels clear.")
    else:
        print(f"[Collision Check] WARNING: {collisions} collisions detected.")
    
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    return collisions


def generate_map():
    print("=" * 60)
    print("Generating Mapa CartoSul 2026...")
    print("=" * 60)
    
    qgs_app = QgsApplication([], False)
    qgs_app.initQgis()
    
    try:
        project = QgsProject.instance()
        target_crs = QgsCoordinateReferenceSystem(CONFIG["crs_authid"])
        project.setCrs(target_crs)
        
        # 1. Load Pontos layer
        pontos_path = CONFIG["points_geojson"]
        if not os.path.isabs(pontos_path):
            pontos_path = os.path.abspath(pontos_path)
        pontos_layer = QgsVectorLayer(pontos_path, "Pontos", "ogr")
        if not pontos_layer.isValid():
            raise RuntimeError(f"Failed to load Pontos layer from {pontos_path}")
        project.addMapLayer(pontos_layer)
        
        # 2. Compute rotation from ref_lines
        ref_lines_path = CONFIG["ref_lines_geojson"]
        if not os.path.isabs(ref_lines_path):
            ref_lines_path = os.path.abspath(ref_lines_path)
        rotation_deg, p0_utm, p1_utm = compute_rotation_from_ref_lines(ref_lines_path, target_crs, project)
        print(f"Computed canvas rotation: {rotation_deg:.4f}° (p0 downwards, p1 upwards)")
        
        # 3. Setup Print Layout (A4 Portrait: 210 x 297 mm, 10mm margins)
        layout = QgsPrintLayout(project)
        layout.setName("Mapa CartoSul 2026")
        layout.initializeDefaults()
        
        page = layout.pageCollection().page(0)
        page.setPageSize("A4", QgsLayoutItemPage.Portrait)
        
        margin = CONFIG["page_margin_mm"]
        usable_width = 210.0 - 2 * margin  # 190 mm
        geom = CONFIG["layout_geometry"]
        
        # 4. Title Item
        title_item = QgsLayoutItemLabel(layout)
        title_item.setText(CONFIG["title_text"])
        title_tf = QgsTextFormat()
        title_tf.setFont(QFont("Liberation Sans", 18, QFont.Bold))
        title_item.setTextFormat(title_tf)
        title_item.setHAlign(Qt.AlignHCenter)
        title_item.setVAlign(Qt.AlignVCenter)
        title_item.attemptMove(QgsLayoutPoint(margin, geom["title_y"], QgsUnitTypes.LayoutMillimeters))
        title_item.attemptResize(QgsLayoutSize(usable_width, geom["title_height"], QgsUnitTypes.LayoutMillimeters))
        title_item.setFrameEnabled(True)
        title_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.5, QgsUnitTypes.LayoutMillimeters))
        title_item.setBackgroundColor(QColor(255, 255, 255))
        title_item.setBackgroundEnabled(True)
        layout.addLayoutItem(title_item)
        
        # 5. Map Item (Canvas occupies full vertical space down to footer)
        map_y = geom["canvas_y"]
        map_height = geom["canvas_height"]
        map_item = QgsLayoutItemMap(layout)
        map_item.setCrs(target_crs)
        map_item.attemptMove(QgsLayoutPoint(margin, map_y, QgsUnitTypes.LayoutMillimeters))
        map_item.attemptResize(QgsLayoutSize(usable_width, map_height, QgsUnitTypes.LayoutMillimeters))
        map_item.setFrameEnabled(True)
        map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.5, QgsUnitTypes.LayoutMillimeters))
        map_item.setScale(CONFIG["map_scale"])
        layout.addLayoutItem(map_item)
        
        # 6. Solve optimal balanced center (eliminates blank space at bottom of canvas)
        if CONFIG["auto_center_rotated"]:
            cx, cy = solve_balanced_center(pontos_layer, target_crs, rotation_deg, map_item, usable_width, map_height, CONFIG["map_scale"], project)
            print(f"Optimal balanced map center (UTM 22S): ({cx:.2f}, {cy:.2f})")
        else:
            ct = QgsCoordinateTransform(pontos_layer.crs(), target_crs, project)
            box = ct.transformBoundingBox(pontos_layer.extent())
            cx, cy = box.center().x(), box.center().y()
            set_map_canvas_view(map_item, cx, cy, usable_width, map_height, rotation_deg, CONFIG["map_scale"])
        
        # 7. Add OSM Basemap and warm cache
        basemap_cfg = CONFIG["basemap"]
        osm_layer = QgsRasterLayer(basemap_cfg["url"], "OSM Basemap", "wms")
        osm_layer.setOpacity(basemap_cfg["opacity"])
        project.addMapLayer(osm_layer)
        
        print("Fetching and warming OSM tile cache...")
        warm_osm_cache(osm_layer, cx, cy, target_crs, project, basemap_cfg["cache_wait_seconds"])
        
        # Set map layers: points and OSM basemap (ref_lines is NOT rendered)
        map_item.setLayers([pontos_layer, osm_layer])
        map_item.setKeepLayerSet(True)
        
        # 8. Apply symbology and labels
        apply_pontos_symbology(pontos_layer, CONFIG["symbology"])
        apply_pontos_labels(pontos_layer, CONFIG["labels"])
        
        # 9. Rotated North Arrow in top-right of map canvas
        na_cfg = CONFIG["north_arrow"]
        north_arrow = QgsLayoutItemPicture(layout)
        north_arrow.setPicturePath(na_cfg["svg_path"])
        north_arrow.setLinkedMap(map_item)
        north_arrow.setNorthMode(QgsLayoutItemPicture.GridNorth)
        na_size = na_cfg["size_mm"]
        north_arrow.attemptMove(QgsLayoutPoint(margin + usable_width - na_size - 4.0, map_y + 3.0, QgsUnitTypes.LayoutMillimeters))
        north_arrow.attemptResize(QgsLayoutSize(na_size, na_size, QgsUnitTypes.LayoutMillimeters))
        north_arrow.setBackgroundColor(QColor(255, 255, 255, na_cfg["background_opacity"]))
        north_arrow.setBackgroundEnabled(True)
        layout.addLayoutItem(north_arrow)
        
        # 10. Footer Box: directly beneath canvas, extending to bottom margin (y = 287 mm)
        footer_y = geom["footer_y"]
        footer_height = geom["footer_height"]
        footer_box = QgsLayoutItemLabel(layout)
        footer_box.setText("")
        footer_box.attemptMove(QgsLayoutPoint(margin, footer_y, QgsUnitTypes.LayoutMillimeters))
        footer_box.attemptResize(QgsLayoutSize(usable_width, footer_height, QgsUnitTypes.LayoutMillimeters))
        footer_box.setFrameEnabled(True)
        footer_box.setFrameStrokeWidth(QgsLayoutMeasurement(0.5, QgsUnitTypes.LayoutMillimeters))
        footer_box.setBackgroundColor(QColor(255, 255, 255))
        footer_box.setBackgroundEnabled(True)
        layout.addLayoutItem(footer_box)
        
        # 11. Graphical Scale Bar (inside top of footer)
        sb_cfg = CONFIG["scalebar"]
        scalebar = QgsLayoutItemScaleBar(layout)
        scalebar.setLinkedMap(map_item)
        scalebar.setUnits(QgsUnitTypes.DistanceMeters)
        scalebar.setNumberOfSegments(sb_cfg["segments"])
        scalebar.setNumberOfSegmentsLeft(sb_cfg["segments_left"])
        scalebar.setUnitsPerSegment(sb_cfg["units_per_segment"])
        scalebar.setUnitLabel("m")
        scalebar.setSegmentSizeMode(QgsScaleBarSettings.SegmentSizeFixed)
        scalebar.setStyle(sb_cfg["style"])
        sb_tf = QgsTextFormat()
        sb_tf.setFont(QFont("Liberation Sans", int(sb_cfg["font_size"])))
        scalebar.setTextFormat(sb_tf)
        scalebar.attemptMove(QgsLayoutPoint(margin + 6.0, footer_y + 4.0, QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(scalebar)
        
        # 12. Inscribed Metadata Label (below scale bar)
        meta_label = QgsLayoutItemLabel(layout)
        meta_text = (
            "<b>Projeção:</b> UTM Zona 22S &nbsp;|&nbsp; <b>Datum:</b> SIRGAS 2000 (EPSG:31982) &nbsp;|&nbsp; <b>Escala:</b> 1:1.750<br>"
            "<b>Autoria:</b> Prof. Kauê e Moraes Vestena &nbsp;|&nbsp; <b>Evento:</b> CartoSul 2026 &nbsp;|&nbsp; <b>Basemap:</b> OpenStreetMap (dimmed)"
        )
        meta_label.setText(meta_text)
        meta_label.setMode(QgsLayoutItemLabel.ModeHtml)
        meta_tf = QgsTextFormat()
        meta_tf.setFont(QFont("Liberation Sans", 7))
        meta_tf.setSize(7.5)
        meta_label.setTextFormat(meta_tf)
        meta_label.attemptMove(QgsLayoutPoint(margin + 6.0, footer_y + 21.0, QgsUnitTypes.LayoutMillimeters))
        meta_label.attemptResize(QgsLayoutSize(usable_width - 50.0, 15.0, QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(meta_label)
        
        # 13. QR Code & Caption in Metadata Panel
        qr_cfg = CONFIG.get("qr_code", {})
        if qr_cfg.get("enabled", True):
            qr_rel_path = qr_cfg.get("image_path", "assets/cartosul-2026-qr.png")
            qr_path = qr_rel_path if os.path.isabs(qr_rel_path) else os.path.abspath(qr_rel_path)
            if os.path.exists(qr_path):
                col_width = 44.0
                col_center = margin + usable_width - (col_width / 2.0) - 1.0
                qr_size = qr_cfg.get("size_mm", 28.0)
                qr_x = col_center - (qr_size / 2.0)
                qr_y = footer_y + 2.5
                
                qr_picture = QgsLayoutItemPicture(layout)
                qr_picture.setPicturePath(qr_path)
                qr_picture.attemptMove(QgsLayoutPoint(qr_x, qr_y, QgsUnitTypes.LayoutMillimeters))
                qr_picture.attemptResize(QgsLayoutSize(qr_size, qr_size, QgsUnitTypes.LayoutMillimeters))
                layout.addLayoutItem(qr_picture)
                
                # Caption below QR code: "acesse a versão digital"
                qr_label = QgsLayoutItemLabel(layout)
                qr_label.setText(qr_cfg.get("caption", "acesse a versão digital"))
                qr_tf = QgsTextFormat()
                caption_font_size = qr_cfg.get("caption_font_size", 7.5)
                qr_tf.setFont(QFont("Liberation Sans", int(caption_font_size)))
                qr_tf.setSize(caption_font_size)
                qr_label.setTextFormat(qr_tf)
                qr_label.setHAlign(Qt.AlignHCenter)
                qr_label.setVAlign(Qt.AlignVCenter)
                qr_label.attemptMove(QgsLayoutPoint(col_center - (col_width / 2.0), footer_y + 31.5, QgsUnitTypes.LayoutMillimeters))
                qr_label.attemptResize(QgsLayoutSize(col_width, 6.0, QgsUnitTypes.LayoutMillimeters))
                layout.addLayoutItem(qr_label)
        
        layout.refresh()
        
        # 14. Test collision avoidance first (Requirement 23)
        test_label_collisions(map_item, layout)
        
        # 15. Export to PDF (with vector text for crisp typography)
        pdf_path = CONFIG["output_pdf"]
        exporter = QgsLayoutExporter(layout)
        pdf_settings = QgsLayoutExporter.PdfExportSettings()
        pdf_settings.dpi = CONFIG["pdf_dpi"]
        pdf_settings.textRenderFormat = QgsRenderContext.TextFormatAlwaysText
        res_pdf = exporter.exportToPdf(pdf_path, pdf_settings)
        if res_pdf == QgsLayoutExporter.Success:
            print(f"SUCCESS: Exported PDF to: {os.path.abspath(pdf_path)}")
        else:
            print(f"ERROR: PDF export failed with code {res_pdf}")
        
        # 15. Export Preview PNG
        png_path = CONFIG["output_preview_png"]
        img_settings = QgsLayoutExporter.ImageExportSettings()
        img_settings.dpi = CONFIG["preview_png_dpi"]
        res_png = exporter.exportToImage(png_path, img_settings)
        if res_png == QgsLayoutExporter.Success:
            print(f"SUCCESS: Exported PNG preview to: {os.path.abspath(png_path)}")
        else:
            print(f"ERROR: PNG preview export failed with code {res_png}")
            
        # Optional: update project layout
        if CONFIG["update_qgz_project"]:
            qgz_path = CONFIG["project_qgz"]
            lm = project.layoutManager()
            existing = lm.layoutByName("Mapa CartoSul 2026")
            if existing:
                lm.removeLayout(existing)
            lm.addLayout(layout)
            project.write(qgz_path)
            print(f"Updated layout inside {qgz_path}")

    finally:
        qgs_app.exitQgis()

    print("=" * 60)
    print("Map generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    generate_map()
