import unicodedata
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from db.database import get_raw_conn

router = APIRouter()


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


@router.get("/zonas", summary="Lista todas las alcaldías y colonias")
def get_zonas():
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    try:
        rows = conn.execute(
            "SELECT DISTINCT alcaldia, colonia FROM catalogo_cp ORDER BY alcaldia, colonia"
        ).fetchall()

        result = {}
        for r in rows:
            alc = r["alcaldia"].title() if r["alcaldia"] else "Desconocida"
            col = r["colonia"] or ""
            if alc not in result:
                result[alc] = []
            result[alc].append(col)

        return [
            {"alcaldia": alc, "colonias": cols}
            for alc, cols in sorted(result.items())
        ]
    finally:
        conn.close()


@router.get("/competencia", summary="Datos de competencia por giro y zona")
def get_competencia(
    scian: str = Query(..., description="Código SCIAN del giro"),
    alcaldia: str = Query(..., description="Nombre de la alcaldía"),
    colonia: Optional[str] = Query(None, description="Nombre de la colonia (opcional)"),
):
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

        if not cp_rows:
            raise HTTPException(
                status_code=404,
                detail=f"Alcaldía '{alcaldia}' no encontrada en catálogo.",
            )

        cps = [r["codigo_postal"] for r in cp_rows]
        placeholders = ",".join("?" * len(cps))

        count_colonia = 0
        if colonia:
            row = conn.execute(
                f"""SELECT COUNT(*) as cnt FROM competencia_denue
                    WHERE CAST(scian AS TEXT) LIKE ? AND codigo_postal IN ({placeholders})""",
                [f"{scian_prefix}%"] + cps,
            ).fetchone()
            count_colonia = row["cnt"] if row else 0

        row_alc = conn.execute(
            """SELECT COUNT(*) as cnt FROM competencia_denue
               WHERE CAST(scian AS TEXT) LIKE ? AND LOWER(alcaldia) LIKE ?""",
            (f"{scian_prefix}%", f"%{alcaldia.lower()}%"),
        ).fetchone()
        if row_alc and row_alc["cnt"] > 0:
            count_alcaldia = row_alc["cnt"]
        else:
            row_alc2 = conn.execute(
                """SELECT COUNT(*) as cnt FROM competencia_denue
                   WHERE CAST(scian AS TEXT) LIKE ? AND LOWER(alcaldia) LIKE ?""",
                (f"{scian_prefix}%", f"%{search_alc}%"),
            ).fetchone()
            count_alcaldia = row_alc2["cnt"] if row_alc2 else 0

        renta_m2 = None
        if cps:
            row_renta = conn.execute(
                f"""SELECT AVG(renta_m2) as avg_renta FROM zonas_renta
                    WHERE codigo_postal IN ({placeholders})""",
                cps,
            ).fetchone()
            renta_m2 = round(row_renta["avg_renta"], 1) if row_renta and row_renta["avg_renta"] else None

        uso_descripcion = None
        if cps:
            row_uso = conn.execute(
                f"""SELECT uso_descripcion, COUNT(*) as cnt FROM uso_suelo
                    WHERE codigo_postal IN ({placeholders})
                    GROUP BY uso_descripcion ORDER BY cnt DESC LIMIT 1""",
                cps,
            ).fetchone()
            uso_descripcion = row_uso["uso_descripcion"] if row_uso else None

        nivel = "alto" if count_colonia >= 5 else ("medio" if count_colonia >= 3 else "bajo")
        if not colonia:
            norm = count_alcaldia // 50
            nivel = "alto" if norm >= 5 else ("medio" if norm >= 3 else "bajo")

        return {
            "scian": scian,
            "alcaldia": alcaldia,
            "colonia": colonia,
            "competidores_estimados_colonia": count_colonia,
            "competidores_estimados_alcaldia": count_alcaldia,
            "nivel_competencia": nivel,
            "renta_m2": renta_m2,
            "uso_suelo_descripcion": uso_descripcion,
            "fuente": "DENUE INEGI (datos reales)",
        }
    finally:
        conn.close()
