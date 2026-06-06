"""
Handlers del flujo de trámites para ViableCDMX.
Guía al usuario por las fases de trámites según su tipo de negocio.
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.states import FASE1, FASE2, FASE3_SIAPEM, CHECKLIST, MENU

logger = logging.getLogger(__name__)


def _teclado_continuar(callback_data: str = "continuar_fase") -> InlineKeyboardMarkup:
    """Crea un teclado simple de continuar."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Continuar →", callback_data=callback_data)]
    ])


async def fase1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra la Fase 1: Documentos Base (Llave CDMX + CUS SEDUVI + Protección Civil).
    """
    query = update.callback_query
    if query:
        await query.answer()

    impacto = context.user_data.get("impacto", "bajo")
    pc_data = context.user_data.get("proteccion_civil", {})
    pc_requerido = pc_data.get("requerido", False)
    giro = context.user_data.get("giro_nombre_oficial", context.user_data.get("giro", "tu negocio"))
    alcaldia = context.user_data.get("alcaldia", "")
    colonia = context.user_data.get("colonia", "")

    impacto_nombres = {"bajo": "Bajo Impacto", "vecinal": "Impacto Vecinal", "zonal": "Impacto Zonal"}
    impacto_nombre = impacto_nombres.get(impacto, impacto.title())

    ubicacion_str = f"{colonia}, {alcaldia}" if colonia and alcaldia else alcaldia or colonia

    lineas = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📋 FASE 1 - DOCUMENTOS BASE",
        f"Negocio: {giro}",
        f"Clasificacion: {impacto_nombre}",
        f"Ubicacion: {ubicacion_str}" if ubicacion_str else "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "Estos tramites son obligatorios para TODOS los negocios:",
        "",
        "1️⃣ CUENTA LLAVE CDMX",
        "   Es la puerta de entrada a todos los tramites digitales.",
        "   Si no tienes, creala en: llave.cdmx.gob.mx",
        "   Costo: GRATUITO",
        "   Tiempo: Inmediato",
        "",
        "2️⃣ CERTIFICADO UNICO DE ZONIFICACION (CUS SEDUVI)",
        "   IMPORTANTE: Este documento confirma que tu giro",
        "   esta permitido en la direccion de tu local.",
        "   Vigencia maxima: 1 año.",
        "   No firmes contrato de renta sin el antes.",
        "   Tramitar en: certificadodigital.cdmx.gob.mx",
        "   Tiempo: 5-15 dias habiles",
        "",
    ]

    # Protección Civil
    if pc_requerido:
        lineas.extend([
            "3️⃣ PROGRAMA INTERNO DE PROTECCION CIVIL ⚠️",
            "   Tu local REQUIERE este programa por:",
            f"   {pc_data.get('fundamento', 'Supera los limites de m² o aforo')}",
            "   Debes contratarlo con empresa certificadora antes del SIAPEM.",
            "   Costo: Variable ($3,000 - $15,000 MXN aprox.)",
            "   Tiempo: 10-30 dias habiles",
            "   Web: proteccioncivil.cdmx.gob.mx",
        ])
    else:
        lineas.extend([
            "3️⃣ PROTECCION CIVIL - EXENTO ✅",
            f"   {pc_data.get('fundamento', 'Exento por menos de 250 m² y menos de 100 personas')}",
            "   No necesitas este programa.",
        ])

    lineas.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ])

    # Añadir nota sobre siguiente fase
    if impacto in ["vecinal", "zonal"]:
        lineas.append("Siguiente: Pre-requisitos adicionales para tu tipo de negocio.")
    else:
        lineas.append("Siguiente: Registro en SIAPEM (directo, sin pasos adicionales).")

    mensaje = "\n".join(l for l in lineas if l != "")

    botones = [
        [InlineKeyboardButton("Continuar →", callback_data="ir_fase2")]
    ]

    if query:
        try:
            await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(botones))
        except Exception:
            await query.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(botones))
    else:
        # Llamada desde handler de texto
        await update.effective_message.reply_text(
            mensaje, reply_markup=InlineKeyboardMarkup(botones)
        )

    return FASE1


async def fase2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra la Fase 2: Pre-requisitos específicos.
    Para impacto vecinal/zonal: constancias de no adeudo.
    Para bajo impacto: saltar directo a SIAPEM.
    """
    query = update.callback_query
    if query:
        await query.answer()

    impacto = context.user_data.get("impacto", "bajo")

    # Bajo impacto no tiene Fase 2: saltar a SIAPEM
    if impacto == "bajo":
        return await siapem_handler(update, context)

    giro = context.user_data.get("giro_nombre_oficial", context.user_data.get("giro", "tu negocio"))

    impacto_nombres = {"vecinal": "Impacto Vecinal", "zonal": "Impacto Zonal"}
    impacto_nombre = impacto_nombres.get(impacto, impacto.title())

    lineas = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📋 FASE 2 - PRE-REQUISITOS ESPECIALES",
        f"Clasificacion: {impacto_nombre}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"Por ser un negocio de {impacto_nombre}, necesitas obtener:",
        "",
        "4️⃣ CONSTANCIA DE NO ADEUDO DE PREDIAL",
        "   Certifica que el inmueble no tiene deudas de predial.",
        "   Se tramita ante la Tesoreria de la CDMX.",
        "   Costo: GRATUITO",
        "   Tiempo: 1-2 dias habiles (en linea)",
        "   Link: data.finanzas.cdmx.gob.mx/formato_lc",
        "",
        "5️⃣ CONSTANCIA DE NO ADEUDO DE AGUA (SACMEX)",
        "   Certifica que el inmueble no tiene deudas de agua.",
        "   Se tramita ante el Sistema de Aguas de la CDMX.",
        "   Costo: GRATUITO",
        "   Tiempo: 1-2 dias habiles",
        "   Link: data.finanzas.cdmx.gob.mx/formato_lc",
        "",
        "💡 CONSEJO:",
        "   Estas constancias deben ser del INMUEBLE donde operaras,",
        "   no de tu domicilio personal. Asegurate de tenerlas vigentes.",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "Siguiente: Registro en SIAPEM.",
    ]

    if impacto == "zonal":
        lineas.insert(-2, "")
        lineas.insert(-2, "⚠️ RECORDATORIO ZONAL:")
        lineas.insert(-2, "   Tras el SIAPEM, la Alcaldia debe autorizar tu permiso.")
        lineas.insert(-2, "   Este proceso puede tardar 30-60 dias habiles.")

    mensaje = "\n".join(lineas)

    botones = [
        [InlineKeyboardButton("Continuar →", callback_data="ir_siapem")]
    ]

    if query:
        try:
            await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(botones))
        except Exception:
            await query.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(botones))
    else:
        await update.effective_message.reply_text(
            mensaje, reply_markup=InlineKeyboardMarkup(botones)
        )

    return FASE2


