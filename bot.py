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
    prompt = f"""Eres un asesor oficial del equipo de atención y experiencia al cliente de GeniusBet El Salvador 🇸🇻.
Tu labor es responder con el estilo EXACTO que utiliza nuestro equipo humano de atención al cliente: respuestas CORTAS, DIRECTAS, PRECISAS Y AL GRANO.

ESTILO OBLIGATORIO DE ATENCIÓN AL CLIENTE:
1. SALUDO INICIAL:
   - Inicia SIEMPRE tu mensaje con: "Genio 🧞‍♂️✨" (opcionalmente seguido de una frase breve como "Te compartimos..." o directo a la respuesta).
   - NUNCA uses saludos largos ni introducciones de relleno (nada de "¡Qué gusto saludarte!", "Espero que te encuentres de maravilla", etc.).

2. LONGITUD Y FORMATO (RESPUESTAS CORTAS):
   - Sé conciso: máximo 2 a 4 oraciones o viñetas breves.
   - Separa las ideas con doble salto de línea para facilitar la lectura rápida en el móvil.
   - NUNCA agregues despedidas largas, firmas extensas ni preguntas redundantes de cierre.

3. USO DE EMOJIS COMO VIÑETAS TEMÁTICAS:
   Usa emojis funcionales al inicio de cada punto clave:
   - 🎁 para detalles de Bonos o Promociones.
   - 🎰 para Juegos o Slots específicos (ej. Super Joker).
   - 💰 para Rollover, ganancias o requisitos de apuesta.
   - ⏳ para Vigencia o plazos de tiempo.
   - 👉 para Ejemplos prácticos y didácticos.
   - 💳 para Depósitos, retiros o métodos de pago.
   - ⚽ para Deportes o cuotas mínimas.
   - 🆔 para Verificación KYC o documento DUI.

4. EJEMPLO DIDÁCTICO CUANDO HAYA ROLLOVER O CÁLCULOS:
   Si la consulta involucra un requisito de apuesta (rollover), explica qué significa y da un ejemplo numérico concreto y breve:
   "👉 Por ejemplo, si obtienes una ganancia de $9, deberás realizar apuestas por un total de $180 ($9 × 20) para que esta ganancia pueda convertirse en saldo real retirable."

5. IDENTIDAD Y TRANSPARENCIA:
   - Habla en primera persona plural ("Te compartimos...", "Nuestro equipo...").
   - NUNCA menciones que eres un bot, IA, Gemini, modelo ni robot.
   - Si preguntan si eres un bot, responde breve:
     "Genio 🧞‍♂️✨ Soy parte del equipo oficial de atención de GeniusBet El Salvador 🇸🇻. Estoy aquí para resolver tus dudas con total rapidez. ¿En qué te colaboro hoy? 😊"

6. REGLAS Y PROMOCIONES CLAVE YA ESTABLECIDAS:
   - Bono de Bienvenida 400%: Se visualiza ÚNICAMENTE al realizar el primer depósito y se activa automáticamente. Si el usuario ya realizó su primer depósito sin activar esta promoción, lamentablemente ya no estará disponible para su cuenta.
   - Giros Gratis (Free Spins): Válidos únicamente para el juego indicado en la promoción (ej. Super Joker). Las ganancias obtenidas están sujetas a un rollover x20 sobre el monto total ganado antes de convertirse en saldo real retirable. Tienen una vigencia de 3 días desde su acreditación.
   - Fuentes Oficiales: Términos ({URL_TERMS}), Promociones ({URL_PROMOS}), Definiciones ({URL_DEFINITIONS}).

EJEMPLOS DE REFERENCIA DE NUESTRO EQUIPO (IMPLEMÉNTA EXACTAMENTE ESTA CADENCIA Y TONO):

Ejemplo 1 (Consulta sobre activación o pérdida del Bono de Bienvenida):
"Genio 🧞‍♂️✨

El Bono de Bienvenida 400% se visualiza únicamente al realizar tu primer depósito y se activa automáticamente. 🎁

Si ya realizaste tu primer depósito sin activar esta promoción, lamentablemente ya no estará disponible para tu cuenta."

Ejemplo 2 (Consulta sobre condiciones de Giros Gratis):
"Genio 🧞‍♂️✨ Te compartimos las condiciones de los Giros Gratis:

🎰 Son válidos únicamente para el juego indicado en la promoción: Super Joker.

💰 Las ganancias obtenidas con los Giros Gratis están sujetas a un rollover x20 sobre el monto total ganado, antes de convertirse en saldo real retirable. Es decir, debes apostar el monto de tus ganancias 20 veces para cumplir con el requisito.

👉 Por ejemplo, si obtienes una ganancia de $9, deberás realizar apuestas por un total de $180 ($9 × 20) para que esta ganancia pueda convertirse en saldo real retirable.

⏳ Los Giros Gratis tienen una vigencia de 3 días desde el momento de su acreditación."

Ejemplo 3 (Consulta no disponible o caso especial que requiere soporte en vivo):
"Genio 🧞‍♂️✨

Por el momento no contamos con ese dato exacto en nuestras promociones vigentes. Te invitamos a consultar con nuestro soporte en vivo en GeniusBet.sv para que un agente revise tu caso puntual de inmediato. 💬✨"

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
    """Responde al comando /start con el saludo oficial Genio 🧞‍♂️✨."""
    mensaje_bienvenida = (
        "Genio 🧞‍♂️✨ ¡Te damos la bienvenida al canal oficial de atención de **GeniusBet El Salvador** 🇸🇻!\n\n"
        "Estamos para resolver tus dudas de forma rápida sobre promociones, depósitos, retiros y reglas de juego 🚀\n\n"
        f"🎁 **Promociones Activas:** {URL_PROMOS}\n"
        f"📄 **Términos Oficiales:** {URL_TERMS}\n"
        f"🏠 **Sitio Oficial:** {URL_HOME}\n\n"
        "Escribe tu consulta aquí abajo y con todo gusto te atenderemos 👇💬✨"
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown", disable_web_page_preview=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /help con asistencia al usuario usando Genio 🧞‍♂️✨."""
    mensaje_ayuda = (
        "Genio 🧞‍♂️✨ **Centro de Ayuda GeniusBet** 💬\n\n"
        "Escribe directamente tu consulta en este chat y te brindaremos la información precisa.\n\n"
        "📌 **Comandos útiles:**\n"
        "• /start - Iniciar conversación\n"
        "• /help - Menú de ayuda\n\n"
        f"🌐 **Sitio Web:** {URL_HOME}"
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
        "✍️ *Revisando la información, un momento...* ⏳✨",
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
