"""
Handlers del flujo de evaluación de viabilidad comercial para ViableCDMX.
Implementa la entrevista de perfilamiento y el análisis completo del negocio.
"""
import logging
import unicodedata

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.states import (
    ASK_GIRO, ASK_UBICACION, ASK_M2, ASK_AFORO, ASK_ALCOHOL,
    MOSTRAR_VIABILIDAD, MENU, FASE1
)
from db.database import get_raw_conn

logger = logging.getLogger(__name__)


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _get_alcaldias_from_db() -> list:
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    try:
        rows = conn.execute("SELECT DISTINCT alcaldia FROM catalogo_cp ORDER BY alcaldia").fetchall()
        return [r["alcaldia"] for r in rows if r["alcaldia"]]
    finally:
        conn.close()


def _get_top_giros_from_db() -> list:
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    try:
        rows = conn.execute(
            "SELECT nombre_corto FROM giros WHERE nombre_corto IS NOT NULL ORDER BY no LIMIT 8"
        ).fetchall()
        return [r["nombre_corto"] for r in rows]
    finally:
        conn.close()


def _normalizar_alcaldia(texto: str) -> str:
    alcaldias = _get_alcaldias_from_db()
    texto_norm = _strip_accents(texto.lower().strip())
    for alc in alcaldias:
        if not alc:
            continue
        alc_norm = _strip_accents(alc.lower())
        if texto_norm == alc_norm:
            return alc
    for alc in alcaldias:
        if not alc:
            continue
        alc_norm = _strip_accents(alc.lower())
        if texto_norm in alc_norm or alc_norm in texto_norm:
            return alc
    return texto.strip()


def _parsear_ubicacion(texto: str) -> tuple:
    texto_lower = texto.lower()
    texto_norm = _strip_accents(texto_lower)
    alcaldias = _get_alcaldias_from_db()
    alcaldia_encontrada = None

    for alcaldia in alcaldias:
        if not alcaldia:
            continue
        alc_norm = _strip_accents(alcaldia.lower())
        if alc_norm in texto_norm:
            alcaldia_encontrada = _normalizar_alcaldia(alcaldia)
            break

    if alcaldia_encontrada is None:
        partes = [p.strip() for p in texto.split(",")]
        if len(partes) >= 2:
            for parte in partes:
                parte_norm = _strip_accents(parte.lower())
                for alcaldia in alcaldias:
                    if not alcaldia:
                        continue
                    alc_norm = _strip_accents(alcaldia.lower())
                    if alc_norm in parte_norm:
                        alcaldia_encontrada = _normalizar_alcaldia(alcaldia)
                        colonia = next((p for p in partes if p != parte), partes[0])
                        return alcaldia_encontrada, colonia.strip()
            return partes[-1].strip(), partes[0].strip()
        else:
            return "No especificada", texto.strip()

    colonia_texto = texto_norm.replace(_strip_accents(alcaldia_encontrada.lower()), "").strip()
    colonia_texto = colonia_texto.strip(",. ")
    colonia = colonia_texto.title() if colonia_texto else "No especificada"

    return alcaldia_encontrada, colonia


async def ask_giro_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        giros_top = _get_top_giros_from_db()
    except Exception:
        giros_top = []

    GIRO_EMOJIS = {
        "Restaurante": "🍽️", "Cafetería": "☕", "Tienda de Abarrotes": "🛒",
        "Estética / Salón de Belleza": "💇", "Gimnasio": "🏋️", "Bar": "🍺",
        "Hotel": "🏨", "Salón de Fiestas": "🎪",
    }

    botones = []
    row = []
    for i, giro in enumerate(giros_top[:8]):
        emoji = GIRO_EMOJIS.get(giro, "🏪")
        row.append(InlineKeyboardButton(f"{emoji} {giro}", callback_data=f"giro_{giro}"))
        if len(row) == 2:
            botones.append(row)
            row = []
    if row:
        botones.append(row)
    botones.append([InlineKeyboardButton("✍️ Escribir otro...", callback_data="giro_otro")])

    teclado = InlineKeyboardMarkup(botones)

    texto = (
        "¿Que tipo de negocio quieres abrir?\n\n"
        "Selecciona una opcion o escribe el nombre de tu negocio:"
    )

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(texto, reply_markup=teclado)
        except Exception:
            await update.callback_query.message.reply_text(texto, reply_markup=teclado)
    else:
        await update.message.reply_text(texto, reply_markup=teclado)

    return ASK_GIRO


