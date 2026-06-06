"""
Handler de programas de apoyo para ViableCDMX.
Muestra programas de financiamiento, crédito y asesoría desde data/viabilidad.db.
"""
import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.states import APOYO, MENU
from db.database import get_raw_conn

logger = logging.getLogger(__name__)


def _cargar_programas() -> list:
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    try:
        rows = conn.execute("SELECT * FROM programas_apoyo ORDER BY id").fetchall()
        resultados = []
        for r in rows:
            emoji_map = {
                "capital_semilla": "🌱",
                "credito_preferencial": "💰",
                "credito_pyme": "🏦",
                "beneficio_fiscal": "📉",
                "programa_compras_gobierno": "🏛️",
                "espacio_comercial": "🏪",
                "programa_integral_mujer": "👩",
                "financiamiento_sustentable": "🌿",
                "asesoria_gratuita": "🤝",
                "incubacion_negocio": "🚀",
            }
            tipo = r.get("tipo", "")
            emoji = emoji_map.get(tipo, "📌")

            monto = "Variable"
            if r.get("monto_max") and r["monto_max"] > 0:
                monto = f"Hasta ${r['monto_max']:,.0f} MXN"
            elif r.get("descuento"):
                monto = r["descuento"]
            elif r.get("costo_renta"):
                monto = r["costo_renta"]
            elif tipo == "asesoria_gratuita" or tipo == "servicio_gratuito":
                monto = "Gratuito"

            resultados.append({
                "nombre": r["nombre"],
                "descripcion": r["descripcion"] or "",
                "monto": monto,
                "link": r["link"] or "",
                "tipo": tipo,
                "emoji": emoji,
                "direccion": r.get("direccion", ""),
                "contacto": r.get("contacto", ""),
                "organismo": r.get("organismo", ""),
            })
        return resultados
    finally:
        conn.close()


async def apoyo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    programas = _cargar_programas()

    lineas = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "💰 PROGRAMAS DE APOYO PARA EMPRENDEDORES CDMX",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "Aqui encontraras los principales apoyos disponibles:",
        "",
    ]

    for i, programa in enumerate(programas, 1):
        emoji = programa.get("emoji", "📌")
        nombre = programa.get("nombre", "Programa")
        descripcion = programa.get("descripcion", "")
        monto = programa.get("monto", "Variable")
        link = programa.get("link", "")
        tipo = programa.get("tipo", "")

        lineas.append(f"{i}. {emoji} {nombre}")
        if tipo:
            lineas.append(f"   Tipo: {tipo}")
        lineas.append(f"   {descripcion}")
        lineas.append(f"   Monto: {monto}")

        if programa.get("direccion"):
            lineas.append(f"   Direccion: {programa['direccion']}")
        if programa.get("contacto"):
            lineas.append(f"   Contacto: {programa['contacto']}")

        if link:
            lineas.append(f"   Web: {link}")

        lineas.append("")

    lineas.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "💡 CONSEJO:",
        "Visita el CENPROIN para asesoria GRATUITA y personalizada",
        "sobre cual programa es mejor para tu caso.",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ])

    mensaje = "\n".join(lineas)

    botones = [
        [InlineKeyboardButton("← Volver al menu", callback_data="volver_menu")],
        [InlineKeyboardButton("🔍 Evaluar mi negocio", callback_data="menu_viabilidad")],
    ]
    teclado = InlineKeyboardMarkup(botones)

    if query:
        try:
            await query.edit_message_text(mensaje, reply_markup=teclado)
        except Exception:
            await query.message.reply_text(mensaje, reply_markup=teclado)
    else:
        await update.effective_message.reply_text(mensaje, reply_markup=teclado)

    return APOYO
