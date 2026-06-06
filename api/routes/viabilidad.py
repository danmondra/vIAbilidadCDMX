import json
import unicodedata
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fuzzywuzzy import fuzz, process

from api.models import ViabilidadRequest, ViabilidadResponse
from db.database import get_raw_conn

router = APIRouter()


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _get_conn():
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    return conn


def _find_giro_db(conn, query: str) -> Optional[dict]:
    rows = conn.execute(
        "SELECT * FROM v_giro_completo WHERE nombre_corto IS NOT NULL"
    ).fetchall()
    if not rows:
        return None

    nombres = [r["nombre_corto"] for r in rows]
    match = process.extractOne(query, nombres, scorer=fuzz.token_set_ratio)
    if match is None or match[1] < 30:
        return None

    return next((r for r in rows if r["nombre_corto"] == match[0]), None)


def _resolve_cp(conn, alcaldia: str, colonia: Optional[str]) -> dict:
    cp_rows = []
    search_alc = _strip_accents(alcaldia.lower())
    search_col = _strip_accents(colonia.lower()) if colonia else None

    all_cps = conn.execute("SELECT codigo_postal, colonia, alcaldia FROM catalogo_cp").fetchall()

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
        return {"cps": [], "alcaldia_found": None, "colonia_found": None}

    return {
        "cps": [r["codigo_postal"] for r in cp_rows],
        "alcaldia_found": cp_rows[0]["alcaldia"],
        "colonia_found": cp_rows[0]["colonia"] if colonia else None,
    }


def _calc_uso_suelo(zona_tipo: str, impacto: str) -> dict:
    compatible = True
    advertencia = None

    if zona_tipo == "habitacional":
        if impacto == "zonal":
            compatible = False
            advertencia = (
                "Zona predominantemente habitacional. El impacto zonal es muy "
                "restrictivo en este tipo de zona; es probable que no sea compatible "
                "con el uso de suelo. Solicita el CUS SEDUVI para confirmar."
            )
        elif impacto == "vecinal":
            advertencia = (
                "Zona habitacional. Verifica con el CUS SEDUVI que el giro está "
                "permitido; en algunos casos se requiere dictamen adicional."
            )
    elif zona_tipo == "mixto":
        if impacto == "zonal":
            advertencia = (
                "Zona mixta. En general compatible, pero confirma con el CUS SEDUVI "
                "para establecimientos de impacto zonal."
            )

    return {
        "zona_tipo": zona_tipo,
        "compatible": compatible,
        "advertencia": advertencia,
        "link_cus": "http://certificadodigital.cdmx.gob.mx:8080/CertificadoDigital/certificado/solicitaCertificado",
        "nota": "Verificación definitiva requiere CUS SEDUVI vigente.",
    }


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


