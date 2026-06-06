"""
Handler de inicio y menú principal del bot ViableCDMX.
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.states import MENU, ASK_GIRO, APOYO, MIGRACION, FASE1

logger = logging.getLogger(__name__)

MENSAJE_BIENVENIDA = (
    "Hola, soy vIAble CDMX 🏙️\n\n"
    "Tu asesor virtual para abrir negocios en la Ciudad de México.\n\n"
    "Te ayudo a:\n"
    "📊 Evaluar la viabilidad de tu negocio\n"
    "📋 Conocer los tramites legales que necesitas\n"
    "💰 Encontrar programas de apoyo\n"
    "🔄 Migrar tu registro SIAPEM anterior\n\n"
    "¿Con que quieres empezar?"
)


def _construir_teclado_menu() -> InlineKeyboardMarkup:
    """Construye el teclado del menú principal."""
    botones = [
        [InlineKeyboardButton("🔍 Evaluar mi negocio", callback_data="menu_viabilidad")],
        [InlineKeyboardButton("📋 Ver tramites directos", callback_data="menu_tramites")],
        [InlineKeyboardButton("💰 Programas de apoyo", callback_data="menu_apoyo")],
        [InlineKeyboardButton("🔄 Migrar registro SIAPEM", callback_data="menu_migracion")],
    ]
    return InlineKeyboardMarkup(botones)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Maneja el comando /start.
    Muestra el mensaje de bienvenida con el menú principal.
    """
    # Limpiar datos previos de la sesión
    context.user_data.clear()

    await update.message.reply_text(
        MENSAJE_BIENVENIDA,
        reply_markup=_construir_teclado_menu()
    )

    return MENU


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Maneja las selecciones del menú principal.
    Enruta al flujo apropiado según el callback_data.
    """
    query = update.callback_query
    await query.answer()

    callback = query.data

    if callback == "menu_viabilidad":
        await query.edit_message_text(
            "Vamos a evaluar la viabilidad de tu negocio.\n\n"
            "Te haré algunas preguntas rapidas. Tomara menos de 2 minutos.\n\n"
            "¿Que tipo de negocio quieres abrir?"
        )
        # Importar aquí para evitar importaciones circulares
        from bot.handlers.viabilidad import ask_giro_handler
        return await ask_giro_handler(update, context)

    elif callback == "menu_tramites":
        # Mostrar tramites directamente si ya tienen datos, sino pedir giro
        if context.user_data.get("impacto"):
            from bot.handlers.tramites import fase1_handler
            return await fase1_handler(update, context)
        else:
            await query.edit_message_text(
                "Para mostrarte los tramites necesito conocer tu negocio.\n\n"
                "¿Que tipo de negocio quieres abrir?"
            )
            from bot.handlers.viabilidad import ask_giro_handler
            return await ask_giro_handler(update, context)

    elif callback == "menu_apoyo":
        from bot.handlers.apoyo import apoyo_handler
        return await apoyo_handler(update, context)

    elif callback == "menu_migracion":
        from bot.handlers.migracion import migracion_handler
        return await migracion_handler(update, context)

    elif callback == "volver_menu":
        await query.edit_message_text(
            "Menu principal. ¿En que te puedo ayudar?",
            reply_markup=_construir_teclado_menu()
        )
        return MENU

    else:
        logger.warning(f"Callback no reconocido en menu_handler: {callback}")
        await query.edit_message_text(
            "No reconoci esa opcion. Volviendo al menu principal.",
            reply_markup=_construir_teclado_menu()
        )
        return MENU
