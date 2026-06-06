"""
Servicio de consulta DENUE (Directorio Estadístico Nacional de Unidades Económicas).
Busca y analiza la competencia comercial usando data/viabilidad.db.
"""
import logging
import unicodedata

from db.database import get_raw_conn

logger = logging.getLogger(__name__)


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _nivel_competencia(count: int, umbral_baja: int = 3, umbral_alta: int = 8) -> str:
    if count <= umbral_baja:
        return "baja"
    elif count <= umbral_alta:
        return "moderada"
    else:
        return "alta"


def buscar_competencia(scian: str, alcaldia: str, colonia: str = None) -> dict:
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    try:
        scian_prefix = scian[:4] if len(scian) >= 4 else scian
        search_alc = _strip_accents(alcaldia.lower())
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

        colonia_count = 0
        alcaldia_count = 0

        if cp_rows:
            cps = [r["codigo_postal"] for r in cp_rows]
            placeholders = ",".join("?" * len(cps))

            if colonia:
                row = conn.execute(
                    f"""SELECT COUNT(*) as cnt FROM competencia_denue
                        WHERE CAST(scian AS TEXT) LIKE ? AND codigo_postal IN ({placeholders})""",
                    [f"{scian_prefix}%"] + cps,
                ).fetchone()
                colonia_count = row["cnt"] if row else 0

            row_alc = conn.execute(
                """SELECT COUNT(*) as cnt FROM competencia_denue
                   WHERE CAST(scian AS TEXT) LIKE ? AND LOWER(alcaldia) LIKE ?""",
                (f"{scian_prefix}%", f"%{alcaldia.lower()}%"),
            ).fetchone()
            if row_alc and row_alc["cnt"] > 0:
                alcaldia_count = row_alc["cnt"]
            else:
                row_alc2 = conn.execute(
                    """SELECT COUNT(*) as cnt FROM competencia_denue
                       WHERE CAST(scian AS TEXT) LIKE ? AND LOWER(alcaldia) LIKE ?""",
                    (f"{scian_prefix}%", f"%{search_alc}%"),
                ).fetchone()
                alcaldia_count = row_alc2["cnt"] if row_alc2 else 0

        if colonia and colonia_count > 0:
            nivel = _nivel_competencia(colonia_count, umbral_baja=3, umbral_alta=7)
        else:
            count_normalizado = alcaldia_count // 50 if alcaldia_count else 0
            nivel = _nivel_competencia(count_normalizado, umbral_baja=2, umbral_alta=5)

        return {
            "colonia_count": colonia_count,
            "alcaldia_count": alcaldia_count,
            "nivel": nivel,
            "fuente": "DENUE INEGI (DB viabilidad.db)"
        }
    finally:
        conn.close()
