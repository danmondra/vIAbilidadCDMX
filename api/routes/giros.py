import json
from typing import List

from fastapi import APIRouter, Depends, Query
from fuzzywuzzy import fuzz, process
from sqlalchemy.orm import Session

from api.models import GiroBusquedaResponse
from db.database import get_db, get_raw_conn

router = APIRouter()


@router.get("/giros", summary="Lista todos los giros disponibles")
def get_giros():
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    try:
        rows = conn.execute(
            "SELECT * FROM v_giro_completo WHERE nombre_corto IS NOT NULL"
        ).fetchall()
        results = []
        for r in rows:
            kw = r.get("keywords")
            results.append({
                "nombre": r["nombre_corto"],
                "scian": str(r["clave_scian"]),
                "impacto": r["tipo_de_impacto"],
                "formato_siapem": r.get("formato_siapem", ""),
                "articulo_lem": r.get("articulo_lem", ""),
                "descripcion": r.get("descripción", ""),
                "keywords": json.loads(kw) if kw else [],
                "horario_operacion": r.get("horario_de_operación", ""),
                "margen_operativo": r.get("margen_operativo"),
            })
        return results
    finally:
        conn.close()


@router.get(
    "/giros/buscar",
    response_model=List[GiroBusquedaResponse],
    summary="Búsqueda difusa de giros por nombre",
)
def buscar_giros(q: str = Query(..., min_length=1, description="Término de búsqueda")):
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    try:
        rows = conn.execute(
            "SELECT * FROM v_giro_completo WHERE nombre_corto IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    nombres = [r["nombre_corto"] for r in rows]
    matches = process.extract(q, nombres, scorer=fuzz.token_set_ratio, limit=5)

    results = []
    for match in matches:
        match_nombre = match[0]
        score = match[1]
        if score < 30:
            continue
        row = next((r for r in rows if r["nombre_corto"] == match_nombre), None)
        if row:
            impacto_raw = row.get("tipo_de_impacto", "")
            impacto_map = {
                "bajo impacto": "bajo", "bajo": "bajo",
                "impacto vecinal": "vecinal", "vecinal": "vecinal",
                "impacto zonal": "zonal", "zonal": "zonal",
            }
            impacto = impacto_map.get(impacto_raw.lower().strip(), impacto_raw.lower().strip())

            results.append(
                GiroBusquedaResponse(
                    nombre=row["nombre_corto"],
                    scian=str(row["clave_scian"]),
                    impacto=impacto,
                    formato_siapem=row.get("formato_siapem", ""),
                )
            )
    return results
