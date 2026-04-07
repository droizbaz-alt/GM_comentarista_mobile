from flask import Flask, request, jsonify
import sys
import os
import io

app = Flask(__name__)

# Configuración básica de CORS para desarrollo y producción
from flask_cors import CORS
CORS(app)

@app.route('/api/health', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "version": "1.0.5", "message": "Python GM API is alive and lazy"})

@app.route('/api/debug', methods=['GET'])
@app.route('/debug', methods=['GET'])
def debug():
    """Endpoint para diagnosticar la salud de los módulos en Vercel."""
    info = {
        "cwd": os.getcwd(),
        "sys_path": sys.path,
        "env": {k: v for k, v in os.environ.items() if "KEY" not in k and "SECRET" not in k},
        "modules": {}
    }
    
    # Probar importaciones críticas
    try:
        import chess
        info["modules"]["chess"] = "OK"
    except Exception as e:
        info["modules"]["chess"] = f"Error: {e}"
        
    try:
        import requests
        info["modules"]["requests"] = "OK"
    except Exception as e:
        info["modules"]["requests"] = f"Error: {e}"
        
    return jsonify(info)

@app.route('/api/analyze/position', methods=['POST'])
@app.route('/analyze/position', methods=['POST'])
def analyze_position():
    """Consulta Lichess Cloud Eval y Tablebases de forma robusta."""
    import requests # Import dinámico
    
    data = request.json
    fen = data.get('fen')
    if not fen: return jsonify({"error": "FEN is required"}), 400
    
    results = {"eval": None, "tb": None}
    
    try:
        # 1. Cloud Eval (Stockfish 16.1)
        res = requests.get("https://lichess.org/api/cloud-eval", params={'fen': fen}, timeout=3)
        if res.status_code == 200:
            eval_data = res.json()
            pvs = eval_data.get('pvs', [])
            if pvs:
                results["eval"] = {"cp": pvs[0].get('cp'), "mate": pvs[0].get('mate')}
                
        # 2. Tablebase (Syzygy) - Solo si hay pocas piezas
        piece_count = fen.split()[0].replace('/', '')
        for d in "12345678": piece_count = piece_count.replace(d, '')
        
        if len(piece_count) <= 7:
            res_tb = requests.get("https://tablebase.lichess.ovh/standard", params={'fen': fen}, timeout=3)
            if res_tb.status_code == 200:
                results["tb"] = res_tb.json()
    except Exception as e:
        # Silencioso en producción para evitar 500s innecesarios
        return jsonify({"eval": None, "tb": None, "note": str(e)})
    
    return jsonify(results)

@app.route('/api/commentate', methods=['POST'])
@app.route('/commentate', methods=['POST'])
def commentate():
    try:
        # Importación diferida para evitar fallos de arranque
        import chess.pgn
        from commentary_engine import CommentaryEngine
        from ai_client import QUALITY_PROFILES
        
        data = request.json
        pgn_text = data.get('pgn')
        metadata = data.get('metadata')
        api_key = data.get('api_key')
        quality = data.get('quality', 'Media')
        use_hybrid = data.get('use_hybrid', True)
        
        if not pgn_text or not metadata:
            return jsonify({"error": "Faltan datos PGN o metadatos"}), 400

        commentator = CommentaryEngine(
            None, 
            api_key=api_key,
            enable_ai=True,
            model_name=QUALITY_PROFILES[quality]["lite"],
            pro_model_name=QUALITY_PROFILES[quality]["pro"],
            lite_model_name=QUALITY_PROFILES[quality]["lite"],
            use_hybrid=use_hybrid,
            use_cache=True
        )

        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if not game: return jsonify({"error": "PGN inválido"}), 400

        commented_pgn = commentator.commentate_preanalyzed_game(
            game, metadata, data.get('critical_moments', [])
        )

        return jsonify({
            "pgn": commented_pgn,
            "error": commentator.last_error
        })

    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/lichess/user', methods=['POST'])
@app.route('/lichess/user', methods=['POST'])
def lichess_user():
    from lichess_api import get_user_last_games, format_game_label
    data = request.json
    username = data.get('username')
    games, error = get_user_last_games(username)
    if error: return jsonify({"error": error}), 400
    
    formatted = []
    for g in games:
        formatted.append({
            "id": g.get("id"),
            "label": format_game_label(g, username),
            "pgn": g.get("pgn")
        })
    return jsonify({"games": formatted})

# Soporte para Lichess single game
@app.route('/api/lichess/game', methods=['POST'])
@app.route('/lichess/game', methods=['POST'])
def lichess_game():
    from lichess_api import get_game_pgn
    data = request.json
    url_or_id = data.get('url_or_id')
    pgn, error = get_game_pgn(url_or_id)
    if error: return jsonify({"error": error}), 400
    return jsonify({"pgn": pgn})

if __name__ == '__main__':
    app.run(debug=True)
