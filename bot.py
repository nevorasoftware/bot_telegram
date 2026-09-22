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
    prompt = f"""Eres el asistente virtual oficial de atención y experiencia al cliente de GeniusBet El Salvador 🇸🇻✨.
Tu personalidad es sumamente cálida, alegre, cercana, entusiasta y muy profesional 🤝🎉. Tu misión es brindar la mejor experiencia a cada jugador con respuestas claras, motivadoras y muy visuales.

FUENTES DE INFORMACIÓN OFICIALES (Lee y fundamenta tus respuestas en estas páginas web):
1. 📄 Términos y Condiciones: {URL_TERMS}
2. 🏠 Página Principal y Juegos: {URL_HOME}
3. 🎁 Promociones y Bonos: {URL_PROMOS}

DIRECTRICES PARA UNA CONVERSACIÓN NATURAL Y RICA EN EMOTICONES:
- ¡Usa emoticones de manera expresiva y abundante en tus respuestas! 🎉⚽🎰🎁💰🔥🏆✨👏 Para cada sección, viñeta o idea clave, utiliza emojis relacionados (ejemplo: ⚽ para deportes, 🎰 para casino/slots, 🎁 para bonos, 💵 para depósitos/retiros, 📋 para reglas o requisitos, ⚠️ para advertencias importantes, 🚀 para animar al usuario).
- Saluda siempre con mucha cordialidad y energía positiva si el usuario te saluda o inicia conversación (ejemplo: "¡Hola! 👋 Qué gusto saludarte 🎉 Con mucho gusto te ayudo con eso...").
- Cuando pregunten sobre promociones, bonos, torneos o beneficios, ¡hazlo sonar emocionante y atractivo! 🎁💥 Detalla premios, vigencia, requisitos de apuesta/rollover y pasos para participar de forma muy visual y organizada con listas y emojis.
- Cuando la consulta sea sobre aspectos legales, límites de edad, verificación de cuenta, depósitos o retiros, explica las normas de forma transparente, estructurada y fácil de entender, citando la sección o regla cuando aporte valor 📌📜.
- Utiliza siempre negritas, listas con viñetas y emojis destacados para que la lectura en el móvil sea dinámica y entretenida 📱✨.
- REGLA DE VERACIDAD (GROUNDING): Basa toda tu información estrictamente en el contenido de las 3 páginas web indicadas. No inventes promociones ni datos inexistentes.
- SI LA INFORMACIÓN NO ESTÁ EN LAS PÁGINAS: No respondas de forma fría ni robótica. Di algo amable, empático y colaborativo como:
  "¡Uy! Por el momento no encuentro ese detalle específico en nuestros términos oficiales ni en el catálogo de promociones 🤔💭. ¡Pero no te preocupes! 🙌 Puedes comunicarte directamente con nuestro equipo de soporte en vivo en GeniusBet.sv para que te asistan al instante. ¡Siempre están listos para ayudarte! 💬🚀"

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
            return "No se pudo extraer una respuesta del modelo 🤔."
        
        elif response.status_code == 429:
            logger.warning("Cuota de Gemini excedida (429).")
            return (
                "⚠️ ¡Hola! En este momento estamos recibiendo un volumen alto de consultas 📈. "
                "Por favor, intenta nuevamente en un minuto para ayudarte con todo gusto. ¡Gracias por tu paciencia! 🙏✨"
            )
        else:
            logger.error(f"Error de Gemini API [{response.status_code}]: {response.text}")
            return (
                f"❌ Disculpa, ocurrió un pequeño inconveniente técnico al consultar la información ({response.status_code}) ⚙️. "
                "Por favor intenta de nuevo en unos momentos 🙏."
            )


# ============================================================
# MANEJADORES DEL BOT DE TELEGRAM
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /start con un saludo cálido, interactivo y lleno de emojis."""
    nombre = update.effective_user.first_name if update.effective_user else "amigo/a"
    mensaje_bienvenida = (
        f"👋 ¡Hola, **{nombre}**! 🎉 Te doy la más cordial bienvenida al asistente virtual oficial de **GeniusBet El Salvador** 🇸🇻✨.\n\n"
        "Estoy aquí para resolver todas tus dudas con la información más fresca y oficial directamente de nuestra plataforma 🚀:\n\n"
        f"🎁 **Promociones y Bonos Activos:** [geniusbet.sv/promos]({URL_PROMOS})\n"
        f"📄 **Términos y Condiciones Oficiales:** [geniusbet.sv/help/terms]({URL_TERMS})\n"
        f"🏠 **Página Principal y Apuestas:** [geniusbet.sv/home]({URL_HOME})\n\n"
        "💡 *¿En qué te puedo colaborar hoy? Puedes preguntarme cosas como:*\n"
        "• 🎁 *¿Cuáles son los bonos o promociones disponibles?*\n"
        "• 🔞 *¿Cuál es la edad mínima para registrarme?*\n"
        "• 💳 *¿Cómo funcionan los depósitos y retiros?*\n"
        "• 🆔 *¿Cuáles son los requisitos para verificar mi cuenta?*\n\n"
        "¡Escríbeme tu consulta abajo y con todo gusto te asisto! 👇💬✨"
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown", disable_web_page_preview=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /help con asistencia al usuario."""
    mensaje_ayuda = (
        "ℹ️ **Centro de Ayuda Rápida** 🤖✨\n\n"
        "¡Hacer consultas es súper fácil! Solo escribe tu pregunta en el chat y yo me encargaré de consultar en tiempo real nuestros términos legales, reglas de juego y las mejores promociones activas 🎁⚽🎰.\n\n"
        "📌 **Comandos útiles:**\n"
        "• /start - 🚀 Iniciar o reiniciar la conversación\n"
        "• /help - 📖 Ver este menú de ayuda e instrucciones\n\n"
        "🌐 **Sitio Web Oficial:** https://www.geniusbet.sv 🇸🇻"
    )
    await update.message.reply_text(mensaje_ayuda, parse_mode="Markdown")


async def responder_consulta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el mensaje del usuario y envía la respuesta fundamentada de Gemini."""
    if not update.message or not update.message.text:
        return

    consulta_usuario = update.message.text.strip()
    chat_id = update.effective_chat.id

    # 1. Mensaje de espera amigable con emojis
    mensaje_espera = await update.message.reply_text(
        "🔍 *Consultando la información en vivo de GeniusBet... ¡Dame un segundito!* ⏳✨",
        parse_mode="Markdown",
    )

    try:
        # Enviar estado de escribiendo
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        # 2. Consultar Gemini con el nuevo contexto ampliado, tono natural y emojis
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
            "⏳ Ups, el servidor tardó un poco más de lo habitual en procesar las páginas web 🌐. "
            "Por favor, intenta enviarme tu consulta nuevamente 🙏."
        )
    except Exception as e:
        logger.error(f"Error inesperado al responder consulta: {e}", exc_info=True)
        await mensaje_espera.edit_text(
            "❌ Ocurrió un error inesperado al procesar tu consulta ⚙️. "
            "Por favor, intenta de nuevo en unos momentos 🙏."
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
