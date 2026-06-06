"""
Motor de análisis de viabilidad comercial para ViableCDMX.
Implementa la lógica de negocio basada en la Ley de Establecimientos Mercantiles (LEM).
Todos los datos se leen de data/viabilidad.db.
"""
import json
import logging

from db.database import get_raw_conn

logger = logging.getLogger(__name__)

IMPACTO_MAP = {
    "bajo impacto": "bajo", "bajo": "bajo",
    "impacto vecinal": "vecinal", "vecinal": "vecinal",
    "impacto zonal": "zonal", "zonal": "zonal",
}


def _get_conn():
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    return conn


def clasificar_impacto(giro_nombre: str, vende_alcohol: str) -> dict:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM v_giro_completo WHERE nombre_corto IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {
            "impacto": "bajo", "formato_siapem": "EM-03",
            "articulo_lem": "Art. 35 LEM", "giro_nombre": giro_nombre,
            "scian": "000000", "horario_operacion": "PERMANENTE",
        }

    mejor_match = None
    mejor_score = 0

    try:
        from fuzzywuzzy import fuzz
        giro_lower = giro_nombre.lower().strip()
        for row in rows:
            nombre = row["nombre_corto"]
            score = fuzz.partial_ratio(giro_lower, nombre.lower())
            kw = json.loads(row["keywords"]) if row.get("keywords") else []
            for k in kw:
                ks = fuzz.partial_ratio(giro_lower, k.lower())
                if ks > score:
                    score = ks
            if score > mejor_score:
                mejor_score = score
                mejor_match = row
    except ImportError:
        giro_lower = giro_nombre.lower().strip()
        for row in rows:
            if giro_lower in row["nombre_corto"].lower() or row["nombre_corto"].lower() in giro_lower:
                mejor_match = row
                break

    if mejor_match is None:
        mejor_match = rows[0]
        logger.warning(f"No se encontró match para '{giro_nombre}', usando '{mejor_match['nombre_corto']}'")

    impacto_raw = mejor_match.get("tipo_de_impacto", "Bajo Impacto")
    impacto = IMPACTO_MAP.get(impacto_raw.lower().strip(), "bajo")

    if vende_alcohol == "principal" and impacto in ["bajo", "vecinal"]:
        logger.info(f"Escalando impacto de '{impacto}' a 'zonal' por venta de alcohol como giro principal.")
        impacto = "zonal"
        formato = "EM-08"
        articulo = "Art. 27 Bis LEM (Alcohol Principal)"
    else:
        formato = mejor_match.get("formato_siapem") or "EM-03"
        articulo = mejor_match.get("articulo_lem") or "Art. 35 LEM"

    return {
        "impacto": impacto,
        "formato_siapem": formato,
        "articulo_lem": articulo,
        "giro_nombre": mejor_match["nombre_corto"],
        "scian": str(mejor_match.get("clave_scian", "000000")),
        "horario_operacion": mejor_match.get("horario_de_operación", "PERMANENTE"),
    }


def evaluar_proteccion_civil(m2: int, aforo: int) -> dict:
    exento = (m2 <= 250) and (aforo < 100)

    if exento:
        return {
            "requerido": False,
            "fundamento": "Art. 10, Ap. A, Fr. X, LEM - Exento (menor de 250 m² y menos de 100 personas)",
            "accion": "No necesitas presentar Programa Interno de Protección Civil."
        }
    else:
        razones = []
        if m2 > 250:
            razones.append(f"superficie mayor a 250 m² (tienes {m2} m²)")
        if aforo >= 100:
            razones.append(f"aforo de {aforo} o más personas")

        return {
            "requerido": True,
            "fundamento": f"Art. 10, Ap. A, Fr. X, LEM - Obligatorio por: {', '.join(razones)}",
            "accion": "Debes contratar empresa certificadora para elaborar tu Programa Interno de Protección Civil antes del registro SIAPEM."
        }


