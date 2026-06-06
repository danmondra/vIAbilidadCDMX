import json

from fastapi import APIRouter, HTTPException

from db.database import get_raw_conn

router = APIRouter()

VALID_IMPACTOS = {"bajo", "vecinal", "zonal"}
VALID_FORMATOS = {"EM-03", "EM-11", "EM-08"}

FORMATO_TO_IMPACTO = {
    "EM-03": "bajo",
    "EM-11": "vecinal",
    "EM-08": "zonal",
}


def _get_conn():
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    return conn


@router.get(
    "/tramites/formato/{formato}",
    summary="Instrucciones detalladas para un formato SIAPEM",
)
def get_tramites_por_formato(formato: str):
    formato = formato.upper()
    if formato not in VALID_FORMATOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato inválido. Valores permitidos: {', '.join(VALID_FORMATOS)}",
        )

    impacto = FORMATO_TO_IMPACTO[formato]
    conn = _get_conn()
    try:
        siapem = conn.execute(
            "SELECT * FROM siapem_formatos WHERE formato = ?", (formato,)
        ).fetchone()

        if not siapem:
            raise HTTPException(status_code=404, detail=f"Formato {formato} no encontrado en DB.")

        pasos = json.loads(siapem["pasos_json"]) if siapem["pasos_json"] else []
        documentos = json.loads(siapem["documentos_json"]) if siapem["documentos_json"] else []

        return {
            "formato": formato,
            "impacto": impacto,
            "tipo": siapem["tipo"],
            "titulo": siapem["titulo"],
            "costo": siapem["costo"],
            "plazo": siapem["plazo"],
            "nota": siapem["nota"],
            "advertencia": siapem["advertencia"],
            "link": siapem["link"],
            "pasos": pasos,
            "documentos": documentos,
        }
    finally:
        conn.close()


@router.get(
    "/tramites/{impacto}",
    summary="Ruta de trámites para un nivel de impacto",
)
def get_tramites_por_impacto(impacto: str):
    impacto = impacto.lower()
    if impacto not in VALID_IMPACTOS:
        raise HTTPException(
            status_code=400,
            detail=f"Impacto inválido. Valores permitidos: {', '.join(VALID_IMPACTOS)}",
        )

    conn = _get_conn()
    try:
        pasos = conn.execute(
            "SELECT * FROM tramites_pasos WHERE impacto = ? ORDER BY fase, orden",
            (impacto,),
        ).fetchall()

        fase0 = [p for p in pasos if p["fase"] == "fase0"]
        fase1 = [p for p in pasos if p["fase"] == "fase1"]
        fase2 = [p for p in pasos if p["fase"] == "fase2"]

        siapem = conn.execute(
            "SELECT * FROM siapem_formatos WHERE impacto = ?", (impacto,)
        ).fetchone()

        fase3 = None
        if siapem:
            fase3 = {
                "formato": siapem["formato"],
                "costo": siapem["costo"],
                "plazo": siapem["plazo"],
                "link": siapem["link"],
                "nota": siapem["nota"],
            }

        return {
            "impacto": impacto,
            "fase0_preparacion": fase0,
            "fase1_prerequisitos": fase1,
            "fase2_documentos": fase2,
            "fase3_registro": fase3,
            "total_pasos": len(fase0) + len(fase1) + len(fase2) + (1 if fase3 else 0),
        }
    finally:
        conn.close()
