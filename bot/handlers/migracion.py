"""
Handler de migración SIAPEM para ViableCDMX.
Guía a usuarios con registro previo en la plataforma antigua del SIAPEM.
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.states import MIGRACION, MENU

logger = logging.getLogger(__name__)

MENSAJE_MIGRACION = """━━━━━━━━━━━━━━━━━━━━━━━━
🔄 MIGRACION DE REGISTRO SIAPEM
━━━━━━━━━━━━━━━━━━━━━━━━

¿Como saber si necesitas migrar?

Si al entrar con tu Llave CDMX al SIAPEM NO encuentras los tramites o avisos que ya realizaste, entonces necesitas migrar tu registro a la nueva plataforma.

━━━━━━━━━━━━━━━━━━━━━━━━
📎 DOCUMENTOS QUE NECESITAS
━━━━━━━━━━━━━━━━━━━━━━━━

Prepara estos documentos en PDF antes de empezar:

1. Trámites anteriores escaneados:
   • Bajo Impacto: EM-03 o EM-B
   • Impacto Vecinal: EM-11 o EM-A
   • Impacto Zonal: EM-08

2. Certificado Unico de Zonificacion (CUS SEDUVI) con el que tramitaste originalmente.

3. El Aviso o Permiso con el que operabas (el documento fisico escaneado).

4. Constancias de No Adeudo de Predial y Agua (UNICAMENTE para EM-11 y EM-08).

━━━━━━━━━━━━━━━━━━━━━━━━
📋 PROCEDIMIENTO PASO A PASO
━━━━━━━━━━━━━━━━━━━━━━━━

1. Entra a: siapem.cdmx.gob.mx

2. Accede con tu Llave CDMX (esquina superior derecha).

3. Ve a la seccion "Mis negocios".

4. IMPORTANTE: NO selecciones "Dar de alta nuevo negocio".
   Selecciona la opcion:
   "Dar de alta un establecimiento que ya cuenta con Clave Unica"

5. El sistema te preguntara si tu negocio tiene el nombre que muestra. Si es correcto, da clic en Continuar.

6. Si tu negocio NO aparece en la lista, entonces selecciona "Dar de Alta un Nuevo Establecimiento".

7. Elige el tipo de persona titular: Fisica o Moral.

8. Una vez dado de alta, ve a "Mis tramites".

9. Selecciona "Registrar nuevo tramite".

10. Elige tu negocio.

11. Selecciona el tramite que le corresponde segun el impacto:
    • Bajo Impacto: EM-03 o EM-B
    • Impacto Vecinal: EM-11
    • Impacto Zonal: EM-08 o EM-A

12. Adjunta tus documentos escaneados.

13. Realiza tu tramite y descarga tu nuevo Acuse.

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ NOTA IMPORTANTE
━━━━━━━━━━━━━━━━━━━━━━━━

La migracion NO genera un tramite nuevo. Simplemente traslada tu registro anterior al nuevo sistema SIAPEM. Tus derechos adquiridos se mantienen.

━━━━━━━━━━━━━━━━━━━━━━━━
❓ ¿NECESITAS AYUDA PERSONALIZADA?
━━━━━━━━━━━━━━━━━━━━━━━━

Centro Promotor de Inversion (CENPROIN)

📍 Av. Cuauhtemoc 899, Col. Narvarte
   Alcaldia Benito Juarez

🕐 Lunes a Viernes
   9:00 a 14:30 horas

📧 dudas.siapem@sedeco.cdmx.gob.mx

🌐 siapem.cdmx.gob.mx

━━━━━━━━━━━━━━━━━━━━━━━━"""


async def migracion_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra las instrucciones de migración de registro SIAPEM.
    Para usuarios que ya tenían registro en la plataforma antigua.
    """
    query = update.callback_query
    if query:
        await query.answer()

    botones = [
        [InlineKeyboardButton("🔍 Evaluar negocio nuevo", callback_data="menu_viabilidad")],
        [InlineKeyboardButton("📋 Ver tramites", callback_data="menu_tramites")],
        [InlineKeyboardButton("🏠 Menu principal", callback_data="volver_menu")],
    ]
    teclado = InlineKeyboardMarkup(botones)

    if query:
        try:
            await query.edit_message_text(MENSAJE_MIGRACION, reply_markup=teclado)
        except Exception:
            await query.message.reply_text(MENSAJE_MIGRACION, reply_markup=teclado)
    else:
        await update.effective_message.reply_text(MENSAJE_MIGRACION, reply_markup=teclado)

    return MENU
