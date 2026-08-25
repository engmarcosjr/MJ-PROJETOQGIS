import os
import sys
import json
import sqlite3
import shapely.wkb
import shapely.geometry

# Configuração de Layers, Cores ACI e Lineweights
LAYER_CONFIG = {
    'Rede_Lote': {'aci': 72, 'lw': 20},
    'Rede_Quadra': {'aci': 32, 'lw': 30},
    'Rede_Meio_Fio': {'aci': 221, 'lw': 25},
    'Logradouro': {'aci': 8, 'lw': 18},
    'Curva_Nivel_Mestra': {'aci': 30, 'lw': 35},
    'Curva_Nivel_Intermediaria': {'aci': 64, 'lw': 15},
    'Nos': {'aci': 7, 'lw': 25},
    'Rede_DN50': {'aci': 4, 'lw': 40},
    'Rede_DN75': {'aci': 3, 'lw': 40},
    'Rede_DN100': {'aci': 1, 'lw': 50},
    'Rede_DN150': {'aci': 5, 'lw': 50},
    'Rede_DN200': {'aci': 6, 'lw': 50},
    'Rede_DN250': {'aci': 14, 'lw': 60},
    'Rede_DN300': {'aci': 5, 'lw': 60},
}

def gpkg_to_shapely(gpkg_blob):
    if not gpkg_blob:
        return None
    flags = gpkg_blob[3]
    envelope_type = (flags >> 1) & 0x07
    env_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    offset = 8 + env_sizes.get(envelope_type, 0)
    wkb = gpkg_blob[offset:]
    return shapely.wkb.loads(wkb)

