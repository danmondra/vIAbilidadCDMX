"""
Servicio de verificación de Uso de Suelo para ViableCDMX.
Consulta data/viabilidad.db para determinar la compatibilidad del giro con la zonificación.
"""
import logging
import unicodedata

from db.database import get_raw_conn
from bot.services.viabilidad_engine import validar_uso_suelo

logger = logging.getLogger(__name__)


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _get_conn():
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    return conn


def _normalizar_alcaldia(alcaldia_input: str) -> str:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT DISTINCT alcaldia FROM catalogo_cp").fetchall()
    finally:
        conn.close()

    entrada = _strip_accents(alcaldia_input.lower().strip())
    for row in rows:
        nombre = row["alcaldia"]
        if not nombre:
            continue
        nombre_norm = _strip_accents(nombre.lower())
        if entrada == nombre_norm or entrada in nombre_norm or nombre_norm in entrada:
            return nombre
    return alcaldia_input.strip()


def _infer_zona_tipo(uso_descripcion: str) -> str:
    if not uso_descripcion:
        return "mixto"
    uso_lower = uso_descripcion.lower()
    if "habitacional" in uso_lower and "comercio" not in uso_lower and "servicio" not in uso_lower:
        return "habitacional"
    if any(k in uso_lower for k in ["comercio", "centro de barrio", "servicio", "mixto"]):
        return "mixto"
    if any(k in uso_lower for k in ["industria", "equipamiento"]):
        return "comercial"
    return "mixto"


def _obtener_zona_tipo(alcaldia: str, colonia: str) -> tuple:
    conn = _get_conn()
    try:
        alcaldia_normal = _normalizar_alcaldia(alcaldia)
        search_alc = _strip_accents(alcaldia_normal.lower())
        search_col = _strip_accents(colonia.lower()) if colonia else None

        all_cps = conn.execute("SELECT codigo_postal, colonia, alcaldia FROM catalogo_cp").fetchall()

        cp_rows = []
        if search_col:
            for r in all_cps:
                if (search_col in _strip_accents((r["colonia"] or "").lower()) and
                    search_alc in _strip_accents((r["alcaldia"] or "").lower())):
                    cp_rows.append(r)
                    if len(cp_rows) >= 5:
                        break

        if not cp_rows:
            for r in all_cps:
                if search_alc in _strip_accents((r["alcaldia"] or "").lower()):
                    cp_rows.append(r)
                    if len(cp_rows) >= 10:
                        break

        if not cp_rows:
            logger.info(f"Alcaldía '{alcaldia}' no encontrada en catalogo_cp.")
            return "mixto", 300, "Estimación (alcaldía no encontrada)"

        cps = [r["codigo_postal"] for r in cp_rows]
        placeholders = ",".join("?" * len(cps))

        uso_row = conn.execute(
            f"""SELECT uso_descripcion, COUNT(*) as cnt FROM uso_suelo
                WHERE codigo_postal IN ({placeholders})
                GROUP BY uso_descripcion ORDER BY cnt DESC LIMIT 1""",
            cps,
        ).fetchone()

        uso_descripcion = uso_row["uso_descripcion"] if uso_row else None
        zona_tipo = _infer_zona_tipo(uso_descripcion)

        renta_row = conn.execute(
            f"""SELECT AVG(renta_m2) as avg_renta FROM zonas_renta
                WHERE codigo_postal IN ({placeholders})""",
            cps,
        ).fetchone()
        renta_m2 = round(renta_row["avg_renta"], 1) if renta_row and renta_row["avg_renta"] else 300

        fuente = f"DB catalogo_cp ({len(cps)} CPs)"
        if colonia and uso_descripcion:
            fuente += f" - {colonia}"

        return zona_tipo, renta_m2, fuente
    finally:
        conn.close()


def verificar_compatibilidad(alcaldia: str, colonia: str, impacto: str) -> dict:
    zona_tipo, renta_m2, fuente = _obtener_zona_tipo(alcaldia, colonia)

    zona_map = {
        "habitacional": "habitacional",
        "residencial": "habitacional",
        "mixto": "mixto",
        "comercial": "comercial",
        "industrial": "mixto",
        "corredor_comercial": "comercial",
    }
    zona_tipo_normalizado = zona_map.get(zona_tipo.lower(), "mixto")

    resultado = validar_uso_suelo(impacto, zona_tipo_normalizado)

    return {
        "compatible": resultado["compatible"],
        "zona_tipo": zona_tipo,
        "accion": resultado.get("accion"),
        "fuente": fuente,
        "renta_m2": renta_m2
    }
