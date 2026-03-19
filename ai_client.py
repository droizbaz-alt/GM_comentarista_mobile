"""
ai_client.py — Módulo centralizado para la comunicación con la API de Google Gemini.

Responsabilidades:
  - Inicializar y gestionar la conexión con genai.Client.
  - Gestionar el sistema de fallback entre modelos cuando hay errores de cuota (429).
  - Leer el prompt base desde AI_PROMPT.txt y aplicar sustituciones dinámicas.
  - Guardar/recuperar comentarios desde el caché (CacheManager).
  - Registrar errores de API en pgn_errors.log.
"""
import os
import re
import time

try:
    from google import genai
except ImportError:
    genai = None

from cache_manager import CacheManager


# ---------------------------------------------------------------------------
# Mapa de modelos por nivel de calidad (para la UI simplificada)
# ---------------------------------------------------------------------------
QUALITY_PROFILES = {
    "Básica": {
        "lite":  "gemini-2.5-flash-lite",
        "pro":   "gemini-2.5-flash",
    },
    "Media": {
        "lite":  "gemini-3.1-flash-lite-preview",
        "pro":   "gemini-2.5-flash",
    },
    "Alta": {
        "lite":  "gemini-3.1-flash-lite-preview",
        "pro":   "gemini-2.5-pro",
    },
}

# Modelos de rescate con altas cuotas gratuitas (intentados si los primarios fallan)
RESCUE_MODELS = ["gemini-3.1-flash-lite-preview", "gemma-3-27b-it"]