async def giro_btn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    callback = query.data

    if callback == "giro_otro":
        await query.edit_message_text(
            "Escribe el nombre de tu negocio. Por ejemplo:\n\n"
            "• Taqueria\n"
            "• Consultorio dental\n"
            "• Tienda de ropa\n"
            "• Panaderia artesanal"
        )
        return ASK_GIRO

    giro_nombre = callback.replace("giro_", "", 1)
    context.user_data["giro"] = giro_nombre
    context.user_data["giro_raw"] = giro_nombre

    await query.edit_message_text(
        f"Perfecto, {giro_nombre} 👍\n\n"
        "Ahora dime la ubicacion de tu local.\n\n"
        "Puedes escribir:\n"
        "• Solo la colonia (ej: Roma Norte)\n"
        "• Colonia y Alcaldia (ej: Condesa, Cuauhtemoc)\n"
        "• O la direccion completa"
    )

    return ASK_UBICACION


async def giro_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    context.user_data["giro_raw"] = texto

    try:
        from bot.services.ai_service import clasificar_giro_libre
        giro_normalizado = clasificar_giro_libre(texto)
    except Exception as e:
        logger.error(f"Error al clasificar giro con IA: {e}")
        giro_normalizado = texto

    context.user_data["giro"] = giro_normalizado

    await update.message.reply_text(
        f"Entendido, registro el negocio como: {giro_normalizado} 👍\n\n"
        "Ahora dime la ubicacion de tu local.\n\n"
        "Puedes escribir:\n"
        "• Solo la colonia (ej: Roma Norte)\n"
        "• Colonia y Alcaldia (ej: Condesa, Cuauhtemoc)\n"
        "• O la direccion completa"
    )

    return ASK_UBICACION


async def ubicacion_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()

    alcaldia, colonia = _parsear_ubicacion(texto)
    context.user_data["alcaldia"] = alcaldia
    context.user_data["colonia"] = colonia
    context.user_data["ubicacion_raw"] = texto

    if alcaldia != "No especificada" and colonia != "No especificada":
        confirmacion = f"Ubicacion registrada: {colonia}, {alcaldia} 📍"
    elif alcaldia != "No especificada":
        confirmacion = f"Ubicacion registrada: {alcaldia} 📍"
    else:
        confirmacion = f"Ubicacion registrada: {texto} 📍\n(Si quieres ser mas especifico, puedes indicar la alcaldia)"

    botones = [
        [
            InlineKeyboardButton("📐 Menos de 250 m²", callback_data="m2_menos250"),
            InlineKeyboardButton("📐 Mas de 250 m²", callback_data="m2_mas250"),
        ],
        [InlineKeyboardButton("❓ No se exactamente", callback_data="m2_nosé")],
    ]

    await update.message.reply_text(
        f"{confirmacion}\n\n"
        "¿Cual es la superficie aproximada de tu local?",
        reply_markup=InlineKeyboardMarkup(botones)
    )

    return ASK_M2


async def m2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    opciones_m2 = {
        "m2_menos250": (150, "Menos de 250 m²"),
        "m2_mas250": (300, "Mas de 250 m²"),
        "m2_nosé": (150, "No especificado"),
    }

    m2_val, m2_texto = opciones_m2.get(query.data, (150, "No especificado"))
    context.user_data["m2"] = m2_val
    context.user_data["m2_texto"] = m2_texto

    botones = [
        [
            InlineKeyboardButton("👥 Menos de 100 personas", callback_data="aforo_menos100"),
            InlineKeyboardButton("👥 Mas de 100 personas", callback_data="aforo_mas100"),
        ],
        [InlineKeyboardButton("❓ No se", callback_data="aforo_nose")],
    ]

    await query.edit_message_text(
        f"Superficie: {m2_texto} ✅\n\n"
        "¿Cual es el aforo maximo esperado?\n"
        "(Cantidad de personas que pueden estar en el local al mismo tiempo)",
        reply_markup=InlineKeyboardMarkup(botones)
    )

    return ASK_AFORO


