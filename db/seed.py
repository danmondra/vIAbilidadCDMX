#!/usr/bin/env python3
"""
Seed idempotente para data/viabilidad.db.
Lee los JSON legacy y pobla las tablas nuevas.
Ejecutar: python db/seed.py
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "viabilidad.db"


def _add_column_if_not_exists(cur, table, col, col_type):
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
    except sqlite3.OperationalError:
        pass


def seed_giros(cur):
    _add_column_if_not_exists(cur, "giros", "articulo_lem", "TEXT")
    _add_column_if_not_exists(cur, "giros", "formato_siapem", "TEXT")
    _add_column_if_not_exists(cur, "giros", "keywords", "TEXT")
    _add_column_if_not_exists(cur, "giros", "nombre_corto", "TEXT")

    path = DATA_DIR / "giros.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            giros = json.load(f)

        count = 0
        for g in giros:
            scian = str(g.get("scian", ""))
            cur.execute(
                """UPDATE giros SET
                    articulo_lem = ?,
                    formato_siapem = ?,
                    keywords = ?,
                    nombre_corto = ?
                WHERE CAST(clave_scian AS TEXT) = ?""",
                (
                    g.get("articulo_lem"),
                    g.get("formato_siapem"),
                    json.dumps(g.get("keywords", []), ensure_ascii=False),
                    g.get("nombre"),
                    scian,
                ),
            )
            if cur.rowcount > 0:
                count += cur.rowcount
            else:
                cur.execute(
                    """INSERT OR IGNORE INTO giros
                       (clave_scian, descripción, tipo_de_impacto, horario_de_operación,
                        articulo_lem, formato_siapem, keywords, nombre_corto)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        int(scian) if scian.isdigit() else 0,
                        g.get("descripcion", g.get("nombre", "")),
                        g.get("impacto", ""),
                        "PERMANENTE",
                        g.get("articulo_lem"),
                        g.get("formato_siapem"),
                        json.dumps(g.get("keywords", []), ensure_ascii=False),
                        g.get("nombre"),
                    ),
                )
                count += cur.rowcount

        print(f"  [OK] giros: {count} filas actualizadas/insertadas desde giros.json")
    else:
        cur.execute("UPDATE giros SET nombre_corto = clasificación WHERE nombre_corto IS NULL")
        cur.execute("UPDATE giros SET formato_siapem = 'EM-03' WHERE tipo_de_impacto LIKE '%Bajo%' AND formato_siapem IS NULL")
        cur.execute("UPDATE giros SET formato_siapem = 'EM-11' WHERE tipo_de_impacto LIKE '%Vecinal%' AND formato_siapem IS NULL")
        cur.execute("UPDATE giros SET formato_siapem = 'EM-08' WHERE tipo_de_impacto LIKE '%Zonal%' AND formato_siapem IS NULL")
        cur.execute("UPDATE giros SET articulo_lem = 'Art. 35 LEM' WHERE tipo_de_impacto LIKE '%Bajo%' AND articulo_lem IS NULL")
        cur.execute("UPDATE giros SET articulo_lem = 'Art. 19 LEM' WHERE tipo_de_impacto LIKE '%Vecinal%' AND articulo_lem IS NULL")
        cur.execute("UPDATE giros SET articulo_lem = 'Art. 27 Bis LEM' WHERE tipo_de_impacto LIKE '%Zonal%' AND articulo_lem IS NULL")
        cur.execute("UPDATE giros SET keywords = '[]' WHERE keywords IS NULL")
        print("  [OK] giros: columnas añadidas y pobladas desde datos existentes (giros.json no encontrado)")


