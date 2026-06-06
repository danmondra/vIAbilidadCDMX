"""
Servicio de IA para ViableCDMX.
Usa Anthropic Claude para clasificar giros y responder preguntas sobre trámites.
Los giros se cargan de data/viabilidad.db.
"""
import logging
import os

from db.database import get_raw_conn

logger = logging.getLogger(__name__)


def _cargar_lista_giros() -> list:
    conn = get_raw_conn()
    conn.row_factory = lambda cursor, row: dict(
        zip([col[0] for col in cursor.description], row)
    )
    try:
        rows = conn.execute(
            "SELECT DISTINCT nombre_corto FROM giros WHERE nombre_corto IS NOT NULL ORDER BY nombre_corto"
        ).fetchall()
        return [r["nombre_corto"] for r in rows]
    finally:
        conn.close()


def _get_anthropic_client():
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY no configurada.")
            return None
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.warning("Librería anthropic no instalada.")
        return None


def clasificar_giro_libre(texto: str) -> str:
    client = _get_anthropic_client()
    if client is None:
        logger.info("Cliente Anthropic no disponible. Devolviendo texto original.")
        return texto.strip()

    lista_giros = _cargar_lista_giros()
    if not lista_giros:
        return texto.strip()

    lista_str = ", ".join(lista_giros)

    try:
        mensaje = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=50,
            system=(
                "Eres un asistente que clasifica giros comerciales en CDMX. "
                "Dado un texto libre, devuelve ÚNICAMENTE el nombre del giro más cercano "
                f"de esta lista: {lista_str}. "
                "Solo devuelve el nombre exacto de la lista, sin explicación, "
                "sin punto final, sin comillas."
            ),
            messages=[
                {"role": "user", "content": f"Clasifica este negocio: {texto}"}
            ]
        )

        giro_clasificado = mensaje.content[0].text.strip()

        giro_lower = giro_clasificado.lower()
        for nombre in lista_giros:
            if giro_lower == nombre.lower():
                return nombre

        for nombre in lista_giros:
            if giro_lower in nombre.lower() or nombre.lower() in giro_lower:
                return nombre

        return giro_clasificado

    except Exception as e:
        logger.error(f"Error al llamar a Anthropic API para clasificar giro: {e}")
        return texto.strip()


def responder_pregunta_tramite(pregunta: str) -> str:
    client = _get_anthropic_client()

    fallback_message = (
        "Lo siento, no puedo procesar tu pregunta en este momento.\n\n"
        "Para obtener ayuda personalizada, contacta al:\n\n"
        "🏢 Centro Promotor de Inversión (CENPROIN)\n"
        "📍 Av. Cuauhtémoc 899, Col. Narvarte, Alcaldía Benito Juárez\n"
        "🕐 Lunes a viernes, 9:00 a 14:30 horas\n"
        "📧 dudas.siapem@sedeco.cdmx.gob.mx\n"
        "🌐 siapem.cdmx.gob.mx"
    )

    if client is None:
        return fallback_message

    system_context = """Eres un asesor virtual especializado en la apertura de negocios en la
Ciudad de México. Tu conocimiento se basa en:

1. LEY DE ESTABLECIMIENTOS MERCANTILES (LEM CDMX):
   - Art. 35: Negocios de BAJO IMPACTO (estéticas, papelerías, abarrotes, cafeterías, fondas)
   - Art. 19: Negocios de IMPACTO VECINAL (restaurantes, hoteles, salones de fiestas, gimnasios)
   - Art. 27 Bis: Negocios de IMPACTO ZONAL (bares, cantinas, antros, casinos)
   - Art. 10, Ap. A, Fr. X: Exención de Protección Civil (< 250 m² Y < 100 personas)

2. SISTEMA SIAPEM (siapem.cdmx.gob.mx):
   - EM-03: Aviso de Funcionamiento para Bajo Impacto (gratuito, inmediato)
   - EM-11: Aviso de Funcionamiento para Impacto Vecinal (pago Art. 191 Fr. I)
   - EM-08: Solicitud de PERMISO para Impacto Zonal (pago Art. 191 Fr. II + autorización Alcaldía)

3. TRÁMITES PREVIOS:
   - Llave CDMX: obligatoria para cualquier trámite (llave.cdmx.gob.mx)
   - CUS SEDUVI: Certificado Único de Zonificación, vigencia 1 año
   - Constancias de no adeudo predial y agua: solo para Impacto Vecinal y Zonal
   - Programa Interno de Protección Civil: solo si > 250 m² o >= 100 personas

4. MIGRACIÓN SIAPEM:
   - Para usuarios con registro anterior: NO dar de alta como nuevo negocio
   - Usar "Dar de alta establecimiento con Clave Única"
   - Adjuntar trámites anteriores escaneados (EM-03, EM-B, EM-11, EM-A, EM-08)

5. CONTACTOS:
   - CENPROIN: Av. Cuauhtémoc 899, Narvarte, Benito Juárez. L-V 9:00-14:30
   - Email SIAPEM: dudas.siapem@sedeco.cdmx.gob.mx
   - SIAPEM: siapem.cdmx.gob.mx
   - CUS SEDUVI: certificadodigital.cdmx.gob.mx
   - No adeudos: data.finanzas.cdmx.gob.mx/formato_lc

Los datos de giros, zonas, competencia y trámites se consultan de la base de datos consolidada.
Responde SIEMPRE en español. Sé conciso y claro. Usa emojis para hacer el texto más legible
en Telegram. NO uses Markdown con asteriscos o guiones bajos. Usa texto plano con emojis."""

    try:
        mensaje = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system_context,
            messages=[
                {"role": "user", "content": pregunta}
            ]
        )

        return mensaje.content[0].text.strip()

    except Exception as e:
        logger.error(f"Error al llamar a Anthropic API para responder pregunta: {e}")
        return fallback_message
