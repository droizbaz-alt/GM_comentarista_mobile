"""
app.py — GM Comentarista (Versión Móvil / PWA)
Optimizado para Streamlit Cloud + navegadores móviles.
"""
import streamlit as st
import chess
import chess.pgn
import chess.engine
import io
import os
import time
import traceback
import asyncio
import sys
import re
import datetime
import warnings

from commentary_engine import CommentaryEngine
from ai_client import AIClient, QUALITY_PROFILES
import lichess_api
from chess_component import chess_board

# ─── Windows asyncio fix (solo en local) ───────────────────────────────────
if sys.platform == "win32":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ─── Stockfish (cloud: se usa el binario del servidor) ─────────────────────
def find_stockfish():
    if os.environ.get("STOCKFISH_PATH"):
        return os.environ["STOCKFISH_PATH"]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        "/usr/games/stockfish",           # Streamlit Cloud (Ubuntu)
        "/usr/bin/stockfish",
        "/usr/local/bin/stockfish",
        os.path.join(script_dir, "stockfish"),
        os.path.join(script_dir, "stockfish.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return "stockfish"  # esperar que esté en PATH

STOCKFISH_PATH = find_stockfish()

# ─── Configuración de página ── modo wide para móvil horizontal también ────
st.set_page_config(
    page_title="GM Comentarista",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="collapsed",   # 📱 sidebar cerrada por defecto en móvil
)

# ─── CSS Mobile-First ───────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Variables de color ── */
:root {
    --accent: #4A90D9;
    --accent2: #e8b84b;
    --bg: #1a1a2e;
    --card: #16213e;
    --text: #eaeaea;
    --muted: #8892a4;
}

/* ── Fondo global ── */
.stApp { background: var(--bg); color: var(--text); }
[data-testid="stSidebar"] { background: #0f0f1a; }

/* ── Ocultar decoraciones de Streamlit ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* ── Título principal ── */
.gm-header {
    text-align: center;
    padding: 1rem 0 0.5rem;
    font-size: clamp(1.4rem, 5vw, 2rem);
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.gm-sub {
    text-align: center;
    color: var(--muted);
    font-size: 0.85rem;
    margin-bottom: 1.2rem;
}

/* ── Tarjetas de sección ── */
.card {
    background: var(--card);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    border: 1px solid rgba(74,144,217,0.15);
}

/* ── Tablero de ajedrez responsive ── */
iframe[title="chess_board"] {
    max-width: 100% !important;
    width: 100% !important;
}
#board { width: 100% !important; }

/* ── Botones grandes y táctiles ── */
.stButton > button {
    width: 100%;
    min-height: 48px;
    font-size: 1rem;
    border-radius: 10px;
    font-weight: 600;
    background: linear-gradient(135deg, var(--accent), #2c6fc0);
    color: white;
    border: none;
    transition: transform .15s, box-shadow .15s;
}
.stButton > button:active {
    transform: scale(0.97);
}
.stButton > button:hover {
    box-shadow: 0 4px 20px rgba(74,144,217,0.4);
}

/* ── Sliders y selects más grandes ── */
.stSlider [data-baseweb="slider"] { cursor: pointer; }
.stSlider > div { padding: 0.5rem 0; }
.stSelectbox select { font-size: 1rem; min-height: 44px; }
.stTextInput input { min-height: 44px; font-size: 1rem; border-radius: 8px; }
.stRadio label { font-size: 1rem; padding: 0.35rem 0; }

/* ── Tabs scroll horizontal en móvil ── */
[data-testid="stHorizontalBlock"] { gap: 0.5rem; }
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    flex-wrap: nowrap;
}
.stTabs [data-baseweb="tab"] {
    white-space: nowrap;
    min-width: fit-content;
    padding: 0.5rem 0.8rem;
    font-size: 0.85rem;
}

/* ── Comentarios IA ── */
.stAlert { border-radius: 10px; font-size: 0.95rem; line-height: 1.6; }

/* ── Progress bar ── */
.stProgress > div > div { background: var(--accent); border-radius: 8px; }

/* ── Expander ── */
[data-testid="stExpander"] details {
    border: 1px solid rgba(74,144,217,0.2);
    border-radius: 10px;
    background: var(--card);
}

/* ── Métricas ── */
[data-testid="stMetric"] {
    background: var(--card);
    border-radius: 10px;
    padding: 0.75rem;
    border: 1px solid rgba(74,144,217,0.15);
}

/* ── Sidebar overlay en móvil ── */
@media (max-width: 768px) {
    .main .block-container { padding: 0.5rem 0.75rem 2rem; }
    [data-testid="stSidebar"][aria-expanded="true"] { width: 85vw !important; }
}
</style>
""", unsafe_allow_html=True)

# ─── Header ────────────────────────────────────────────────────────────────
st.markdown('<div class="gm-header">♟️ GM Comentarista</div>', unsafe_allow_html=True)
st.markdown('<div class="gm-sub">Análisis pedagógico con IA · Nivel Gran Maestro</div>', unsafe_allow_html=True)

# ─── Sidebar: Configuración ─────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")

    # Perfiles de análisis
    PROFILES = {
        "⚡ Rápido":   {"depth": 12, "threads": 1, "critical_threshold": 1.0,  "quality": "Básica",  "desc": "Ideal para revisar rápidamente."},
        "⚖️ Estándar": {"depth": 16, "threads": 2, "critical_threshold": 0.75, "quality": "Media",   "desc": "Equilibrio velocidad/calidad. ✅"},
        "🏆 Profundo": {"depth": 20, "threads": 2, "critical_threshold": 0.5,  "quality": "Alta",    "desc": "Análisis exhaustivo con modelos Pro."},
    }
    sel_profile = st.radio("Perfil", list(PROFILES.keys()), index=1)
    profile = PROFILES[sel_profile]
    st.caption(profile["desc"])
    st.divider()

    st.header("🧠 IA Gemini")
    use_ai   = st.checkbox("Activar comentarios", value=True)
    api_key  = st.text_input("API Key de Gemini", type="password",
                             help="Consigue tu clave gratis en aistudio.google.com")
    use_hybrid = st.checkbox("🚀 Modo Híbrido", value=True,
                             help="Modelos rápidos para jugadas normales + Pro para momentos críticos.")
    st.divider()

    st.header("💾 Caché")
    use_cache = st.checkbox("Activar caché de IA", value=True)
    if use_cache:
        from cache_manager import CacheManager
        cm = CacheManager()
        stats = cm.get_stats()
        st.caption(f"📊 {stats['count']} posiciones guardadas")
        if st.button("🗑️ Limpiar caché"):
            if cm.clear():
                st.success("Caché vaciada")
                st.rerun()

    # Valores base desde el perfil
    depth              = profile["depth"]
    threads            = profile["threads"]
    critical_threshold = profile["critical_threshold"]
    quality            = profile["quality"]
    ai_lite_model      = QUALITY_PROFILES[quality]["lite"]
    ai_pro_model       = QUALITY_PROFILES[quality]["pro"]

    with st.expander("🔬 Ajustes Avanzados"):
        depth             = st.slider("Profundidad Stockfish", 10, 24, depth)
        threads           = st.slider("Hilos CPU", 1, 4, threads)
        critical_threshold = st.slider("Umbral Crítico", 0.1, 2.0, critical_threshold, 0.05)
        model_options = [
            "gemini-3.1-flash-lite-preview", "gemma-3-27b-it",
            "gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.1-pro-preview",
        ]
        ai_lite_model = st.selectbox("Modelo Base", model_options,
            index=model_options.index(ai_lite_model) if ai_lite_model in model_options else 0)
        ai_pro_model  = st.selectbox("Modelo Pro", model_options,
            index=model_options.index(ai_pro_model) if ai_pro_model in model_options else 3)

    with st.expander("📝 Prompt de la IA"):
        prompt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AI_PROMPT.txt")
        cur_prompt  = open(prompt_file, encoding="utf-8").read() if os.path.exists(prompt_file) else ""
        new_prompt  = st.text_area("Prompt personalizado", value=cur_prompt, height=180)
        if st.button("💾 Guardar prompt"):
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(new_prompt)
            st.success("Guardado.")

# ─── Session state ──────────────────────────────────────────────────────────
for key, default in {
    "pgn_to_analyze": None,
    "output_pgn":     None,
    "last_ai_error":  None,
    "last_move_ts":   0,
    "pgn_counter":    0,
    "viewer_node":    None,
    "viewer_game":    None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Carga de Partida ───────────────────────────────────────────────────────
st.header("📥 Cargar Partida")
tab_local, tab_lichess, tab_historial, tab_crear = st.tabs(
    ["📂 Archivo PGN", "🔗 Lichess", "📋 Historial", "✏️ Crear"]
)

with tab_local:
    uploaded = st.file_uploader("Sube tu PGN", type=["pgn"])
    if uploaded:
        content = uploaded.getvalue().decode("utf-8", errors="replace")
        if content != st.session_state.pgn_to_analyze:
            st.session_state.pgn_to_analyze = content
            st.session_state.output_pgn     = None

with tab_lichess:
    lichess_input = st.text_input("Usuario o ID de partida Lichess",
                                  placeholder="Ej: Hikaru  o  abc12345")
    if lichess_input:
        if len(lichess_input) == 8 or "lichess.org" in lichess_input:
            if st.button("⬇️ Importar partida"):
                with st.spinner("Descargando…"):
                    pgn_str, err = lichess_api.get_game_pgn(lichess_input)
                    if not err:
                        st.session_state.pgn_to_analyze = pgn_str
                        st.session_state.output_pgn     = None
                        st.success("✅ Partida cargada")
                    else:
                        st.error(f"Error: {err}")
        else:
            if st.button("🔍 Buscar últimas partidas"):
                games, err = lichess_api.get_user_last_games(lichess_input)
                if games:
                    st.session_state.lichess_games = games
                    st.session_state.lichess_user  = lichess_input
                else:
                    st.error(f"No se encontraron partidas: {err}")
            if st.session_state.get("lichess_games") and st.session_state.get("lichess_user") == lichess_input:
                options = {lichess_api.format_game_label(g, lichess_input): g["id"]
                           for g in st.session_state.lichess_games}
                sel = st.selectbox("Selecciona una partida:", list(options.keys()))
                if st.button("📥 Cargar seleccionada"):
                    with st.spinner("Cargando…"):
                        pgn_str, err = lichess_api.get_game_pgn(options[sel])
                        if not err:
                            st.session_state.pgn_to_analyze = pgn_str
                            st.session_state.output_pgn     = None

with tab_historial:
    hist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historial_analisis")
    os.makedirs(hist_dir, exist_ok=True)
    # Listar subcarpetas
    subdirs  = ["General"] + [d for d in os.listdir(hist_dir)
                               if os.path.isdir(os.path.join(hist_dir, d)) and d != "General"]
    sel_folder = st.selectbox("Carpeta:", subdirs)
    f_path   = os.path.join(hist_dir, sel_folder)
    pgn_files = sorted(
        [f for f in os.listdir(f_path) if f.endswith(".pgn")],
        key=lambda x: os.path.getctime(os.path.join(f_path, x)), reverse=True
    ) if os.path.exists(f_path) else []
    if pgn_files:
        sel_file = st.selectbox("Análisis:", pgn_files)
        if st.button("👁️ Cargar análisis"):
            with open(os.path.join(f_path, sel_file), encoding="utf-8") as f:
                st.session_state.pgn_to_analyze = f.read()
                st.session_state.output_pgn     = st.session_state.pgn_to_analyze
    else:
        st.caption("No hay análisis guardados en esta carpeta.")

with tab_crear:
    st.subheader("✏️ Crear Partida")
    if "manual_pgn" not in st.session_state:
        g = chess.pgn.Game()
        g.headers.update({"Event": "Partida Amistosa", "Site": "GM Comentarista Mobile",
                          "Date": datetime.datetime.now().strftime("%Y.%m.%d"),
                          "White": "?", "Black": "?"})
        st.session_state.manual_pgn = str(g)

    def _on_pgn_change():
        st.session_state.manual_pgn = st.session_state[f"pgn_ed_{st.session_state.pgn_counter}"]

    st.text_area("PGN (edita cabeceras o jugadas):", value=st.session_state.manual_pgn,
                 height=160, key=f"pgn_ed_{st.session_state.pgn_counter}", on_change=_on_pgn_change)

    try:
        tmp = chess.pgn.read_game(io.StringIO(st.session_state.manual_pgn))
        cur_fen = tmp.end().board().fen() if tmp else chess.STARTING_FEN
    except Exception:
        cur_fen = chess.STARTING_FEN
        tmp = chess.pgn.Game()

    res = chess_board(fen=cur_fen, key="creator_board")
    if res and res != "none":
        move_val = res.get("move") if isinstance(res, dict) else res
        ts       = res.get("ts", 0) if isinstance(res, dict) else 0
        if move_val and ts != st.session_state.last_move_ts:
            st.session_state.last_move_ts = ts
            try:
                m = chess.Move.from_uci(move_val)
                board_test = tmp.end().board()
                if m in board_test.legal_moves:
                    tmp.end().add_main_variation(m)
                    st.session_state.manual_pgn = str(tmp)
                    st.session_state.pgn_counter += 1
                    st.rerun()
            except Exception:
                pass

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Reiniciar", use_container_width=True):
            for k in ["manual_pgn", "last_move_ts", "pgn_counter"]:
                st.session_state.pop(k, None)
            st.rerun()
    with col2:
        if st.button("📥 Analizar esta partida", use_container_width=True):
            st.session_state.pgn_to_analyze = st.session_state.manual_pgn
            st.session_state.output_pgn     = None
            st.success("¡Cargada! Baja a la sección de análisis.")

# ─── Análisis ───────────────────────────────────────────────────────────────
if st.session_state.pgn_to_analyze:
    st.divider()
    col_ok, col_clear = st.columns([3, 1])
    col_ok.success("✅ Partida cargada — lista para analizar")
    if col_clear.button("🗑️ Limpiar", use_container_width=True, help="Descartar esta partida y cargar otra"):
        st.session_state.pgn_to_analyze = None
        st.session_state.output_pgn     = None
        st.session_state.viewer_game    = None
        st.session_state.viewer_node    = None
        st.rerun()

    if st.button("🚀 Generar Comentarios", type="primary", use_container_width=True):
        st.session_state.output_pgn    = None
        st.session_state.last_ai_error = None

        progress_bar = st.progress(0.0)
        status_text  = st.empty()
        time_text    = st.empty()

        try:
            start_time = time.time()
            engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH, timeout=30.0)
            engine.configure({"Threads": threads})

            commentator = CommentaryEngine(
                engine, depth=depth, api_key=api_key,
                knowledge_context=None,
                enable_ai=use_ai,
                model_name=ai_lite_model,
                pro_model_name=ai_pro_model,
                lite_model_name=ai_lite_model,
                use_hybrid=use_hybrid,
                critical_threshold=critical_threshold,
                use_cache=use_cache,
            )
            game = chess.pgn.read_game(io.StringIO(st.session_state.pgn_to_analyze))
            total_plies = sum(1 for _ in game.mainline_moves()) or 1

            def update_progress(current, turn, status="engine"):
                if status == "engine":
                    prog = (current / total_plies) * 0.6
                    progress_bar.progress(min(prog, 0.6))
                    elapsed = time.time() - start_time
                    eta = int((total_plies - current) * (elapsed / max(current, 1))) + 20
                    status_text.info(f"♟️ Analizando… {current}/{total_plies} jugadas")
                    time_text.caption(f"ETA: ~{max(eta, 0)}s")
                elif status == "ai_start":
                    progress_bar.progress(0.7)
                    status_text.warning("🧠 Generando comentarios con IA…")
                elif status == "ai_enhancing":
                    prog = 0.75 + (current / max(turn or 1, 1)) * 0.1
                    progress_bar.progress(min(prog, 0.85))
                    status_text.error(f"🔍 Analizando momento crítico {current}/{turn}…")
                elif status == "syncing":
                    progress_bar.progress(0.9)
                    status_text.info("🔄 Sincronizando árbol PGN…")
                elif status == "saving":
                    progress_bar.progress(0.98)
                    status_text.success("💾 Guardando análisis…")

            st.session_state.output_pgn = commentator.analyze_game(game, callback=update_progress)
            if commentator.last_error:
                st.session_state.last_ai_error = commentator.last_error

            update_progress(0, None, status="saving")
            engine.quit()

            # Auto-guardar en historial
            try:
                hist_root = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "historial_analisis", "General")
                os.makedirs(hist_root, exist_ok=True)
                fn = f"analisis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pgn"
                with open(os.path.join(hist_root, fn), "w", encoding="utf-8") as f:
                    f.write(st.session_state.output_pgn)
            except Exception:
                pass

            status_text.success("✅ ¡Análisis completado!")
            progress_bar.progress(1.0)
            st.rerun()

        except FileNotFoundError:
            st.error("⚠️ Stockfish no encontrado. En Streamlit Cloud, añade un paquete `packages.txt` con `stockfish`.")
        except Exception as e:
            st.error(f"❌ Error: {e}")
            with st.expander("Detalles del error"):
                st.code(traceback.format_exc())

# ─── Visualizador de Resultados ──────────────────────────────────────────────
if st.session_state.output_pgn:
    st.divider()
    st.subheader("✅ Análisis Completado")

    # Alerta de error en IA (si la hubo)
    if st.session_state.last_ai_error:
        with st.expander("⚠️ Incidencias de la IA"):
            msg = st.session_state.last_ai_error
            st.warning(msg)
            if "429" in msg:
                st.error("📉 Cuota agotada. Prueba con otro modelo en Ajustes Avanzados.")

    # Cargar partida si cambió
    if (st.session_state.viewer_game is None or
            st.session_state.get("_prev_output") != st.session_state.output_pgn):
        st.session_state.viewer_game = chess.pgn.read_game(
            io.StringIO(st.session_state.output_pgn))
        st.session_state.viewer_node  = st.session_state.viewer_game
        st.session_state["_prev_output"] = st.session_state.output_pgn

    game_obj = st.session_state.viewer_game
    node     = st.session_state.viewer_node

    # ── Navegación: botones grandes táctiles ────────────────────────────────
    mainline   = list(game_obj.mainline())
    total_plies = len(mainline)
    cur_ply    = node.ply()

    col_start, col_prev, col_slider, col_next, col_end = st.columns([1, 1, 4, 1, 1])
    if col_start.button("⏮", use_container_width=True):
        st.session_state.viewer_node = game_obj; st.rerun()
    if col_prev.button("◀", use_container_width=True):
        if node.parent: st.session_state.viewer_node = node.parent; st.rerun()
    new_ply = col_slider.slider("Jugada", 0, total_plies, cur_ply, label_visibility="collapsed")
    if new_ply != cur_ply:
        n = game_obj
        for _ in range(new_ply):
            if n.variations: n = n.variation(0)
            else: break
        st.session_state.viewer_node = n; st.rerun()
    if col_next.button("▶", use_container_width=True):
        if node.variations: st.session_state.viewer_node = node.variation(0); st.rerun()
    if col_end.button("⏭", use_container_width=True):
        st.session_state.viewer_node = game_obj.end(); st.rerun()

    # ── Tablero + Comentario ─────────────────────────────────────────────────
    board = node.board()

    # En móvil mostramos el tablero arriba y el comentario debajo (1 columna)
    chess_board(fen=board.fen(), key="viewer_board")

    comment = node.comment
    if comment:
        clean = re.sub(r"\[%.*?\]", "", comment).strip()
        if clean:
            st.info(clean)
    else:
        st.caption("Mueve el slider o los botones para ver los comentarios de cada jugada.")

    # ── Variantes disponibles ────────────────────────────────────────────────
    if len(node.variations) > 1:
        st.warning("⚠️ Variantes disponibles en esta posición:")
        for i, var in enumerate(node.variations):
            label = f"Línea {i+1}: {board.san(var.move)}"
            if i == 0: label += " (Principal)"
            if st.button(label, key=f"var_{node.ply()}_{i}"):
                st.session_state.viewer_node = var; st.rerun()

    # ── Crónica completa ─────────────────────────────────────────────────────
    with st.expander("📜 Crónica completa"):
        nodes_list = []
        cur = game_obj
        while cur:
            nodes_list.append(cur)
            cur = cur.next() if cur.variations else None

        for n in nodes_list:
            if not n.parent: continue
            move_san = n.parent.board().san(n.move)
            move_num = (n.ply() + 1) // 2
            prefix   = f"{move_num}." if n.ply() % 2 != 0 else ""
            c1, c2   = st.columns([1, 4])
            if c1.button(f"{prefix}{move_san}", key=f"nav_{n.ply()}"):
                st.session_state.viewer_node = n; st.rerun()
            if n.comment:
                c_txt = re.sub(r"\[%.*?\]", "", n.comment).strip()
                if c_txt: c2.markdown(f"*{c_txt}*")
            else:
                c2.caption("-")

    # ── Descarga ─────────────────────────────────────────────────────────────
    st.divider()
    st.download_button(
        "📥 Descargar PGN Comentado",
        st.session_state.output_pgn,
        f"gm_analisis_{int(time.time())}.pgn",
        use_container_width=True,
    )
    with st.expander("📋 Ver PGN completo"):
        st.text_area("", value=st.session_state.output_pgn, height=300)

    if st.button("🔄 Nueva partida", use_container_width=True):
        st.session_state.output_pgn     = None
        st.session_state.pgn_to_analyze = None
        st.session_state.viewer_game    = None
        st.session_state.viewer_node    = None
        st.rerun()