def seed_tramites(cur):
    path = DATA_DIR / "tramites.json"
    if not path.exists():
        print("  [SKIP] tramites.json no encontrado")
        return

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tramites_pasos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            impacto TEXT NOT NULL,
            fase TEXT NOT NULL,
            paso INTEGER,
            nombre TEXT,
            descripcion TEXT,
            link TEXT,
            link_info TEXT,
            costo TEXT,
            plazo TEXT,
            obligatorio TEXT,
            condicion TEXT,
            fundamento TEXT,
            orden INTEGER
        )
    """)
    cur.execute("DELETE FROM tramites_pasos")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS siapem_formatos (
            formato TEXT PRIMARY KEY,
            impacto TEXT,
            tipo TEXT,
            titulo TEXT,
            costo TEXT,
            plazo TEXT,
            pasos_json TEXT,
            documentos_json TEXT,
            nota TEXT,
            advertencia TEXT,
            link TEXT
        )
    """)
    cur.execute("DELETE FROM siapem_formatos")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    IMPACTO_MAP = {"bajo": "bajo", "vecinal": "vecinal", "zonal": "zonal"}
    FORMATO_MAP = {"bajo": "EM-03", "vecinal": "EM-11", "zonal": "EM-08"}
    TIPO_MAP = {
        "EM-03": "Aviso de Funcionamiento",
        "EM-11": "Aviso de Funcionamiento",
        "EM-08": "Solicitud de Permiso",
    }
    TITULO_MAP = {
        "EM-03": "EM-03 - Aviso de Funcionamiento (Bajo Impacto)",
        "EM-11": "EM-11 - Aviso de Funcionamiento (Impacto Vecinal)",
        "EM-08": "EM-08 - Solicitud de Permiso (Impacto Zonal)",
    }

    pasos_count = 0
    for impacto_key in ["bajo", "vecinal", "zonal"]:
        impacto_data = data.get(impacto_key, {})
        fases = impacto_data.get("fases", {})

        for fase_key in ["fase0", "fase1", "fase2"]:
            fase_data = fases.get(fase_key, {})
            pasos = fase_data.get("pasos", [])
            for i, p in enumerate(pasos):
                obligatorio_val = p.get("obligatorio", True)
                if isinstance(obligatorio_val, bool):
                    obligatorio_str = "true" if obligatorio_val else "false"
                else:
                    obligatorio_str = str(obligatorio_val)

                cur.execute(
                    """INSERT INTO tramites_pasos
                       (impacto, fase, paso, nombre, descripcion, link, link_info,
                        costo, plazo, obligatorio, condicion, fundamento, orden)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        impacto_key,
                        fase_key,
                        p.get("paso", i),
                        p.get("nombre", ""),
                        p.get("descripcion", ""),
                        p.get("link", ""),
                        p.get("link_info", ""),
                        p.get("costo", ""),
                        p.get("plazo", ""),
                        obligatorio_str,
                        p.get("condicion", ""),
                        p.get("fundamento", ""),
                        i,
                    ),
                )
                pasos_count += 1

        fase3 = fases.get("fase3", {})
        formato = FORMATO_MAP[impacto_key]
        cur.execute(
            """INSERT OR REPLACE INTO siapem_formatos
               (formato, impacto, tipo, titulo, costo, plazo, pasos_json,
                documentos_json, nota, advertencia, link)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                formato,
                impacto_key,
                TIPO_MAP[formato],
                TITULO_MAP[formato],
                fase3.get("costo", ""),
                fase3.get("plazo", ""),
                json.dumps(fase3.get("pasos", []), ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                fase3.get("descripcion", ""),
                fase3.get("advertencia_siapem", impacto_data.get("advertencia", "")),
                fase3.get("link", "https://siapem.cdmx.gob.mx"),
            ),
        )

    print(f"  [OK] tramites_pasos: {pasos_count} filas")
    print(f"  [OK] siapem_formatos: 3 filas")