def validar_uso_suelo(giro_impacto: str, zona_tipo: str) -> dict:
    matriz = {
        "bajo": {"habitacional": True, "mixto": True, "comercial": True},
        "vecinal": {"habitacional": False, "mixto": True, "comercial": True},
        "zonal": {"habitacional": False, "mixto": False, "comercial": True}
    }

    impacto_key = giro_impacto.lower()
    zona_key = zona_tipo.lower()

    if impacto_key not in matriz:
        return {"compatible": True, "zona_tipo": zona_tipo, "accion": None}

    compatible = matriz[impacto_key].get(zona_key, False)

    if compatible:
        return {"compatible": True, "zona_tipo": zona_tipo, "accion": None}
    else:
        acciones = {
            ("vecinal", "habitacional"): (
                "Tu negocio de impacto vecinal NO es compatible con zona habitacional. "
                "Busca un local en zona mixta o comercial."
            ),
            ("zonal", "habitacional"): (
                "Tu negocio de impacto zonal NO es compatible con zona habitacional. "
                "Requieres zona comercial exclusivamente."
            ),
            ("zonal", "mixto"): (
                "Tu negocio de impacto zonal NO es compatible con zona mixta. "
                "Requieres zona comercial. Verifica con SEDUVI."
            ),
        }
        accion = acciones.get(
            (impacto_key, zona_key),
            f"Giro de impacto {giro_impacto} no compatible con zona {zona_tipo}. Consulta SEDUVI o CENPROIN."
        )
        return {"compatible": False, "zona_tipo": zona_tipo, "accion": accion}


def calcular_radar_mvp(competencia_score: int, zona_data: dict, giro_impacto: str, scian: str = None) -> dict:
    conn = _get_conn()
    try:
        renta_row = conn.execute("SELECT AVG(renta_m2) as avg FROM zonas_renta").fetchone()
        renta_promedio_cdmx = renta_row["avg"] if renta_row and renta_row["avg"] else 300
    finally:
        conn.close()

    renta_zona = zona_data.get("renta_m2", renta_promedio_cdmx)

    competencia_raw = min(competencia_score, 15)
    competencia_invertida = max(0, int(100 - (competencia_raw / 15 * 100)))

    ratio_renta = renta_zona / renta_promedio_cdmx if renta_promedio_cdmx > 0 else 1

    if ratio_renta <= 0.7:
        rentabilidad = 85
    elif ratio_renta <= 1.0:
        rentabilidad = 70
    elif ratio_renta <= 1.5:
        rentabilidad = 50
    elif ratio_renta <= 2.0:
        rentabilidad = 35
    else:
        rentabilidad = 20

    if giro_impacto == "zonal":
        rentabilidad = min(100, rentabilidad + 10)
    elif giro_impacto == "bajo":
        rentabilidad = max(0, rentabilidad - 5)

    if renta_zona <= 100:
        gastos_fijos = 85
    elif renta_zona <= 200:
        gastos_fijos = 70
    elif renta_zona <= 350:
        gastos_fijos = 50
    elif renta_zona <= 500:
        gastos_fijos = 30
    else:
        gastos_fijos = 15

    bloqueante = (competencia_invertida < 25) and (gastos_fijos < 30)

    return {
        "competencia": competencia_invertida,
        "rentabilidad": rentabilidad,
        "gastos_fijos": gastos_fijos,
        "bloqueante": bloqueante
    }


