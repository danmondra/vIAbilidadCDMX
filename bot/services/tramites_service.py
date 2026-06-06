"""
Servicio de trámites para ViableCDMX.
Genera roadmaps y checklists de trámites desde data/viabilidad.db.
"""
import json
import logging

from db.database import get_raw_conn

logger = logging.getLogger(__name__)


def _get_conn():
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    return conn


def generar_roadmap(impacto: str, proteccion_civil: bool) -> list:
    conn = _get_conn()
    try:
        pasos = conn.execute(
            "SELECT * FROM tramites_pasos WHERE impacto = ? ORDER BY fase, orden",
            (impacto,),
        ).fetchall()

        if not proteccion_civil:
            pasos = [p for p in pasos if "proteccion" not in (p.get("nombre") or "").lower()]

        roadmap = []
        fase_labels = {
            "fase0": "Fase 0 - Preparación",
            "fase1": "Fase 1 - Documentos Base",
            "fase2": "Fase 2 - Pre-requisitos",
        }

        for p in pasos:
            paso_dict = {
                "paso": p["paso"],
                "descripcion": p["nombre"] or "",
                "detalle": p["descripcion"] or "",
                "link": p["link"] or "",
                "costo": p["costo"] or "Variable",
                "plazo": p["plazo"] or "Consultar",
                "obligatorio": p["obligatorio"] != "false",
                "fase": fase_labels.get(p["fase"], p["fase"]),
            }

            if "proteccion" in (p.get("nombre") or "").lower() and not proteccion_civil:
                paso_dict["obligatorio"] = False
                paso_dict["descripcion"] = "Protección Civil (EXENTO)"
                paso_dict["detalle"] = "Tu negocio está exento por tener menos de 250 m² y menos de 100 personas."

            roadmap.append(paso_dict)

        siapem = conn.execute(
            "SELECT * FROM siapem_formatos WHERE impacto = ?", (impacto,)
        ).fetchone()

        if siapem:
            roadmap.append({
                "paso": 99,
                "descripcion": f"Registro SIAPEM ({siapem['formato']})",
                "detalle": siapem["nota"] or "",
                "link": siapem["link"] or "https://siapem.cdmx.gob.mx/",
                "costo": siapem["costo"] or "Gratuito",
                "plazo": siapem["plazo"] or "Variable",
                "obligatorio": True,
                "fase": "Fase 3 - Registro SIAPEM",
                "formato": siapem["formato"],
            })

        return sorted(roadmap, key=lambda x: x["paso"])
    finally:
        conn.close()


def formatear_checklist(impacto: str, proteccion_civil: bool) -> str:
    impacto_nombres = {"bajo": "Bajo Impacto", "vecinal": "Impacto Vecinal", "zonal": "Impacto Zonal"}
    impacto_formatos = {"bajo": "EM-03", "vecinal": "EM-11", "zonal": "EM-08"}
    impacto_nombre = impacto_nombres.get(impacto, impacto.title())
    formato = impacto_formatos.get(impacto, "EM-03")

    lineas = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ CHECKLIST FINAL - {impacto_nombre}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "Marca cada punto antes de ir al SIAPEM:",
        "",
        "📌 FASE 1 - DOCUMENTOS BASE",
        "",
        "☐ Cuenta Llave CDMX activa y funcionando",
        "   llave.cdmx.gob.mx",
        "",
        "☐ Certificado Unico de Zonificacion (CUS SEDUVI)",
        "   Vigencia maxima: 1 año",
        "   certificadodigital.cdmx.gob.mx",
        "",
    ]

    if proteccion_civil:
        lineas.extend([
            "☐ Programa Interno de Proteccion Civil",
            "   Elaborado por empresa certificadora autorizada",
            "   proteccioncivil.cdmx.gob.mx",
            "",
        ])
    else:
        lineas.extend([
            "✅ Proteccion Civil - EXENTO",
            "   (menos de 250 m² Y menos de 100 personas)",
            "   Art. 10, Ap. A, Fr. X, LEM",
            "",
        ])

    if impacto in ["vecinal", "zonal"]:
        lineas.extend([
            "📌 FASE 2 - PRE-REQUISITOS ESPECIALES",
            "",
            "☐ Constancia de No Adeudo de Predial",
            "   Tramitar ante Tesoreria CDMX",
            "   data.finanzas.cdmx.gob.mx/formato_lc",
            "",
            "☐ Constancia de No Adeudo de Agua (SACMEX)",
            "   Tramitar ante SACMEX",
            "   data.finanzas.cdmx.gob.mx/formato_lc",
            "",
        ])

    lineas.extend([
        "📌 FASE 3 - REGISTRO SIAPEM",
        "",
        f"☐ Ingresar a SIAPEM: siapem.cdmx.gob.mx",
        "☐ 'Mis negocios' → 'Dar de alta nuevo negocio'",
        "☐ Llenar datos de persona Fisica o Moral",
        "☐ 'Mis tramites' → 'Registrar nuevo tramite'",
        f"☐ Seleccionar formato {formato}",
        "☐ Registrar informacion solicitada",
    ])

    if impacto == "bajo":
        lineas.extend([
            "☐ Descargar e imprimir Acuse (SIN costo)",
            "",
        ])
    elif impacto == "vecinal":
        lineas.extend([
            "☐ Pagar linea de captura de derechos",
            "   (Art. 191, Fraccion I, Codigo Fiscal CDMX)",
            "☐ Descargar e imprimir Acuse",
            "",
        ])
    elif impacto == "zonal":
        lineas.extend([
            "☐ Pagar linea de captura de derechos",
            "   (Art. 191, Fraccion II, Codigo Fiscal CDMX)",
            "☐ Esperar autorizacion expresa de la Alcaldia",
            "   (Plazo estimado: 30-60 dias habiles)",
            "☐ Descargar e imprimir Acuse tras autorizacion",
            "",
        ])

    lineas.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "❓ Dudas: dudas.siapem@sedeco.cdmx.gob.mx",
        "🏢 CENPROIN: Av. Cuauhtemoc 899, Narvarte",
        "   Lunes a Viernes 9:00 - 14:30 hrs",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ])

    return "\n".join(lineas)


def get_formato_siapem_instrucciones(formato: str) -> str:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM siapem_formatos WHERE formato = ?", (formato,)
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return (
            f"No se encontraron instrucciones para {formato} en la base de datos.\n\n"
            "Consulta directamente en siapem.cdmx.gob.mx"
        )

    pasos = json.loads(row["pasos_json"]) if row["pasos_json"] else []
    documentos = json.loads(row["documentos_json"]) if row["documentos_json"] else []

    lineas = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📋 {row['titulo']}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📄 Tipo: {row['tipo']}",
        f"💰 Costo: {row['costo']}",
        f"⏱ Plazo: {row['plazo']}",
        "",
        "📝 PROCEDIMIENTO PASO A PASO:",
        "",
    ]

    for i, paso in enumerate(pasos, 1):
        lineas.append(f"{i}. {paso}")

    if documentos:
        lineas.extend(["", "📎 DOCUMENTOS QUE NECESITAS:", ""])
        for doc in documentos:
            lineas.append(f"• {doc}")

    if row.get("nota"):
        lineas.extend(["", "ℹ️ NOTA IMPORTANTE:", row["nota"]])

    if row.get("advertencia"):
        lineas.extend(["", "⚠️ ADVERTENCIA:", row["advertencia"]])

    lineas.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🌐 {row['link'] or 'siapem.cdmx.gob.mx'}",
        "📧 dudas.siapem@sedeco.cdmx.gob.mx",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ])

    return "\n".join(lineas)