def seed_programas_apoyo(cur):
    path = DATA_DIR / "programas_apoyo.json"
    if not path.exists():
        print("  [SKIP] programas_apoyo.json no encontrado")
        return

    cur.execute("""
        CREATE TABLE IF NOT EXISTS programas_apoyo (
            id INTEGER PRIMARY KEY,
            nombre TEXT,
            organismo TEXT,
            descripcion TEXT,
            monto_max REAL,
            tipo TEXT,
            modalidad TEXT,
            tasa_interes TEXT,
            plazo_max_meses INTEGER,
            requisitos_json TEXT,
            link TEXT,
            aplica_giros_json TEXT,
            convocatoria TEXT,
            direccion TEXT,
            contacto TEXT,
            beneficios_adicionales_json TEXT,
            descuento TEXT,
            costo_renta TEXT,
            proyectos_elegibles_json TEXT,
            duracion_programa TEXT
        )
    """)
    cur.execute("DELETE FROM programas_apoyo")

    with open(path, encoding="utf-8") as f:
        programas = json.load(f)

    for p in programas:
        cur.execute(
            """INSERT OR REPLACE INTO programas_apoyo
               (id, nombre, organismo, descripcion, monto_max, tipo, modalidad,
                tasa_interes, plazo_max_meses, requisitos_json, link,
                aplica_giros_json, convocatoria, direccion, contacto,
                beneficios_adicionales_json, descuento, costo_renta,
                proyectos_elegibles_json, duracion_programa)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                p.get("id"),
                p.get("nombre"),
                p.get("organismo"),
                p.get("descripcion"),
                p.get("monto_max"),
                p.get("tipo"),
                p.get("modalidad"),
                p.get("tasa_interes"),
                p.get("plazo_max_meses"),
                json.dumps(p.get("requisitos", []), ensure_ascii=False),
                p.get("link"),
                json.dumps(p.get("aplica_giros", []), ensure_ascii=False),
                p.get("convocatoria"),
                p.get("direccion"),
                p.get("contacto"),
                json.dumps(p.get("beneficios_adicionales", []), ensure_ascii=False),
                p.get("descuento"),
                p.get("costo_renta"),
                json.dumps(p.get("proyectos_elegibles", []), ensure_ascii=False),
                p.get("duracion_programa"),
            ),
        )

    print(f"  [OK] programas_apoyo: {len(programas)} filas")


def seed_legal_rules(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS legal_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regla TEXT,
            fundamento TEXT,
            descripcion TEXT,
            aplica_impacto TEXT,
            aplica_giros_pattern TEXT,
            nivel_db INTEGER,
            obligatorio INTEGER,
            mensaje_usuario TEXT
        )
    """)
    cur.execute("DELETE FROM legal_rules")

    rules = [
        {
            "regla": "ruido",
            "fundamento": "Art. 10 LEM",
            "descripcion": "Aislantes acústicos si se superan 85 dB de día o 75 dB de noche",
            "aplica_impacto": "todos",
            "nivel_db": 85,
            "obligatorio": 1,
            "mensaje_usuario": "Si tu negocio genera ruido considerable, deberás instalar aislantes acústicos para cumplir con los límites de 85 dB diurnos y 75 dB nocturnos.",
        },
        {
            "regla": "escuela_300m",
            "fundamento": "Art. 27 Bis LEM",
            "descripcion": "Prohibido instalar giros de impacto zonal a menos de 300m de escuelas",
            "aplica_impacto": "zonal",
            "nivel_db": 300,
            "obligatorio": 1,
            "mensaje_usuario": "Para giros de impacto zonal (bares, antros, casinos), se prohíbe su instalación a menos de 300m de una escuela.",
        },
        {
            "regla": "seguro_rc",
            "fundamento": "Art. 10 LEM",
            "descripcion": "Póliza de responsabilidad civil obligatoria",
            "aplica_impacto": "todos",
            "nivel_db": None,
            "obligatorio": 1,
            "mensaje_usuario": "Deberás contratar una póliza de seguro de responsabilidad civil antes de la apertura.",
        },
        {
            "regla": "horario_max",
            "fundamento": "LEM CDMX",
            "descripcion": "Horarios máximos de operación según giro (bajo impacto, vecinal, zonal)",
            "aplica_impacto": "todos",
            "nivel_db": None,
            "obligatorio": 1,
            "mensaje_usuario": "Tu giro tiene un horario máximo de operación según la ley. Consulta tu formato SIAPEM para detalles.",
        },
    ]

    for r in rules:
        cur.execute(
            """INSERT INTO legal_rules
               (regla, fundamento, descripcion, aplica_impacto,
                aplica_giros_pattern, nivel_db, obligatorio, mensaje_usuario)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                r["regla"],
                r["fundamento"],
                r["descripcion"],
                r["aplica_impacto"],
                None,
                r["nivel_db"],
                r["obligatorio"],
                r["mensaje_usuario"],
            ),
        )

    print(f"  [OK] legal_rules: {len(rules)} filas")


def seed_vista(cur):
    cur.execute("DROP VIEW IF EXISTS v_giro_completo")
    cur.execute("""
        CREATE VIEW v_giro_completo AS
        SELECT g.no, g.clave_scian, g.descripción, g.tipo_de_impacto,
               g.horario_de_operación, g.articulo_lem, g.formato_siapem,
               g.keywords, g.nombre_corto,
               r.margen_operativo
        FROM giros g
        LEFT JOIN rentabilidad_sectores r ON CAST(g.clave_scian AS TEXT) = r.scian_prefix
    """)
    print("  [OK] vista v_giro_completo creada")


def main():
    if not DB_PATH.exists():
        print(f"ERROR: No se encontró {DB_PATH}")
        sys.exit(1)

    print(f"Conectando a {DB_PATH} ...")
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    print("Sembrando giros ...")
    seed_giros(cur)

    print("Sembrando trámites ...")
    seed_tramites(cur)

    print("Sembrando programas de apoyo ...")
    seed_programas_apoyo(cur)

    print("Sembrando reglas legales ...")
    seed_legal_rules(cur)

    print("Creando vista v_giro_completo ...")
    seed_vista(cur)

    conn.commit()
    conn.close()
    print("\nSeed completado exitosamente.")


if __name__ == "__main__":
    main()