class AIClient:
    """Cliente unificado de Gemini con fallback automático entre modelos."""

    def __init__(self, api_key: str, use_cache: bool = True, use_search: bool = False, use_thinking: bool = False):
        self.api_key = api_key
        self.use_search = use_search
        self.use_thinking = use_thinking
        self.client = None
        self.last_error: str | None = None
        self.rate_limit_cooldown_until: float | None = None
        self.cache = CacheManager() if use_cache else None

        self._prompt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AI_PROMPT.txt")
        self._log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pgn_errors.log")
        self._last_response_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_ai_response.txt")

        if genai is None:
            self.last_error = "Librería 'google-genai' no instalada."
            return

        if not api_key:
            return  # Sin clave, la IA queda desactivada silenciosamente

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            self.last_error = f"Error al inicializar Gemini: {e}"

    # ------------------------------------------------------------------
    # Propiedad pública
    # ------------------------------------------------------------------
    @property
    def is_ready(self) -> bool:
        return self.client is not None

    # ------------------------------------------------------------------
    # Método principal
    # ------------------------------------------------------------------
    def generate_commentary(
        self,
        pgn_text: str,
        summary: str,
        knowledge_context: str = "",
        is_enhancement: bool = False,
        model_name: str | None = None,
    ) -> str | None:
        """
        Genera el PGN comentado a través de Gemini.

        Parámetros
        ----------
        pgn_text        : PGN de la partida o ventana crítica.
        summary         : Bloque de datos técnicos de Stockfish.
        knowledge_context: Contenido de NotebookLM, si está disponible.
        is_enhancement  : True si estamos analizando un segmento crítico con el modelo Pro.
        model_name      : Modelo primario a intentar. Si es None se usa gemini-2.5-flash.

        Retorna el PGN comentado como string, o None si todos los modelos fallan.
        """
        if not self.is_ready:
            return None

        prompt = self._build_prompt(pgn_text, summary, knowledge_context, is_enhancement)

        # Cache lookup
        if self.cache:
            cached = self.cache.get_commentary(prompt)
            if cached:
                return cached

        models_to_try = self._build_fallback_list(model_name or "gemini-2.5-flash")

        for current_model in models_to_try:
            for attempt in range(2):
                # Esperar si estamos en cool-down por rate limit
                if self.rate_limit_cooldown_until and time.time() < self.rate_limit_cooldown_until:
                    time.sleep(max(0, self.rate_limit_cooldown_until - time.time()))

                try:
                    response = self.client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config={},
                    )
                    res_text = response.text.strip()

                    # Debug: guardar última respuesta
                    try:
                        with open(self._last_response_file, "w", encoding="utf-8") as f:
                            f.write(res_text)
                    except Exception:
                        pass

                    # Eliminar bloques <thought> de modelos de razonamiento
                    res_text = re.sub(r"<thought>.*?</thought>", "", res_text, flags=re.DOTALL | re.IGNORECASE)
                    res_text = re.sub(r"thinking\n+.*?\n+", "", res_text, flags=re.IGNORECASE)

                    # Extraer bloque PGN
                    pgn_match = re.search(r"```(?:pgn|chess|)?\s*(.*?)\s*```", res_text, re.DOTALL | re.IGNORECASE)
                    if pgn_match:
                        final_pgn = pgn_match.group(1).strip()
                        if self.cache:
                            self.cache.save_commentary(prompt, current_model, final_pgn)
                        return final_pgn

                    # Fallback: buscar primera cabecera PGN o primer movimiento
                    m = re.search(r'(\[[A-Za-z]+\s+".*?"\]|\b1\.\s+)', res_text)
                    if m:
                        final_pgn = res_text[m.start():].strip()
                        if self.cache:
                            self.cache.save_commentary(prompt, current_model, final_pgn)
                        return final_pgn

                    # Sin PGN en la respuesta
                    self._log(f"NO PGN FOUND IN RESPONSE FROM {current_model}")
                    self.last_error = f"Sin PGN en respuesta de {current_model}"

                except Exception as e:
                    error_msg = str(e)
                    self.last_error = error_msg
                    self._log(f"API ERROR (Model: {current_model}, Attempt {attempt + 1})\n{error_msg}")

                    if "429" in error_msg:
                        wait = 5 * (attempt + 1)
                        self.rate_limit_cooldown_until = time.time() + wait
                        if attempt == 1:
                            break  # Pasar al siguiente modelo
                        time.sleep(wait)
                    else:
                        break  # Error no recuperable: siguiente modelo

        return None

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------
    def _build_prompt(
        self,
        pgn_text: str,
        summary: str,
        knowledge_context: str,
        is_enhancement: bool,
    ) -> str:
        """Construye el prompt final leyendo la plantilla de AI_PROMPT.txt."""
        knowledge_section = f"\n[BASE DE CONOCIMIENTO]:\n{knowledge_context}\n" if knowledge_context else ""
        game_id_ctx = f"PARTIDA ACTUAL: {pgn_text[:200]}..."
        time_id = str(time.time())

        template = "{pgn_text}\n{summary}"
        if os.path.exists(self._prompt_file):
            try:
                with open(self._prompt_file, "r", encoding="utf-8") as f:
                    template = f.read()
            except Exception:
                pass

        prompt = (
            template
            .replace("{time_id}", time_id)
            .replace("{game_id_ctx}", game_id_ctx)
            .replace("{knowledge_section}", knowledge_section)
            .replace("{pgn_text}", pgn_text)
            .replace("{summary}", summary)
        )

        # Instrucciones adicionales invariantes
        extra = "\n\n[INSTRUCCIONES ADICIONALES CRÍTICAS]:\n"
        if is_enhancement:
            extra += (
                "ATENCIÓN: Estás analizando un SEGMENTO CRÍTICO de la partida. "
                "Sé extremadamente profundo, analiza las variantes tácticas sugeridas por Stockfish "
                "y explica por qué la evaluación cambió bruscamente.\n"
            )
        else:
            extra += (
                "1. BALANCE DE APERTURA: Inserta OBLIGATORIAMENTE un comentario final de la fase de apertura "
                "con la etiqueta { [BALANCE DE LA APERTURA]: ... }. Hazlo exactamente en la jugada que marca "
                "'DESVÍO TEORÍA', o si todo fue teórico, al finalizar la jugada 20.\n"
            )

        extra += "2. VARIACIONES PGN: Asegúrate de que sean PGN válido.\n"
        extra += "3. ESTRUCTURA DE CIERRE: La última jugada debe tener [MOMENTOS CRÍTICOS] y [LECCIONES].\n"
        extra += "4. PRECISIÓN GEOMÉTRICA (CRÍTICO): Mantén siempre la perspectiva de las blancas al mencionar coordenadas (1-8 y a-h) y diagonales fijas.\n"

        if self.use_search:
            extra += "5. SEARCH GROUNDING: Usa la búsqueda para verificar teoría de apertura.\n"

        return prompt + extra

    def _build_fallback_list(self, primary_model: str) -> list[str]:
        """Devuelve la lista ordenada de modelos a intentar, sin duplicados."""
        models = [primary_model]

        name = primary_model.lower()
        if "pro" in name:
            if "2.5" in name:
                models.extend(["gemini-2.5-flash", "gemini-3.1-flash-lite-preview", "gemma-3-27b-it"])
            else:
                models.extend(["gemini-2.5-pro", "gemini-2.5-flash", "gemini-3.1-flash-lite-preview", "gemma-3-27b-it"])
        elif "flash" in name:
            if "2.0" in name:
                models.extend(["gemini-2.5-flash", "gemini-3.1-flash-lite-preview", "gemma-3-27b-it"])
            else:
                models.extend(["gemini-2.0-flash", "gemini-3.1-flash-lite-preview", "gemma-3-27b-it"])

        # Añadir modelos de rescate como failsafe
        models.extend(RESCUE_MODELS)

        # Deduplicar preservando orden
        seen: set[str] = set()
        return [x for x in models if not (x in seen or seen.add(x))]  # type: ignore[func-returns-value]

    def _log(self, message: str) -> None:
        """Añade una entrada al log de errores."""
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- {time.ctime()} {message} ---\n")
        except Exception:
            pass