async def aforo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    opciones_aforo = {
        "aforo_menos100": (50, "Menos de 100 personas"),
        "aforo_mas100": (150, "Mas de 100 personas"),
        "aforo_nose": (50, "No especificado"),
    }

    aforo_val, aforo_texto = opciones_aforo.get(query.data, (50, "No especificado"))
    context.user_data["aforo"] = aforo_val
    context.user_data["aforo_texto"] = aforo_texto

    botones = [
        [InlineKeyboardButton("🚫 No vendo alcohol", callback_data="alcohol_no")],
        [InlineKeyboardButton("🍷 Si, como complemento a comida", callback_data="alcohol_complemento")],
        [InlineKeyboardButton("🍺 Si, es mi giro principal", callback_data="alcohol_principal")],
    ]

    await query.edit_message_text(
        f"Aforo: {aforo_texto} ✅\n\n"
        "¿Tu negocio vende bebidas alcoholicas?",
        reply_markup=InlineKeyboardMarkup(botones)
    )

    return ASK_ALCOHOL


async def alcohol_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    opciones_alcohol = {
        "alcohol_no": "no",
        "alcohol_complemento": "complemento",
        "alcohol_principal": "principal",
    }

    alcohol = opciones_alcohol.get(query.data, "no")
    context.user_data["alcohol"] = alcohol

    await query.edit_message_text(
        "⏳ Analizando la viabilidad de tu negocio...\n\n"
        "Consultando base de datos de giros, uso de suelo y competencia."
    )

    try:
        giro = context.user_data.get("giro", "Negocio")
        alcaldia = context.user_data.get("alcaldia", "No especificada")
        colonia = context.user_data.get("colonia", "No especificada")
        m2 = context.user_data.get("m2", 150)
        aforo = context.user_data.get("aforo", 50)

        from bot.services.viabilidad_engine import (
            clasificar_impacto, evaluar_proteccion_civil,
            calcular_radar_mvp, generar_reporte_viabilidad
        )
        from bot.services.suelo_service import verificar_compatibilidad
        from bot.services.denue_service import buscar_competencia

        clasificacion = clasificar_impacto(giro, alcohol)
        impacto = clasificacion["impacto"]
        formato = clasificacion["formato_siapem"]

        context.user_data["impacto"] = impacto
        context.user_data["formato"] = formato
        context.user_data["articulo_lem"] = clasificacion["articulo_lem"]
        context.user_data["scian"] = clasificacion["scian"]
        context.user_data["giro_nombre_oficial"] = clasificacion["giro_nombre"]
        context.user_data["horario_operacion"] = clasificacion.get("horario_operacion", "")

        pc_data = evaluar_proteccion_civil(m2, aforo)
        context.user_data["proteccion_civil"] = pc_data

        uso_suelo = verificar_compatibilidad(alcaldia, colonia, impacto)
        context.user_data["uso_suelo"] = uso_suelo

        scian = clasificacion["scian"]
        competencia_data = buscar_competencia(scian, alcaldia, colonia)
        competencia_count = competencia_data.get("colonia_count", 4)

        zona_data_para_radar = {
            "renta_m2": uso_suelo.get("renta_m2", 300)
        }
        radar = calcular_radar_mvp(competencia_count, zona_data_para_radar, impacto, scian)
        context.user_data["radar"] = radar
        context.user_data["competencia"] = competencia_data

        session_para_reporte = dict(context.user_data)
        session_para_reporte["giro"] = giro
        reporte = generar_reporte_viabilidad(session_para_reporte)
        context.user_data["reporte"] = reporte

        if not uso_suelo.get("compatible", True):
            botones_incompatible = [
                [InlineKeyboardButton("🔍 Buscar otra zona", callback_data="suelo_buscar_zona")],
                [InlineKeyboardButton("🔄 Cambiar giro", callback_data="suelo_cambiar_giro")],
                [InlineKeyboardButton("📞 Consultar CENPROIN", callback_data="suelo_cenproin")],
            ]

            accion_texto = uso_suelo.get("accion", "El uso de suelo no es compatible con tu giro.")

            await query.message.reply_text(
                f"⚠️ ALERTA DE USO DE SUELO\n\n"
                f"{reporte}\n\n"
                f"❌ {accion_texto}\n\n"
                f"Te recomiendo verificar directamente en:\n"
                f"ciudadmx.cdmx.gob.mx:8080/seduvi\n\n"
                f"¿Que deseas hacer?",
                reply_markup=InlineKeyboardMarkup(botones_incompatible)
            )
            return MENU

        botones_viabilidad = [
            [InlineKeyboardButton("✅ Si, ver mi Roadmap de Tramites", callback_data="viabilidad_continuar")],
            [InlineKeyboardButton("🔄 Cambiar datos", callback_data="viabilidad_reiniciar")],
        ]

        await query.message.reply_text(
            reporte + "\n\n¿Continuo con tu Roadmap de Tramites?",
            reply_markup=InlineKeyboardMarkup(botones_viabilidad)
        )

        return MOSTRAR_VIABILIDAD

    except Exception as e:
        logger.error(f"Error en el análisis de viabilidad: {e}", exc_info=True)
        await query.message.reply_text(
            "Lo siento, ocurrio un error al analizar tu negocio.\n\n"
            "Por favor intenta de nuevo o contacta al CENPROIN:\n"
            "📧 dudas.siapem@sedeco.cdmx.gob.mx\n"
            "📍 Av. Cuauhtemoc 899, Narvarte"
        )
        return MENU


