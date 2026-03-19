# GM Comentarista — Versión Móvil (PWA)

App de análisis de ajedrez con IA, optimizada para móviles y desplegable en Streamlit Cloud.

## 🚀 Despliegue en Streamlit Cloud (Gratuito)

### Paso 1: Crear el repositorio en GitHub

1. Ve a [github.com](https://github.com) → **New Repository**
2. Nombre sugerido: `gm-comentarista-mobile`
3. **Público** (necesario para el plan gratuito de Streamlit Cloud)
4. Sube esta carpeta completa al repositorio:
   ```
   git init
   git add .
   git commit -m "Initial mobile PWA version"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/gm-comentarista-mobile.git
   git push -u origin main
   ```

### Paso 2: Desplegar en Streamlit Cloud

1. Ve a [share.streamlit.io](https://share.streamlit.io) e inicia sesión con tu cuenta de GitHub
2. Clic en **"New app"**
3. Selecciona tu repositorio `gm-comentarista-mobile`
4. Branch: `main`, File path: `app.py`
5. Clic en **"Deploy!"** — en ~2 minutos tendrás la URL

### Paso 3: Configurar la API Key de Gemini

En Streamlit Cloud no debes poner la API Key en el código. Usa **Secrets**:

1. En tu app desplegada → **⋮ Settings → Secrets**
2. Añade:
   ```toml
   GEMINI_API_KEY = "tu-clave-aqui"
   ```
3. La app la leerá automáticamente como variable de entorno

> **Alternativa**: Introduce la clave manualmente en la sidebar cada vez que uses la app.

### Paso 4: Instalarla como app en el móvil

**Android (Chrome):**
1. Abre la URL de tu app en Chrome
2. Menú (⋮) → **"Añadir a pantalla de inicio"**
3. ¡Ya aparece como app con icono!

**iPhone (Safari):**
1. Abre la URL en Safari
2. Botón compartir (□↑) → **"Añadir a inicio"**

---

## 📁 Estructura del proyecto

```
GM_comentarista_mobile/
├── app.py                  ← App principal (mobile-first)
├── requirements.txt        ← Dependencias Python
├── packages.txt            ← Paquetes del sistema (Stockfish)
├── AI_PROMPT.txt           ← Prompt del Gran Maestro IA
├── .streamlit/
│   └── config.toml         ← Tema oscuro + configuración servidor
├── chess_component/
│   ├── __init__.py         ← Componente Streamlit del tablero
│   └── index.html          ← Tablero interactivo (chessboard.js)
├── commentary_engine.py    ← Motor de análisis Stockfish + orquestación IA
├── ai_client.py            ← Cliente centralizado de Google Gemini
├── cache_manager.py        ← Caché SQLite de comentarios
├── lichess_api.py          ← API de Lichess
└── meta_analysis.py        ← Meta-análisis de partidas
```

---

## ⚠️ Limitaciones vs versión de escritorio

| Función | Escritorio | Móvil (PWA) |
|---|:---:|:---:|
| Análisis Stockfish | ✅ Local | ✅ En el servidor cloud |
| Comentarios Gemini | ✅ | ✅ |
| Historial PGN | ✅ Carpetas locales | ✅ En el servidor (temporal) |
| NotebookLM auto | ✅ | ❌ No soportado |
| Modo offline | ✅ | ❌ Requiere internet |
| Syzygy Tablebases | ✅ Local | ❌ Solo online |

---

## 🔧 Desarrollo local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para usar Stockfish local, añade a `.streamlit/secrets.toml`:
```toml
STOCKFISH_PATH = "C:/ruta/a/stockfish.exe"
```