def generar_reporte_viabilidad(session_data: dict) -> str:
    giro = session_data.get("giro", "No especificado")
    alcaldia = session_data.get("alcaldia", "No especificada")
    colonia = session_data.get("colonia", "No especificada")
    m2 = session_data.get("m2", 0)
    aforo = session_data.get("aforo", 0)
    alcohol = session_data.get("alcohol", "no")
    impacto = session_data.get("impacto", "bajo")
    formato = session_data.get("formato", "EM-03")
    pc_data = session_data.get("proteccion_civil", {})
    uso_suelo = session_data.get("uso_suelo", {})
    radar = session_data.get("radar", {})
    giro_nombre_oficial = session_data.get("giro_nombre_oficial", giro)
    horario = session_data.get("horario_operacion", "")

    impacto_emojis = {"bajo": "🟢", "vecinal": "🟡", "zonal": "🔴"}
    impacto_emoji = impacto_emojis.get(impacto, "⚪")

    alcohol_textos = {
        "no": "No vende alcohol",
        "complemento": "Vende alcohol como complemento a alimentos",
        "principal": "Venta de alcohol como giro principal"
    }
    alcohol_texto = alcohol_textos.get(alcohol, alcohol)

    pc_requerido = pc_data.get("requerido", False)
    pc_texto = "Exento ✅" if not pc_requerido else "Requerido ⚠️"

    suelo_compatible = uso_suelo.get("compatible", True)
    suelo_texto = "Compatible ✅" if suelo_compatible else "Incompatible ❌"
    zona_tipo = uso_suelo.get("zona_tipo", "No determinado")

    competencia_score = radar.get("competencia", 50)
    rentabilidad_score = radar.get("rentabilidad", 50)
    gastos_score = radar.get("gastos_fijos", 50)

    def barra_progreso(score: int) -> str:
        filled = int(score / 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty + f" {score}/100"

    lineas = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "📊 REPORTE DE VIABILIDAD",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"🏪 Negocio: {giro_nombre_oficial}",
        f"📍 Ubicación: {colonia}, {alcaldia}",
        f"📐 Superficie: {m2} m²  |  👥 Aforo: {aforo} personas",
        f"🍷 Alcohol: {alcohol_texto}",
    ]

    if horario:
        lineas.append(f"🕐 Horario máximo: {horario}")

    lineas.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚖️ CLASIFICACION LEGAL (LEM)",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"{impacto_emoji} Impacto: {impacto.upper()}",
        f"📋 Formato SIAPEM: {formato}",
        f"📖 Base legal: {session_data.get('articulo_lem', 'LEM CDMX')}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "🗺️ USO DE SUELO",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"Zona: {zona_tipo.title()}",
        f"Estado: {suelo_texto}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "🛡️ PROTECCION CIVIL",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"Programa Interno: {pc_texto}",
        f"Base: {pc_data.get('fundamento', 'Art. 10, Ap. A, Fr. X, LEM')}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "📈 ANALISIS DE MERCADO",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"Ventaja competitiva:  {barra_progreso(competencia_score)}",
        f"Rentabilidad estimada: {barra_progreso(rentabilidad_score)}",
        f"Nivel de gastos fijos: {barra_progreso(gastos_score)}",
        "",
    ])

    lineas.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    lineas.append("💡 RECOMENDACIONES")
    lineas.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    lineas.append("")

    recomendaciones = []

    if not suelo_compatible:
        recomendaciones.append(
            "❌ ALERTA: El uso de suelo no es compatible con tu giro. "
            "Busca una zona adecuada antes de invertir."
        )

    if pc_requerido:
        recomendaciones.append(
            "⚠️ Necesitas contratar una empresa certificadora para tu Programa "
            "de Protección Civil. Presupuesta entre $5,000 y $30,000 MXN."
        )

    if impacto == "zonal":
        recomendaciones.append(
            "🔴 Tu negocio es de IMPACTO ZONAL. Recuerda que necesitas "
            "autorización expresa de la Alcaldía. El proceso puede tardar 30-60 dias habiles."
        )

    if competencia_score < 40:
        recomendaciones.append(
            "🔥 Alta competencia en tu zona. Considera diferenciarte o buscar "
            "otra colonia con menor saturacion del mercado."
        )

    if rentabilidad_score > 70:
        recomendaciones.append(
            "✅ La relacion costo-beneficio de la zona es favorable para tu giro."
        )
    elif rentabilidad_score < 40:
        recomendaciones.append(
            "⚠️ La renta en esta zona puede afectar tu rentabilidad. "
            "Analiza bien tus costos fijos antes de comprometerte."
        )

    if alcohol == "complemento" and impacto == "vecinal":
        recomendaciones.append(
            "ℹ️ La venta de alcohol como complemento mantiene tu clasificacion "
            "como Impacto Vecinal (EM-11). Si cambias el giro principal a alcohol, "
            "escalaras a Impacto Zonal (EM-08)."
        )

    if not recomendaciones:
        recomendaciones.append("✅ Todo en orden. Procede con tu roadmap de tramites.")

    for rec in recomendaciones:
        lineas.append(rec)
        lineas.append("")

    lineas.append("━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lineas)