@router.post(
    "/viabilidad",
    response_model=ViabilidadResponse,
    summary="Análisis completo de viabilidad para un negocio",
)
def post_viabilidad(req: ViabilidadRequest):
    conn = _get_conn()
    try:
        giro = _find_giro_db(conn, req.giro)
        if giro is None:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró un giro que coincida con '{req.giro}'. Prueba con otro término.",
            )

        impacto_raw = giro.get("tipo_de_impacto", "Bajo Impacto")
        impacto_map = {
            "bajo impacto": "bajo", "bajo": "bajo",
            "impacto vecinal": "vecinal", "vecinal": "vecinal",
            "impacto zonal": "zonal", "zonal": "zonal",
        }
        impacto = impacto_map.get(impacto_raw.lower().strip(), "bajo")
        formato_siapem = giro.get("formato_siapem", "EM-03") or "EM-03"

        if req.alcohol == "principal":
            impacto = "zonal"
            formato_siapem = "EM-08"

        zona_info = _resolve_cp(conn, req.alcaldia, req.colonia)
        if not zona_info["cps"]:
            raise HTTPException(status_code=404, detail=f"Alcaldía '{req.alcaldia}' no encontrada.")

        cps = zona_info["cps"]
        placeholders = ",".join("?" * len(cps))

        renta_row = conn.execute(
            f"SELECT AVG(renta_m2) as avg_renta FROM zonas_renta WHERE codigo_postal IN ({placeholders})",
            cps,
        ).fetchone()
        renta_m2 = round(renta_row["avg_renta"], 1) if renta_row and renta_row["avg_renta"] else 300

        uso_row = conn.execute(
            f"""SELECT uso_descripcion, COUNT(*) as cnt FROM uso_suelo
                WHERE codigo_postal IN ({placeholders})
                GROUP BY uso_descripcion ORDER BY cnt DESC LIMIT 1""",
            cps,
        ).fetchone()
        uso_descripcion = uso_row["uso_descripcion"] if uso_row else None
        zona_tipo = _infer_zona_tipo(uso_descripcion)

        uso_suelo = _calc_uso_suelo(zona_tipo, impacto)

        scian = str(giro.get("clave_scian", ""))
        scian_prefix = scian[:4] if len(scian) >= 4 else scian

        comp_row = conn.execute(
            f"""SELECT COUNT(*) as cnt FROM competencia_denue
                WHERE CAST(scian AS TEXT) LIKE ? AND codigo_postal IN ({placeholders})""",
            [f"{scian_prefix}%"] + cps,
        ).fetchone()
        count_colonia = comp_row["cnt"] if comp_row else 0

        comp_alc_row = conn.execute(
            """SELECT COUNT(*) as cnt FROM competencia_denue
               WHERE CAST(scian AS TEXT) LIKE ? AND LOWER(alcaldia) LIKE ?""",
            (f"{scian_prefix}%", f"%{req.alcaldia.lower()}%"),
        ).fetchone()
        if not comp_alc_row or comp_alc_row["cnt"] == 0:
            comp_alc_row = conn.execute(
                """SELECT COUNT(*) as cnt FROM competencia_denue
                   WHERE CAST(scian AS TEXT) LIKE ? AND LOWER(alcaldia) LIKE ?""",
                (f"{scian_prefix}%", f"%{_strip_accents(req.alcaldia.lower())}%"),
            ).fetchone()
        count_alcaldia = comp_alc_row["cnt"] if comp_alc_row else 0

        nivel = "alto" if count_colonia >= 5 else ("medio" if count_colonia >= 3 else "bajo")
        recomendacion_map = {
            "bajo": "Baja competencia en la zona — buena oportunidad de mercado.",
            "medio": "Competencia moderada. Diferencia tu propuesta de valor.",
            "alto": "Alta saturación en la colonia. Considera una ubicación alternativa o nicho especializado.",
        }
        competencia = {
            "competidores_estimados_colonia": count_colonia,
            "competidores_estimados_alcaldia": count_alcaldia,
            "nivel_competencia": nivel,
            "recomendacion": recomendacion_map[nivel],
            "fuente": "DENUE INEGI (datos reales)",
        }

        margen_row = conn.execute(
            "SELECT margen_operativo FROM rentabilidad_sectores WHERE scian_prefix = ?",
            (scian,),
        ).fetchone()
        margen = margen_row["margen_operativo"] if margen_row else 0.35

        ingreso_mensual = renta_m2 * req.m2 * 3
        ganancia_bruta = ingreso_mensual * margen

        rentabilidad = {
            "margen_operativo_pct": round(margen * 100, 1),
            "ingreso_mensual_estimado": round(ingreso_mensual),
            "ganancia_bruta_estimada": round(ganancia_bruta),
            "nota": "Estimaciones basadas en márgenes sectoriales INEGI (EMS).",
        }

        renta_total = round(renta_m2 * req.m2)
        nomina_estimada = max(8_000, req.m2 * 25)
        servicios = max(2_000, req.m2 * 8)
        otros = round((renta_total + nomina_estimada + servicios) * 0.10)
        total_gastos = renta_total + nomina_estimada + servicios + otros

        gastos_fijos = {
            "renta_local": renta_total,
            "nomina_estimada": nomina_estimada,
            "servicios": servicios,
            "otros_gastos": otros,
            "total_mensual": total_gastos,
            "nota": "Estimación referencial. Renta basada en zonas_renta DB.",
        }

        proteccion_civil_requerida = not (req.m2 <= 250 and req.aforo < 100)

        pasos_rows = conn.execute(
            """SELECT * FROM tramites_pasos WHERE impacto = ? ORDER BY fase, orden""",
            (impacto,),
        ).fetchall()

        if not proteccion_civil_requerida:
            pasos_rows = [p for p in pasos_rows if "proteccion" not in (p.get("nombre") or "").lower()]

        fase0 = [p for p in pasos_rows if p["fase"] == "fase0"]
        fase1 = [p for p in pasos_rows if p["fase"] == "fase1"]
        fase2 = [p for p in pasos_rows if p["fase"] == "fase2"]

        siapem_row = conn.execute(
            "SELECT * FROM siapem_formatos WHERE formato = ?", (formato_siapem,)
        ).fetchone()

        fase3_data = None
        if siapem_row:
            fase3_data = {
                "formato": siapem_row["formato"],
                "costo": siapem_row["costo"],
                "plazo": siapem_row["plazo"],
                "link": siapem_row["link"],
                "nota": siapem_row["nota"],
            }

        plazo_map = {"bajo": "5-20 días hábiles", "vecinal": "10-30 días hábiles", "zonal": "45-75 días hábiles"}

        tramites = {
            "impacto": impacto,
            "fase0_preparacion": fase0,
            "fase1_prerequisitos": fase1,
            "fase2_documentos": fase2,
            "fase3_registro": fase3_data,
            "total_pasos": len(fase0) + len(fase1) + len(fase2) + (1 if fase3_data else 0),
            "plazo_estimado": plazo_map.get(impacto, "variable"),
        }

        programas_rows = conn.execute("SELECT * FROM programas_apoyo ORDER BY id").fetchall()
        programas_apoyo = []
        for p in programas_rows:
            programas_apoyo.append({
                "id": p["id"],
                "nombre": p["nombre"],
                "organismo": p["organismo"],
                "descripcion": p["descripcion"],
                "monto_max": p["monto_max"],
                "tipo": p["tipo"],
                "link": p["link"],
                "convocatoria": p["convocatoria"],
            })

        links = {
            "siapem": "https://siapem.cdmx.gob.mx/index.xhtml",
            "llave_cdmx": "https://llave.cdmx.gob.mx/",
            "cus_seduvi": "http://certificadodigital.cdmx.gob.mx:8080/CertificadoDigital/certificado/solicitaCertificado",
            "proteccion_civil": "https://www.proteccioncivil.cdmx.gob.mx/",
            "fondeso": "https://www.fondeso.cdmx.gob.mx/",
            "sedeco": "https://www.sedeco.cdmx.gob.mx/",
            "retys": "https://retys.cdmx.gob.mx/",
        }

        return ViabilidadResponse(
            impacto=impacto,
            formato_siapem=formato_siapem,
            proteccion_civil_requerida=proteccion_civil_requerida,
            uso_suelo=uso_suelo,
            competencia=competencia,
            rentabilidad=rentabilidad,
            gastos_fijos=gastos_fijos,
            tramites=tramites,
            programas_apoyo=programas_apoyo,
            links=links,
        )
    finally:
        conn.close()