def get_polygons_from_geom(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    elif geom.geom_type == 'MultiPolygon':
        return list(geom.geoms)
    elif geom.geom_type == 'GeometryCollection':
        polys = []
        for g in geom.geoms:
            polys.extend(get_polygons_from_geom(g))
        return polys
    return []

def get_lines_from_geom(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type in ['LineString', 'LinearRing']:
        return [geom]
    elif geom.geom_type == 'MultiLineString':
        return list(geom.geoms)
    elif geom.geom_type == 'GeometryCollection':
        lines = []
        for g in geom.geoms:
            lines.extend(get_lines_from_geom(g))
        return lines
    return []

def get_points_from_geom(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == 'Point':
        return [geom]
    elif geom.geom_type == 'MultiPoint':
        return list(geom.geoms)
    elif geom.geom_type == 'GeometryCollection':
        pts = []
        for g in geom.geoms:
            pts.extend(get_points_from_geom(g))
        return pts
    return []

def format_hatch_solid(layer_name, polygon):
    """Gera bloco HATCH SOLID com formatação 100% compatível com AutoCAD R2000+"""
    lines = []
    
    # Boundary paths count = 1 exterior + N interiors (holes)
    rings = [polygon.exterior] + list(polygon.interiors)
    
    lines.extend([
        "  0", "HATCH",
        "  8", layer_name,
        " 10", "0.0",
        " 20", "0.0",
        " 30", "0.0",
        "210", "0.0",
        "220", "0.0",
        "230", "1.0",
        "  2", "SOLID",
        " 70", "1",      # Solid fill flag
        " 71", "0",      # Associativity flag (non-associative)
        " 91", str(len(rings)) # Number of boundary paths
    ])
    
    for i, ring in enumerate(rings):
        coords = list(ring.coords)
        if len(coords) > 1 and coords[0] == coords[-1]:
            coords = coords[:-1]
        
        flag = 1 if i == 0 else 0  # 1 = external loop (or default), 0 = inner loop
        lines.extend([
            " 92", str(flag),
            " 72", "0",      # Polyline path flag
            " 73", "1",      # Closed flag
            " 93", str(len(coords))
        ])
        for x, y in coords:
            lines.extend([
                " 10", f"{x:.4f}",
                " 20", f"{y:.4f}"
            ])
        lines.append(" 97")
        lines.append("0")    # Number of source boundary objects
    
    lines.extend([
        " 75", "0",          # Hatch style: Normal
        " 76", "1",          # Hatch pattern type: predefined
        " 98", "0"           # Number of seed points
    ])
    return lines

def format_lwpolyline(layer_name, line_geom, closed=False):
    coords = list(line_geom.coords)
    if closed and len(coords) > 1 and coords[0] == coords[-1]:
        coords = coords[:-1]
    
    lines = [
        "  0", "LWPOLYLINE",
        "  8", layer_name,
        " 90", str(len(coords)),
        " 70", "1" if closed else "0"
    ]
    for pt in coords:
        lines.extend([
            " 10", f"{pt[0]:.4f}",
            " 20", f"{pt[1]:.4f}"
        ])
    return lines

def format_point(layer_name, point_geom):
    return [
        "  0", "POINT",
        "  8", layer_name,
        " 10", f"{point_geom.x:.4f}",
        " 20", f"{point_geom.y:.4f}",
        " 30", "0.0"
    ]

def export_recorte_dxf(
    urb_gpkg_path,
    agua_gpkg_path,
    extent_bbox, # (xmin, ymin, xmax, ymax)
    output_dxf_path
):
    xmin, ymin, xmax, ymax = extent_bbox
    clip_box = shapely.geometry.box(xmin, ymin, xmax, ymax)
    
    print(f"=== INICIANDO EXPORTAÇÃO RECORTADA ===")
    print(f"Envelope BBOX: {xmin}, {ymin} até {xmax}, {ymax}")
    
    # 1. Carregar e Recortar Camadas do Urb_Aps_Final
    urb_conn = sqlite3.connect(urb_gpkg_path)
    urb_cursor = urb_conn.cursor()
    
    # Polígonos de Quadras, Lotes, Meio-Fio
    quadras = []
    lotes = []
    meio_fios = []
    logradouros = []
    mestra = []
    intermediaria = []
    
    # Quadras
    urb_cursor.execute('SELECT geom FROM "3_quadra"')
    for row in urb_cursor.fetchall():
        g = gpkg_to_shapely(row[0])
        if g and g.intersects(clip_box):
            clipped = g.intersection(clip_box)
            quadras.extend(get_polygons_from_geom(clipped))
            
    # Lotes
    urb_cursor.execute('SELECT geom FROM "2_lote"')
    for row in urb_cursor.fetchall():
        g = gpkg_to_shapely(row[0])
        if g and g.intersects(clip_box):
            clipped = g.intersection(clip_box)
            lotes.extend(get_polygons_from_geom(clipped))

    # Meio Fio
    urb_cursor.execute('SELECT geom FROM "4_meio_fio"')
    for row in urb_cursor.fetchall():
        g = gpkg_to_shapely(row[0])
        if g and g.intersects(clip_box):
            clipped = g.intersection(clip_box)
            meio_fios.extend(get_polygons_from_geom(clipped))
            
    # Logradouro
    urb_cursor.execute('SELECT geom FROM "logradouro"')
    for row in urb_cursor.fetchall():
        g = gpkg_to_shapely(row[0])
        if g and g.intersects(clip_box):
            clipped = g.intersection(clip_box)
            logradouros.extend(get_lines_from_geom(clipped))
            
    # Curvas de Nível Mestra
    urb_cursor.execute('SELECT geom FROM "8_Curva_de_Nivel_Mestra"')
    for row in urb_cursor.fetchall():
        g = gpkg_to_shapely(row[0])
        if g and g.intersects(clip_box):
            clipped = g.intersection(clip_box)
            mestra.extend(get_lines_from_geom(clipped))
            
    # Curvas de Nível Intermediária
    urb_cursor.execute('SELECT geom FROM "8_Curva_de_Nivel_Intermediaria"')
    for row in urb_cursor.fetchall():
        g = gpkg_to_shapely(row[0])
        if g and g.intersects(clip_box):
            clipped = g.intersection(clip_box)
            intermediaria.extend(get_lines_from_geom(clipped))
            
    urb_conn.close()
    
    # 2. Carregar e Recortar Camadas de Água
    agua_conn = sqlite3.connect(agua_gpkg_path)
    agua_cursor = agua_conn.cursor()
    
    redes_by_dn = {}
    agua_cursor.execute('SELECT geom, cat_dnom FROM "v_edit_arc_54b78599_6794_4b48_aa73_deda35d35771"')
    for row in agua_cursor.fetchall():
        g = gpkg_to_shapely(row[0])
        dn = row[1]
        if g and g.intersects(clip_box):
            clipped = g.intersection(clip_box)
            dn_str = str(dn).strip() if dn else "50"
            layer_dn = f"Rede_DN{dn_str}"
            if layer_dn not in redes_by_dn:
                redes_by_dn[layer_dn] = []
            redes_by_dn[layer_dn].extend(get_lines_from_geom(clipped))
            
    nos = []
    agua_cursor.execute('SELECT geom FROM "v_edit_node_cb9a467c_5e78_4c1f_8c11_ea1081d05975"')
    for row in agua_cursor.fetchall():
        g = gpkg_to_shapely(row[0])
        if g and g.intersects(clip_box):
            clipped = g.intersection(clip_box)
            nos.extend(get_points_from_geom(clipped))
            
    agua_conn.close()
    
    print(f"Feições recortadas extraídas:")
    print(f"  - Quadras: {len(quadras)} polígonos")
    print(f"  - Lotes: {len(lotes)} polígonos")
    print(f"  - Meio-Fio: {len(meio_fios)} polígonos")
    print(f"  - Logradouros: {len(logradouros)} linhas")
    print(f"  - Curvas Mestras: {len(mestra)} linhas clippadas")
    print(f"  - Curvas Intermediárias: {len(intermediaria)} linhas clippadas")
    for dn_layer, lines in sorted(redes_by_dn.items()):
        print(f"  - {dn_layer}: {len(lines)} trechos")
    print(f"  - Nós: {len(nos)} pontos")
    
    # 3. Montar Arquivo DXF R2000 (AC1015) Completo
    dxf_lines = []
    
    # Header com $FILLMODE = 1 e $LWDISPLAY = 1
    dxf_lines.extend([
        "  0", "SECTION",
        "  2", "HEADER",
        "  9", "$ACADVER",
        "  1", "AC1015",
        "  9", "$EXTMIN",
        " 10", f"{xmin:.4f}",
        " 20", f"{ymin:.4f}",
        " 30", "0.0",
        "  9", "$EXTMAX",
        " 10", f"{xmax:.4f}",
        " 20", f"{ymax:.4f}",
        " 30", "0.0",
        "  9", "$FILLMODE",
        " 70", "1",
        "  9", "$LWDISPLAY",
        " 70", "1",
        "  9", "$DRAWORDERCTL",
        " 70", "3",
        "  0", "ENDSEC"
    ])
    
    # Tables & Layers
    active_layers = set(['0', 'Rede_Quadra', 'Rede_Lote', 'Rede_Meio_Fio', 'Logradouro', 'Curva_Nivel_Mestra', 'Curva_Nivel_Intermediaria', 'Nos'])
    active_layers.update(redes_by_dn.keys())
    
    dxf_lines.extend([
        "  0", "SECTION",
        "  2", "TABLES",
        "  0", "TABLE",
        "  2", "LAYER",
        " 70", str(len(active_layers))
    ])
    
    # Layer 0
    dxf_lines.extend([
        "  0", "LAYER",
        "  2", "0",
        " 70", "0",
        " 62", "7",
        "  6", "CONTINUOUS"
    ])
    
    for l_name in sorted(active_layers):
        if l_name == '0':
            continue
        cfg = LAYER_CONFIG.get(l_name, {'aci': 7, 'lw': 25})
        dxf_lines.extend([
            "  0", "LAYER",
            "  2", l_name,
            " 70", "0",
            " 62", str(cfg['aci']),
            "  6", "CONTINUOUS",
            "370", str(cfg['lw'])
        ])
        
    dxf_lines.extend([
        "  0", "ENDTAB",
        "  0", "ENDSEC"
    ])
    
    # ENTITIES: Ordenadas estritamente de baixo para cima (Draw Order)
    dxf_lines.extend([
        "  0", "SECTION",
        "  2", "ENTITIES"
    ])
    
    # ORDEM 1: Hachuras Sólidas no Fundo (Quadras -> Lotes -> Meio-Fio)
    for q in quadras:
        dxf_lines.extend(format_hatch_solid('Rede_Quadra', q))
    for l in lotes:
        dxf_lines.extend(format_hatch_solid('Rede_Lote', l))
    for mf in meio_fios:
        dxf_lines.extend(format_hatch_solid('Rede_Meio_Fio', mf))
        
    # ORDEM 2: Contornos Poligonais das Quadras, Lotes e Meio-Fio
    for q in quadras:
        dxf_lines.extend(format_lwpolyline('Rede_Quadra', q.exterior, closed=True))
    for l in lotes:
        dxf_lines.extend(format_lwpolyline('Rede_Lote', l.exterior, closed=True))
    for mf in meio_fios:
        dxf_lines.extend(format_lwpolyline('Rede_Meio_Fio', mf.exterior, closed=True))
        
    # ORDEM 3: Logradouros
    for lg in logradouros:
        dxf_lines.extend(format_lwpolyline('Logradouro', lg))
        
    # ORDEM 4: Curvas de Nível Clippadas no Retângulo do Recorte
    for c_int in intermediaria:
        dxf_lines.extend(format_lwpolyline('Curva_Nivel_Intermediaria', c_int))
    for c_mes in mestra:
        dxf_lines.extend(format_lwpolyline('Curva_Nivel_Mestra', c_mes))
        
    # ORDEM 5: Redes de Água Separadas por Diâmetro Nominal
    for dn_layer, lines in sorted(redes_by_dn.items()):
        for r_line in lines:
            dxf_lines.extend(format_lwpolyline(dn_layer, r_line))
            
    # ORDEM 6: Nós da Rede
    for n_pt in nos:
        dxf_lines.extend(format_point('Nos', n_pt))
        
    dxf_lines.extend([
        "  0", "ENDSEC",
        "  0", "EOF"
    ])
    
    with open(output_dxf_path, 'w', encoding='cp1252', errors='replace') as f:
        f.write('\n'.join(dxf_lines) + '\n')
        
    print(f"\n✅ SUCESSO ABSOLUTO! DXF Gerado com Hachuras Sólidas e Clipping Estrito em:")
    print(f"👉 {output_dxf_path}")

if __name__ == '__main__':
    export_recorte_dxf(
        urb_gpkg_path="/Volumes/Mac_Dados/Urb-Anápolis/Urb_Aps_Final.gpkg",
        agua_gpkg_path="/Volumes/Mac_Dados/Downloads/QGIS_AGUA_OFF - Copia/data.gpkg",
        extent_bbox=(720234.495, 8192330.572, 720472.095, 8192498.572),
        output_dxf_path="/Volumes/Mac_Dados/Downloads/sicob_COMPLETO_FINAL.dxf"
    )
