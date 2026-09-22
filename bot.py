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
    prompt = f"""Eres un asesor oficial del equipo de atención y experiencia al cliente de GeniusBet El Salvador 🇸🇻✨.
Tu trato es sumamente cálido, alegre, cercano, entusiasta y muy profesional 🤝🎉. Hablas como una persona real, atenta y servicial que forma parte del equipo de GeniusBet.

REGLAS DE IDENTIDAD Y ESTILO:
- NUNCA menciones que eres un bot, robot, inteligencia artificial, modelo de lenguaje o programa de computadora. Jamás menciones modelos técnicos ni nombres como Gemini, Google, OpenAI, etc.
- Habla siempre en primera persona como miembro del equipo humano de GeniusBet ("Con gusto te ayudo", "En nuestro equipo te apoyamos", "Te comparto los detalles...", etc.).
- Si el usuario te pregunta directamente "¿eres un bot?" o similar, responde con simpatía y naturalidad:
  "¡Hola! 👋 Soy parte del equipo de atención de GeniusBet El Salvador 🇸🇻🤝. Estoy aquí para atenderte con total gusto y resolver cualquier duda sobre tus apuestas, cuenta o promociones. ¿En qué te puedo colaborar hoy? 😊✨"

FUENTES DE INFORMACIÓN OFICIALES (Lee y fundamenta tus respuestas en estas páginas web):
1. 📄 Términos y Condiciones: {URL_TERMS}
2. 🏠 Página Principal y Juegos: {URL_HOME}
3. 🎁 Promociones y Bonos: {URL_PROMOS}

DIRECTRICES PARA UNA CONVERSACIÓN NATURAL Y RICA EN EMOTICONES:
- ¡Usa emoticones de manera expresiva y agradable en tus respuestas! 🎉⚽🎰🎁💰🔥🏆✨👏 Úsalos de acuerdo al tema (⚽ para deportes, 🎰 para casino/slots, 🎁 para bonos, 💵 para depósitos/retiros, 📋 para reglas, ⚠️ para advertencias importantes, 🚀 para animar al cliente).
- Saluda siempre con mucha cordialidad y energía si el usuario te saluda o inicia conversación (ejemplo: "¡Hola! 👋 Qué gusto saludarte 🎉 Con mucho gusto te ayudo con eso...").
- Cuando pregunten sobre promociones, bonos, torneos o beneficios, ¡explícalo de forma atractiva y clara! 🎁💥 Detalla premios, vigencia, requisitos de apuesta/rollover y pasos para participar de forma visual y organizada con viñetas.
- Cuando la consulta sea sobre aspectos legales, límites de edad, verificación de cuenta, depósitos o retiros, explica las normas con sencillez y claridad, citando la sección o regla cuando aporte valor 📌📜.
- Utiliza siempre negritas, listas con viñetas y emojis destacados para que la lectura en el móvil sea fluida y entretenida 📱✨.
- REGLA DE VERACIDAD (GROUNDING): Basa toda tu información estrictamente en el contenido de las 3 páginas web indicadas. No inventes promociones ni datos que no existan.
- SI LA INFORMACIÓN NO ESTÁ EN LAS PÁGINAS: No respondas de forma fría ni robótica. Di algo amable y colaborativo como:
  "¡Uy! Por el momento no tengo ese dato específico a la mano en nuestros términos ni en las promociones publicadas 🤔💭. ¡Pero no te preocupes! 🙌 Puedes comunicarte directamente con nuestro equipo de soporte en vivo en GeniusBet.sv para que te den una respuesta exacta de inmediato. ¡Con gusto te atenderán! 💬🚀"

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
            return "No se pudo obtener la información en este momento 🤔."
        
        elif response.status_code == 429:
            logger.warning("Cuota de API excedida (429).")
            return (
                "⚠️ ¡Hola! En este momento estamos atendiendo muchas consultas a la vez 📈. "
                "Por favor, dame un minutito y vuelve a preguntarme para atenderte como te mereces. ¡Muchas gracias por tu paciencia! 🙏✨"
            )
        else:
            logger.error(f"Error de API [{response.status_code}]: {response.text}")
            return (
                f"❌ Disculpa, ocurrió un pequeño inconveniente técnico al consultar la información ({response.status_code}) ⚙️. "
                "Por favor intenta de nuevo en unos momentos 🙏."
            )


# ============================================================
# MANEJADORES DEL BOT DE TELEGRAM
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /start con un saludo cálido, interactivo y humano."""
    nombre = update.effective_user.first_name if update.effective_user else "amigo/a"
    mensaje_bienvenida = (
        f"👋 ¡Hola, **{nombre}**! 🎉 Te doy la bienvenida al canal oficial de atención de **GeniusBet El Salvador** 🇸🇻✨.\n\n"
        "Estoy aquí para ayudarte en lo que necesites sobre nuestra plataforma: resolver tus dudas, contarte sobre nuestras promociones activas o explicarte cualquier detalle de tus apuestas y cuenta 🚀:\n\n"
        f"🎁 **Promociones y Bonos Activos:** [geniusbet.sv/promos]({URL_PROMOS})\n"
        f"📄 **Términos y Condiciones Oficiales:** [geniusbet.sv/help/terms]({URL_TERMS})\n"
        f"🏠 **Página Principal y Apuestas:** [geniusbet.sv/home]({URL_HOME})\n\n"
        "💡 *¿En qué te puedo colaborar hoy? Puedes preguntarme cosas como:*\n"
        "• 🎁 *¿Cuáles son los bonos o promociones disponibles?*\n"
        "• 🔞 *¿Cuál es la edad mínima para abrir cuenta?*\n"
        "• 💳 *¿Cómo funcionan los depósitos y retiros?*\n"
        "• 🆔 *¿Cuáles son los requisitos para verificar mi cuenta?*\n\n"
        "¡Escríbeme tu consulta abajo y con todo gusto te asisto! 👇💬✨"
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown", disable_web_page_preview=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /help con asistencia al usuario."""
    mensaje_ayuda = (
        "ℹ️ **Centro de Ayuda GeniusBet** 💬✨\n\n"
        "¡Resolver tus dudas es súper fácil! Solo escribe tu consulta aquí en el chat y con gusto te explicaré nuestras promociones vigentes, reglas de deportes, casino y métodos de pago 🎁⚽🎰.\n\n"
        "📌 **Comandos útiles:**\n"
        "• /start - 🚀 Iniciar o reiniciar la conversación\n"
        "• /help - 📖 Ver este menú de ayuda\n\n"
        "🌐 **Sitio Web Oficial:** https://www.geniusbet.sv 🇸🇻"
    )
    await update.message.reply_text(mensaje_ayuda, parse_mode="Markdown")


async def responder_consulta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el mensaje del usuario y envía la respuesta con tono natural y humano."""
    if not update.message or not update.message.text:
        return

    consulta_usuario = update.message.text.strip()
    chat_id = update.effective_chat.id

    # 1. Mensaje de espera amigable y humano
    mensaje_espera = await update.message.reply_text(
        "✍️ *Revisando la información, dame un segundito...* ⏳✨",
        parse_mode="Markdown",
    )

    try:
        # Enviar estado de escribiendo
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        # 2. Consultar Gemini con el nuevo tono humano y empático
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
            "⏳ Disculpa la demora, el sistema tardó un poco más de lo habitual en cargar los datos 🌐. "
            "¿Podrías enviarme tu consulta nuevamente por favor? 🙏"
        )
    except Exception as e:
        logger.error(f"Error inesperado al responder consulta: {e}", exc_info=True)
        await mensaje_espera.edit_text(
            "❌ Disculpa, ocurrió un inconveniente al cargar la información ⚙️. "
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
