"""
Punto de entrada principal del bot ViableCDMX.
Bot de Telegram para evaluación de viabilidad de negocios en CDMX.

Usa python-telegram-bot v22 con ConversationHandler (FSM).
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Cargar variables de entorno
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Importar estados FSM
from bot.states import (
    MENU, ASK_GIRO, ASK_UBICACION, ASK_M2, ASK_AFORO, ASK_ALCOHOL,
    PROCESANDO, MOSTRAR_VIABILIDAD, CONFIRM_TRAMITES,
    FASE1, FASE2, FASE3_SIAPEM, CHECKLIST,
    MIGRACION, APOYO
)

# Importar handlers
from bot.handlers.start import start_handler, menu_handler
from bot.handlers.viabilidad import (
    ask_giro_handler,
    giro_handler,
    giro_btn_handler,
    ubicacion_handler,
    m2_handler,
    aforo_handler,
    alcohol_handler,
    viabilidad_decision_handler,
)
from bot.handlers.tramites import (
    fase1_handler,
    fase2_handler,
    siapem_handler,
    checklist_handler,
    tramites_directo_handler,
)
from bot.handlers.apoyo import apoyo_handler
from bot.handlers.migracion import migracion_handler


async def cancelar_handler(update: Update, context) -> int:
    """Cancela la conversación actual y vuelve al inicio."""
    context.user_data.clear()
    botones = [
        [InlineKeyboardButton("🔍 Evaluar mi negocio", callback_data="menu_viabilidad")],
        [InlineKeyboardButton("📋 Ver tramites", callback_data="menu_tramites")],
        [InlineKeyboardButton("💰 Programas de apoyo", callback_data="menu_apoyo")],
        [InlineKeyboardButton("🔄 Migrar registro SIAPEM", callback_data="menu_migracion")],
    ]
    await update.message.reply_text(
        "Operacion cancelada. ¿En que puedo ayudarte?",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return MENU


async def contacto_handler(update: Update, context) -> None:
    """Muestra información de contacto del CENPROIN."""
    await update.message.reply_text(
        "Centro Promotor de Inversion (CENPROIN)\n\n"
        "Para asesoria gratuita y personalizada sobre apertura de negocios:\n\n"
        "📍 Av. Cuauhtemoc 899, Col. Narvarte\n"
        "   Alcaldia Benito Juarez, CDMX\n\n"
        "🕐 Lunes a Viernes: 9:00 a 14:30 horas\n\n"
        "📧 dudas.siapem@sedeco.cdmx.gob.mx\n\n"
        "🌐 siapem.cdmx.gob.mx\n\n"
        "También puedes visitar:\n"
        "🏛️ Consultas uso de suelo: ciudadmx.cdmx.gob.mx\n"
        "📋 CUS SEDUVI: certificadodigital.cdmx.gob.mx\n"
        "💰 No adeudos: data.finanzas.cdmx.gob.mx/formato_lc"
    )


async def apoyo_cmd_handler(update: Update, context) -> int:
    """Handler para el comando /apoyo."""
    return await apoyo_handler(update, context)


async def migrar_cmd_handler(update: Update, context) -> int:
    """Handler para el comando /migrar."""
    return await migracion_handler(update, context)


async def error_handler(update: object, context) -> None:
    """Maneja errores globales del bot."""
    logger.error("Excepcion al manejar una actualizacion:", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Ocurrio un error inesperado. Por favor intenta de nuevo.\n\n"
                "Si el problema persiste, contacta al CENPROIN:\n"
                "📧 dudas.siapem@sedeco.cdmx.gob.mx\n"
                "📍 Av. Cuauhtemoc 899, Narvarte, Benito Juarez\n"
                "🕐 L-V 9:00 a 14:30 hrs"
            )
        except Exception as e:
            logger.error(f"Error al enviar mensaje de error al usuario: {e}")


async def ver_cenproin_callback(update: Update, context) -> int:
    """Muestra información de CENPROIN cuando se presiona el botón."""
    query = update.callback_query
    await query.answer()

    botones = [[InlineKeyboardButton("🏠 Menu principal", callback_data="volver_menu")]]
    await query.edit_message_text(
        "Centro Promotor de Inversion (CENPROIN)\n\n"
        "Asesoria GRATUITA y personalizada:\n\n"
        "📍 Av. Cuauhtemoc 899, Col. Narvarte\n"
        "   Alcaldia Benito Juarez, CDMX\n\n"
        "🕐 Lunes a Viernes: 9:00 a 14:30 horas\n\n"
        "📧 dudas.siapem@sedeco.cdmx.gob.mx\n\n"
        "🌐 siapem.cdmx.gob.mx",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return MENU


def construir_conversation_handler() -> ConversationHandler:
    """
    Construye y configura el ConversationHandler principal del bot.
    """
    # --- Entry Points ---
    entry_points = [
        CommandHandler("start", start_handler),
        CommandHandler("tramites", tramites_directo_handler),
    ]

    # --- States ---
    states = {
        MENU: [
            # Botones del menú principal
            CallbackQueryHandler(menu_handler, pattern="^menu_"),
            CallbackQueryHandler(menu_handler, pattern="^volver_menu$"),
            # Callbacks de uso de suelo incompatible
            CallbackQueryHandler(viabilidad_decision_handler, pattern="^suelo_"),
            # Ver CENPROIN
            CallbackQueryHandler(ver_cenproin_callback, pattern="^ver_cenproin$"),
        ],

        ASK_GIRO: [
            # Botones de giro predefinido
            CallbackQueryHandler(giro_btn_handler, pattern="^giro_"),
            # Texto libre del giro
            MessageHandler(filters.TEXT & ~filters.COMMAND, giro_handler),
        ],

        ASK_UBICACION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ubicacion_handler),
        ],

        ASK_M2: [
            CallbackQueryHandler(m2_handler, pattern="^m2_"),
        ],

        ASK_AFORO: [
            CallbackQueryHandler(aforo_handler, pattern="^aforo_"),
        ],

        ASK_ALCOHOL: [
            CallbackQueryHandler(alcohol_handler, pattern="^alcohol_"),
        ],

        MOSTRAR_VIABILIDAD: [
            CallbackQueryHandler(viabilidad_decision_handler, pattern="^viabilidad_"),
        ],

        FASE1: [
            CallbackQueryHandler(fase2_handler, pattern="^ir_fase2$"),
        ],

        FASE2: [
            CallbackQueryHandler(siapem_handler, pattern="^ir_siapem$"),
        ],

        FASE3_SIAPEM: [
            CallbackQueryHandler(checklist_handler, pattern="^ir_checklist$"),
        ],

        CHECKLIST: [
            CallbackQueryHandler(menu_handler, pattern="^menu_"),
            CallbackQueryHandler(menu_handler, pattern="^volver_menu$"),
            CallbackQueryHandler(ver_cenproin_callback, pattern="^ver_cenproin$"),
        ],

        APOYO: [
            CallbackQueryHandler(menu_handler, pattern="^menu_"),
            CallbackQueryHandler(menu_handler, pattern="^volver_menu$"),
        ],

        MIGRACION: [
            CallbackQueryHandler(menu_handler, pattern="^menu_"),
            CallbackQueryHandler(menu_handler, pattern="^volver_menu$"),
        ],
    }

    # --- Fallbacks ---
    fallbacks = [
        CommandHandler("cancelar", cancelar_handler),
        CommandHandler("start", start_handler),
    ]

    return ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=fallbacks,
        per_user=True,
        per_chat=True,
    )


def _crear_application(token: str) -> Application:
    """
    Crea y configura la Application de python-telegram-bot.
    Reutilizable tanto para polling como para webhook/FastAPI.
    """
    app = Application.builder().token(token).build()

    # Registrar ConversationHandler principal
    conv_handler = construir_conversation_handler()
    app.add_handler(conv_handler)

    # Registrar comandos adicionales (fuera del ConversationHandler)
    app.add_handler(CommandHandler("apoyo", apoyo_cmd_handler))
    app.add_handler(CommandHandler("migrar", migrar_cmd_handler))
    app.add_handler(CommandHandler("contacto", contacto_handler))

    # Registrar handler de errores
    app.add_error_handler(error_handler)

    return app


# ---------------------------------------------------------------------------
# Instancia global de Application para uso con webhook / FastAPI
# (importada por api/routes/webhook.py como `from bot.main import application`)
# ---------------------------------------------------------------------------

def _build_application() -> Application:
    """
    Construye la Application usando el token del entorno.
    Retorna None con advertencia si el token no está configurado,
    para no romper el arranque de la API en entornos sin token configurado.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning(
            "TELEGRAM_BOT_TOKEN no configurado. "
            "La integración webhook del bot no estará disponible."
        )
        return None
    try:
        return _crear_application(token)
    except Exception as e:
        logger.error(f"Error al construir Application de Telegram: {e}")
        return None


# Instancia global — se usa en api/routes/webhook.py
application: Application = _build_application()


def main() -> None:
    """
    Función principal. Configura y ejecuta el bot en modo standalone.
    Usa polling en desarrollo o webhook si se configura WEBHOOK_URL en .env.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN no configurado en variables de entorno.")
        raise ValueError(
            "Se requiere TELEGRAM_BOT_TOKEN. "
            "Configura el archivo .env con tu token de BotFather."
        )

    # Usar la instancia global o crear una nueva
    global application
    if application is None:
        application = _crear_application(token)

    # Determinar modo de ejecución
    webhook_url = os.environ.get("WEBHOOK_URL")
    port = int(os.environ.get("PORT", 8443))

    if webhook_url:
        # Modo webhook (producción)
        logger.info(f"Iniciando bot en modo WEBHOOK: {webhook_url}")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="/api/bot/webhook",
            webhook_url=f"{webhook_url}/api/bot/webhook",
        )
    else:
        # Modo polling (desarrollo)
        logger.info("Iniciando bot en modo POLLING (desarrollo)...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()
