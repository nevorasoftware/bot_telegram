# 🤖 GeniusBet Telegram Bot (Gemini AI & Live URL Grounding)

Bot de atención y experiencia al cliente para Telegram que responde consultas de usuarios basándose exclusivamente en el contenido en tiempo real de la plataforma oficial de GeniusBet El Salvador:
- 🎁 **Promociones y Bonos:** `https://www.geniusbet.sv/promos`
- 📄 **Términos y Condiciones:** `https://www.geniusbet.sv/help/terms-of-conditions`
- 🏠 **Página Principal:** `https://www.geniusbet.sv/home`

---

## 🌟 Características
- **Grounding en Vivo:** Usa la herramienta `url_context` de Google Gemini para leer las páginas web oficiales en cada consulta.
- **Tono Natural y Amigable:** Respuestas cálidas, empáticas y dinámicas que facilitan la interacción y fidelización.
- **Cero Alucinaciones:** Reglas estrictas de veracidad; si un dato no está en las páginas oficiales, guía proactivamente al usuario hacia el soporte en vivo.
- **Preparado para Railway:** Incluye `Procfile` y manejo de variables de entorno para despliegue instantáneo en la nube 24/7.

---

## 📁 Estructura del Repositorio
```
├── bot.py              # Código principal del bot de Telegram
├── requirements.txt    # Dependencias de Python
├── Procfile            # Definición del proceso worker para Railway / PaaS
├── .gitignore          # Exclusión de archivos sensibles (.env, cachés)
└── README.md           # Documentación del proyecto
```

---

## 🛠️ Variables de Entorno Requeridas
Crea un archivo `.env` localmente o agrégalas en el panel de variables de Railway:

```env
TELEGRAM_TOKEN=tu_token_de_telegram_aqui
GEMINI_API_KEY=tu_api_key_de_gemini_aqui
GEMINI_MODEL=gemini-3-flash-preview
```

---

## 🚀 Despliegue en Railway (Paso a Paso)

1. **Crear una cuenta o iniciar sesión** en [Railway](https://railway.app/).
2. Haz clic en **"New Project"** y selecciona **"Deploy from GitHub repo"**.
3. Elige el repositorio `nevorasoftware/bot_telegram`.
4. Ve a la pestaña **Variables** en Railway y agrega las siguientes:
   - `TELEGRAM_TOKEN`: Tu token de Telegram
   - `GEMINI_API_KEY`: Tu clave de API de Gemini
   - `GEMINI_MODEL`: `gemini-3-flash-preview`
   - `PYTHONUNBUFFERED`: `1`
5. Railway detectará automáticamente el archivo `Procfile` e iniciará el proceso `worker` sin necesidad de exponer puertos HTTP.
6. ¡Listo! Tu bot estará en línea las 24 horas del día.

---

## 💻 Ejecución Local

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Ejecutar el bot:
   ```bash
   python -u bot.py
   ```

---

## 🤖 Enlace del Bot en Telegram
- Nombre: **GeniusBetSV-Demo**
- Usuario: [@GeniusBetSvDemoBot](https://t.me/GeniusBetSvDemoBot)
