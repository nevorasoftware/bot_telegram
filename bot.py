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

# Modelos de Gemini a utilizar con fallback automático si uno agota cuota
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
CANDIDATE_MODELS = [
    PRIMARY_MODEL,
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
]
# Eliminar duplicados manteniendo orden de prioridad
MODELS_TO_TRY = list(dict.fromkeys(CANDIDATE_MODELS))

# URLs oficiales de GeniusBet como fuente de verdad
URL_TERMS = "https://www.geniusbet.sv/help/terms-of-conditions"
URL_PROMOS = "https://www.geniusbet.sv/promos"
URL_DEFINITIONS = "https://www.geniusbet.sv/help/betting-definitions"
URL_HOME = "https://www.geniusbet.sv/home"

# Validar credenciales al inicio
if not TELEGRAM_TOKEN:
    raise ValueError("Error: TELEGRAM_TOKEN no encontrado en las variables de entorno.")
if not GEMINI_API_KEY:
    raise ValueError("Error: GEMINI_API_KEY no encontrado en las variables de entorno.")


# ============================================================
# CONSULTA A GEMINI CON GROUNDING Y TONO NATURAL GENIO 🧞‍♂️
# ============================================================
async def consultar_gemini(consulta_usuario: str) -> str:
    """
    Envía la consulta del usuario a Gemini con contexto fundamentado en la web de GeniusBet,
    máxima precisión en los términos y condiciones de cada promoción y trato oficial como 'Genio 🧞‍♂️'.
    Incluye fallback inteligente entre modelos para garantizar disponibilidad continua.
    """
    prompt = f"""Eres un asesor oficial del equipo de atención y experiencia al cliente de GeniusBet El Salvador 🇸🇻✨.
Tu trato es sumamente cálido, alegre, cercano, entusiasta y muy profesional 🤝🎉. Hablas como una persona real, atenta y servicial que forma parte del equipo de GeniusBet.

REGLAS DE IDENTIDAD Y ESTILO:
- TRATO AL USUARIO OBLIGATORIO: Dirígete SIEMPRE al usuario como "Genio 🧞‍♂️" (ejemplos: "¡Hola, Genio 🧞‍♂️!", "Genio 🧞‍♂️, con gusto te explico...", etc.).
- NUNCA menciones que eres un bot, robot, inteligencia artificial, modelo de lenguaje o programa de computadora. Jamás menciones modelos técnicos ni nombres como Gemini, Google, OpenAI, etc.
- Habla siempre en primera persona como miembro del equipo humano de GeniusBet ("Con gusto te ayudo", "En nuestro equipo te apoyamos", "Te comparto los detalles...", etc.).
- Si el usuario te pregunta directamente "¿eres un bot?" o similar, responde con simpatía y naturalidad:
  "¡Hola, Genio 🧞‍♂️! 👋 Soy parte del equipo de atención de GeniusBet El Salvador 🇸🇻🤝. Estoy aquí para atenderte con total gusto y resolver cualquier duda sobre tus apuestas, cuenta o promociones. ¿En qué te puedo colaborar hoy? 😊✨"

FUENTES OFICIALES DE INFORMACIÓN (Fundamenta tus respuestas en estas páginas web de GeniusBet):
1. 📄 Términos y Condiciones Oficiales: {URL_TERMS}
2. 🎁 Promociones y Bonos Activos: {URL_PROMOS}
3. 📖 Reglas y Definiciones de Apuestas: {URL_DEFINITIONS}
4. 🏠 Página Principal y Juegos: {URL_HOME}

PRECISIÓN ESTRICTA Y ENFOQUE EN TÉRMINOS Y CONDICIONES DE CADA PROMOCIÓN:
- Sé sumamente EXACTO y PRECISO con la información. No des datos ambiguos ni generalidades.
- Cuando pregunten sobre promociones, bonos, torneos o beneficios, detalla con total exactitud los TÉRMINOS Y CONDICIONES específicos de cada promoción:
  * Requisito de apuesta o rollover exacto (cuántas veces debe apostarse el bono para liberarlo a saldo real).
  * Cuotas mínimas requeridas para que las apuestas califiquen para el bono o freebet.
  * Vigencia y plazo límite para cumplir los requisitos.
  * Depósito mínimo o condiciones de activación necesarias.
  * Deportes, juegos o mercados válidos y posibles restricciones.
  * Cómo se acreditan las ganancias (saldo de bono vs saldo real retirable).
  * Comparte siempre el enlace directo a nuestras promociones: {URL_PROMOS}.
- Cuando la consulta sea sobre aspectos legales, límites de edad (18+), verificación de cuenta (documento oficial / DUI bajo política KYC), depósitos o retiros, explica las normas con exactitud citando lo establecido en los Términos y Condiciones oficiales 📌📜 ({URL_TERMS}).
- FORMATO ATRACTIVO Y ORDENADO: Utiliza siempre negritas, listas con viñetas y emojis pertinentes (⚽, 🎰, 🎁, 💵, 📋, ⚠️, 🚀, ✅) para que la lectura sea fluida y muy clara 📱✨.
- REGLA DE VERACIDAD (GROUNDING ESTRICTO): Basa toda tu información estrictamente en el contenido de las fuentes de GeniusBet. Queda prohibido inventar promociones, reglas o datos que no existan en el sitio oficial de GeniusBet.
- SI LA INFORMACIÓN ES MUY ESPECÍFICA O CAMBIANTE: Invita amablemente al usuario con simpatía y calidez:
  "¡Hola, Genio 🧞‍♂️! Por el momento no tengo ese dato específico a la mano en nuestros términos ni en las promociones publicadas 🤔💭. ¡Pero no te preocupes! 🙌 Puedes comunicarte directamente con nuestro equipo de soporte en vivo en GeniusBet.sv para que te den una respuesta exacta de inmediato. ¡Con gusto te atenderemos! 💬🚀"

Consulta del usuario:
{consulta_usuario}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for model in MODELS_TO_TRY:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_parts = [p.get("text", "") for p in parts if "text" in p]
                        return "".join(text_parts).strip()
                    continue
                elif response.status_code == 429:
                    logger.warning(f"Cuota excedida en modelo {model} (429). Probando modelo de respaldo...")
                    continue
                else:
                    logger.warning(f"Respuesta {response.status_code} en modelo {model}: {response.text[:200]}")
                    continue
            except Exception as e:
                logger.warning(f"Error consultando modelo {model}: {e}")
                continue

    return (
        "⚠️ ¡Hola, Genio 🧞‍♂️! En este momento estamos atendiendo muchas consultas a la vez 📈. "
        "Por favor, dame un minutito y vuelve a preguntarme para atenderte como te mereces. ¡Muchas gracias por tu paciencia! 🙏✨"
    )


# ============================================================
# MANEJADORES DEL BOT DE TELEGRAM
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /start con un saludo cálido, interactivo y humano usando Genio 🧞‍♂️."""
    mensaje_bienvenida = (
        "👋 ¡Hola, **Genio 🧞‍♂️**! 🎉 Te doy la bienvenida al canal oficial de atención de **GeniusBet El Salvador** 🇸🇻✨.\n\n"
        "Estoy aquí para ayudarte en lo que necesites sobre nuestra plataforma: resolver tus dudas con total precisión sobre promociones, términos y condiciones o cualquier detalle de tus apuestas y cuenta 🚀:\n\n"
        f"🎁 **Promociones y Bonos Activos:** [geniusbet.sv/promos]({URL_PROMOS})\n"
        f"📄 **Términos y Condiciones Oficiales:** [geniusbet.sv/help/terms]({URL_TERMS})\n"
        f"📖 **Definiciones y Reglas de Apuestas:** [geniusbet.sv/help/definitions]({URL_DEFINITIONS})\n"
        f"🏠 **Página Principal y Apuestas:** [geniusbet.sv/home]({URL_HOME})\n\n"
        "💡 *¿En qué te puedo colaborar hoy? Puedes preguntarme sobre:*\n"
        "• 🎁 *Términos, condiciones y rollover de cualquier bono o promoción*\n"
        "• 🔞 *Edad mínima, verificación con DUI y retiros*\n"
        "• 💳 *Métodos de depósito y tiempos de pago*\n"
        "• ⚽ *Reglas específicas de apuestas deportivas y casino*\n\n"
        "¡Escríbeme tu consulta abajo y con todo gusto te asisto! 👇💬✨"
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown", disable_web_page_preview=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /help con asistencia al usuario usando Genio 🧞‍♂️."""
    mensaje_ayuda = (
        "ℹ️ **Centro de Ayuda GeniusBet** 💬✨\n\n"
        "¡Hola, **Genio 🧞‍♂️**! Resolver tus dudas es súper fácil. Escribe tu consulta aquí en el chat y con gusto te daré la información precisa sobre nuestras promociones vigentes, términos y condiciones, reglas de deportes, casino y métodos de pago 🎁⚽🎰.\n\n"
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
# MANEJADOR DE ERRORES DE TELEGRAM
# ============================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja excepciones de red o polling de Telegram evitando trazas ruidosas."""
    error = context.error
    if error and "Conflict: terminated by other getUpdates request" in str(error):
        logger.warning(
            "Conflicto temporal de getUpdates (ocurre normalmente durante despliegues en Railway mientras la instancia previa se detiene). La conexión se estabilizará automáticamente."
        )
    else:
        logger.error(f"Excepción capturada en Telegram: {error}", exc_info=error)


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
    application.add_error_handler(error_handler)

    print("\n" + "=" * 55)
    print("🤖 Bot de Telegram de GeniusBet INICIADO CON ÉXITO")
    print(f"🔗 Bot: https://t.me/GeniusBetSvDemoBot (@GeniusBetSvDemoBot)")
    print(f"🧠 Modelo Gemini: {PRIMARY_MODEL} (Respaldo: {', '.join(MODELS_TO_TRY[1:])})")
    print(f"📄 Fuentes Oficiales: Términos, Promociones, Definiciones y Home")
    print("Presiona Ctrl+C en cualquier momento para detener el bot.")
    print("=" * 55 + "\n")

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
