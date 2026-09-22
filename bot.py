import os
import sys
import logging
import asyncio
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Asegurar codificación UTF-8 en consola de Windows para emojis y caracteres especiales
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configurar logging detallado
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Modelo de Gemini a utilizar (con soporte verificado para url_context)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

# URLs oficiales de GeniusBet como fuente de verdad
URL_TERMS = "https://www.geniusbet.sv/help/terms-of-conditions"
URL_HOME = "https://www.geniusbet.sv/home"
URL_PROMOS = "https://www.geniusbet.sv/promos"

# Validar credenciales al inicio
if not TELEGRAM_TOKEN:
    raise ValueError("Error: TELEGRAM_TOKEN no encontrado en las variables de entorno.")
if not GEMINI_API_KEY:
    raise ValueError("Error: GEMINI_API_KEY no encontrado en las variables de entorno.")


# ============================================================
# CONSULTA A GEMINI CON GROUNDING (url_context) Y TONO NATURAL
# ============================================================
async def consultar_gemini(consulta_usuario: str) -> str:
    """
    Envía la consulta del usuario a Gemini con la herramienta url_context
    y un prompt estricto de grounding pero con tono natural y conversacional.
    """
    prompt = f"""Eres el asistente virtual oficial de atención y experiencia al cliente de GeniusBet El Salvador.
Tu personalidad es cálida, amable, cercana, entusiasta y muy profesional. Tu objetivo es hacer que cada jugador se sienta bienvenido y resuelva sus inquietudes con total claridad.

FUENTES DE INFORMACIÓN OFICIALES (Lee y fundamenta tus respuestas en estas páginas web):
1. Términos y Condiciones: {URL_TERMS}
2. Página Principal y Juegos: {URL_HOME}
3. Promociones y Bonos: {URL_PROMOS}

DIRECTRICES PARA UNA CONVERSACIÓN NATURAL Y PRECISA:
- Saluda de manera agradable y fluida si el usuario te saluda o inicia la charla (ejemplo: "¡Hola! Con gusto te ayudo con eso...", "¡Qué tal! Excelente pregunta...").
- Cuando pregunten sobre promociones, bonos, torneos o beneficios, resalta los aspectos más atractivos (premios, vigencia, requisitos de apuesta/rollover y pasos para participar) de manera dinámica y motivadora.
- Cuando la consulta sea sobre aspectos legales, límites de edad, verificación de cuenta, depósitos o retiros, explica las normas de forma sencilla y transparente, citando la sección o regla correspondiente si aporta claridad.
- Utiliza un formato limpio y legible con viñetas, negritas y emojis discretos que hagan la lectura agradable en Telegram.
- REGLA DE VERACIDAD (GROUNDING): Basa toda tu información estrictamente en el contenido de las 3 páginas web indicadas. No inventes promociones ni inventes datos de contacto.
- SI LA INFORMACIÓN NO ESTÁ EN LAS PÁGINAS: No respondas de forma fría ni robótica. Di algo amable y colaborativo como:
  "Por el momento no dispongo de ese detalle específico en nuestros términos oficiales ni en el catálogo de promociones. Para darte una solución exacta, te sugiero comunicarte con nuestro equipo de soporte en vivo directamente en GeniusBet.sv. ¡Con gusto te atenderán!"

Consulta del usuario:
{consulta_usuario}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"url_context": {}}],
    }

    async with httpx.AsyncClient(timeout=95.0) as client:
        response = await client.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                return "".join(text_parts).strip()
            return "No se pudo extraer una respuesta del modelo."
        
        elif response.status_code == 429:
            logger.warning("Cuota de Gemini excedida (429).")
            return (
                "⚠️ ¡Hola! En este momento estamos recibiendo un volumen alto de consultas. "
                "Por favor, intenta nuevamente en un minuto para ayudarte con todo gusto. 🙏"
            )
        else:
            logger.error(f"Error de Gemini API [{response.status_code}]: {response.text}")
            return (
                f"❌ Disculpa, ocurrió un pequeño inconveniente al consultar la información ({response.status_code}). "
                "Por favor intenta de nuevo en unos momentos."
            )


# ============================================================
# MANEJADORES DEL BOT DE TELEGRAM
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /start con un saludo cálido e interactivo."""
    nombre = update.effective_user.first_name if update.effective_user else "amigo/a"
    mensaje_bienvenida = (
        f"👋 ¡Hola, **{nombre}**! Te doy la bienvenida al asistente oficial de **GeniusBet El Salvador**.\n\n"
        "Estoy aquí para ayudarte a resolver cualquier duda sobre nuestra plataforma, siempre con información oficial y actualizada de:\n"
        f"🎁 **Promociones y Bonos:** [geniusbet.sv/promos]({URL_PROMOS})\n"
        f"📄 **Términos y Condiciones:** [geniusbet.sv/help/terms]({URL_TERMS})\n"
        f"🏠 **Página Principal y Juegos:** [geniusbet.sv/home]({URL_HOME})\n\n"
        "💬 *¿Qué te gustaría consultar hoy? Puedes preguntarme cosas como:*\n"
        "• *¿Qué promociones o bonos hay disponibles?*\n"
        "• *¿Cuál es la edad mínima para registrarme?*\n"
        "• *¿Cómo funcionan los depósitos y retiros?*\n"
        "• *¿Cómo verifico mi cuenta?*\n\n"
        "¡Escríbeme tu pregunta y con gusto te ayudo!"
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown", disable_web_page_preview=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /help con asistencia al usuario."""
    mensaje_ayuda = (
        "ℹ️ **¿Cómo puedo ayudarte?**\n\n"
        "Simplemente escribe en el chat lo que necesitas saber. Consulto en tiempo real "
        "nuestras promociones activas, reglas de apuestas y términos legales para darte respuestas exactas.\n\n"
        "Comandos disponibles:\n"
        "• /start - Iniciar o reiniciar la conversación\n"
        "• /help - Ver este menú de ayuda\n\n"
        "🔗 **Sitio web oficial:** https://www.geniusbet.sv"
    )
    await update.message.reply_text(mensaje_ayuda, parse_mode="Markdown")


async def responder_consulta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el mensaje del usuario y envía la respuesta fundamentada de Gemini."""
    if not update.message or not update.message.text:
        return

    consulta_usuario = update.message.text.strip()
    chat_id = update.effective_chat.id

    # 1. Mensaje de espera amigable
    mensaje_espera = await update.message.reply_text(
        "🔍 *Consultando la información más reciente de GeniusBet, un momento por favor...*",
        parse_mode="Markdown",
    )

    try:
        # Enviar estado de escribiendo
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        # 2. Consultar Gemini con el nuevo contexto ampliado y tono natural
        texto_respuesta = await consultar_gemini(consulta_usuario)

        # 3. Manejar límite de longitud de Telegram (máximo 4096 caracteres)
        if len(texto_respuesta) <= 4000:
            try:
                await mensaje_espera.edit_text(texto_respuesta, parse_mode="Markdown", disable_web_page_preview=True)
            except Exception:
                await mensaje_espera.edit_text(texto_respuesta)
        else:
            await mensaje_espera.edit_text(texto_respuesta[:4000])
            for i in range(4000, len(texto_respuesta), 4000):
                await update.message.reply_text(texto_respuesta[i:i+4000])

    except httpx.TimeoutException:
        logger.error("Tiempo de espera agotado al consultar Gemini")
        await mensaje_espera.edit_text(
            "⏳ Ups, el servidor tardó un poco más de lo habitual en procesar las páginas web. "
            "Por favor, intenta enviarme tu consulta nuevamente."
        )
    except Exception as e:
        logger.error(f"Error inesperado al responder consulta: {e}", exc_info=True)
        await mensaje_espera.edit_text(
            "❌ Ocurrió un error inesperado al procesar tu consulta. "
            "Por favor, intenta de nuevo en unos momentos."
        )


# ============================================================
# PUNTO DE ENTRADA PRINCIPAL
# ============================================================
def main():
    logger.info("Iniciando Asistente de GeniusBet...")
    
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), responder_consulta)
    )

    print("\n" + "=" * 55)
    print("🤖 Bot de Telegram de GeniusBet INICIADO CON ÉXITO")
    print(f"🔗 Bot: https://t.me/GeniusBetSvDemoBot (@GeniusBetSvDemoBot)")
    print(f"🧠 Modelo Gemini: {GEMINI_MODEL} (Grounding: url_context)")
    print(f"📄 Fuentes: Términos, Home y Promociones")
    print("Presiona Ctrl+C en cualquier momento para detener el bot.")
    print("=" * 55 + "\n")

    application.run_polling()


if __name__ == "__main__":
    main()