async def viabilidad_decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    callback = query.data

    if callback == "viabilidad_continuar":
        from bot.handlers.tramites import fase1_handler
        return await fase1_handler(update, context)

    elif callback == "viabilidad_reiniciar":
        await query.edit_message_text(
            "Vamos a empezar de nuevo con tu informacion.\n\n"
            "¿Que tipo de negocio quieres abrir?"
        )
        context.user_data.clear()
        return await ask_giro_handler(update, context)

    elif callback == "suelo_buscar_zona":
        await query.edit_message_text(
            "Para buscar una zona compatible, te recomiendo:\n\n"
            "1. Consultar el mapa de uso de suelo de SEDUVI:\n"
            "   ciudadmx.cdmx.gob.mx:8080/seduvi\n\n"
            "2. Buscar zonas MIXTAS o COMERCIALES en la alcaldia de tu preferencia.\n\n"
            "3. Una vez que tengas una nueva direccion, regresa y evalua de nuevo.\n\n"
            "¿Quieres evaluar con otra ubicacion?"
        )
        context.user_data.pop("alcaldia", None)
        context.user_data.pop("colonia", None)
        return await ask_giro_handler(update, context)

    elif callback == "suelo_cambiar_giro":
        await query.edit_message_text(
            "Entendido. Vamos a buscar un giro compatible con la zona.\n\n"
            "Recuerda que en zonas habitacionales solo se permiten negocios de BAJO IMPACTO "
            "(estéticas, papelerías, abarrotes, etc.)\n\n"
            "¿Que tipo de negocio quieres evaluar ahora?"
        )
        context.user_data.pop("giro", None)
        context.user_data.pop("impacto", None)
        return await ask_giro_handler(update, context)

    elif callback == "suelo_cenproin":
        botones_volver = [
            [InlineKeyboardButton("🔙 Volver al menu", callback_data="volver_menu")],
        ]
        await query.edit_message_text(
            "Centro Promotor de Inversion (CENPROIN)\n\n"
            "Los expertos del CENPROIN pueden ayudarte a determinar la compatibilidad "
            "de uso de suelo de forma gratuita y personalizada.\n\n"
            "📍 Av. Cuauhtemoc 899, Col. Narvarte\n"
            "   Alcaldia Benito Juarez\n\n"
            "🕐 Horario: Lunes a Viernes\n"
            "   9:00 a 14:30 horas\n\n"
            "📧 dudas.siapem@sedeco.cdmx.gob.mx\n\n"
            "🌐 siapem.cdmx.gob.mx",
            reply_markup=InlineKeyboardMarkup(botones_volver)
        )
        return MENU

    else:
        logger.warning(f"Callback no reconocido en viabilidad_decision_handler: {callback}")
        return MOSTRAR_VIABILIDAD