async def siapem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra las instrucciones paso a paso del registro en SIAPEM.
    Usa el formato asignado al negocio (EM-03, EM-11 o EM-08).
    """
    query = update.callback_query
    if query:
        await query.answer()

    formato = context.user_data.get("formato", "EM-03")

    try:
        from bot.services.tramites_service import get_formato_siapem_instrucciones
        instrucciones = get_formato_siapem_instrucciones(formato)
    except Exception as e:
        logger.error(f"Error al obtener instrucciones SIAPEM: {e}")
        instrucciones = (
            f"Error al cargar instrucciones para {formato}.\n\n"
            "Por favor consulta directamente en:\n"
            "siapem.cdmx.gob.mx\n\n"
            "O contacta al CENPROIN:\n"
            "📧 dudas.siapem@sedeco.cdmx.gob.mx"
        )

    botones = [
        [InlineKeyboardButton("✅ Ver checklist final", callback_data="ir_checklist")]
    ]

    if query:
        try:
            await query.edit_message_text(instrucciones, reply_markup=InlineKeyboardMarkup(botones))
        except Exception:
            await query.message.reply_text(instrucciones, reply_markup=InlineKeyboardMarkup(botones))
    else:
        await update.effective_message.reply_text(
            instrucciones, reply_markup=InlineKeyboardMarkup(botones)
        )

    return FASE3_SIAPEM


async def checklist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra el checklist final completo de todos los trámites.
    """
    query = update.callback_query
    if query:
        await query.answer()

    impacto = context.user_data.get("impacto", "bajo")
    pc_data = context.user_data.get("proteccion_civil", {})
    pc_requerido = pc_data.get("requerido", False)

    try:
        from bot.services.tramites_service import formatear_checklist
        checklist = formatear_checklist(impacto, pc_requerido)
    except Exception as e:
        logger.error(f"Error al generar checklist: {e}")
        checklist = (
            "Error al generar el checklist.\n\n"
            "Consulta directamente en siapem.cdmx.gob.mx"
        )

    botones = [
        [InlineKeyboardButton("🔍 Evaluar otro negocio", callback_data="menu_viabilidad")],
        [InlineKeyboardButton("📞 Contacto CENPROIN", callback_data="ver_cenproin")],
        [InlineKeyboardButton("🏠 Menu principal", callback_data="volver_menu")],
    ]

    if query:
        try:
            await query.edit_message_text(checklist, reply_markup=InlineKeyboardMarkup(botones))
        except Exception:
            await query.message.reply_text(checklist, reply_markup=InlineKeyboardMarkup(botones))
    else:
        await update.effective_message.reply_text(
            checklist, reply_markup=InlineKeyboardMarkup(botones)
        )

    return CHECKLIST


async def tramites_directo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler para el comando /tramites.
    Si ya hay datos del negocio, muestra la fase 1. Si no, pide el giro.
    """
    if context.user_data.get("impacto"):
        return await fase1_handler(update, context)
    else:
        from bot.handlers.viabilidad import ask_giro_handler
        await update.message.reply_text(
            "Para mostrarte los tramites, primero necesito saber que tipo de negocio tienes.\n\n"
            "Vamos a hacer una evaluacion rapida:"
        )
        return await ask_giro_handler(update, context)
