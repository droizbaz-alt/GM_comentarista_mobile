from flask import Flask, request, jsonify
import sys
import os
import io
import chess.pgn

# Añadir directorio raíz al path para importar módulos locales
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commentary_engine import CommentaryEngine
from ai_client import QUALITY_PROFILES
from lichess_api import get_game_pgn, get_user_last_games, format_game_label
from chesscom_api import get_user_last_games_chesscom

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/lichess/game', methods=['POST'])
def lichess_game():
    data = request.json
    url_or_id = data.get('url_or_id')
    pgn, error = get_game_pgn(url_or_id)
    if error: return jsonify({"error": error}), 400
    return jsonify({"pgn": pgn})

@app.route('/api/lichess/user', methods=['POST'])
def lichess_user():
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

@app.route('/api/chesscom/user', methods=['POST'])
def chesscom_user():
    data = request.json
    username = data.get('username')
    games, error = get_user_last_games_chesscom(username)
    if error: return jsonify({"error": error}), 400
    return jsonify({"games": games})

@app.route('/api/commentate', methods=['POST'])
def commentate():
    # ... existing commentate logic ...
    try:
        data = request.json
        pgn_text = data.get('pgn')
        # ...
    try:
        data = request.json
        pgn_text = data.get('pgn')
        metadata = data.get('metadata')
        critical_moments = data.get('critical_moments', [])
        api_key = data.get('api_key')
        
        # Perfiles de calidad
        quality = data.get('quality', 'Media')
        use_hybrid = data.get('use_hybrid', True)
        
        if not pgn_text or not metadata:
            return jsonify({"error": "Faltan datos PGN o metadatos de análisis"}), 400

        # Inicializar motor de comentarios (sin binario de Stockfish)
        # Pasamos None al motor porque no lo usaremos en este modo
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
        if not game:
            return jsonify({"error": "PGN inválido"}), 400

        commented_pgn = commentator.commentate_preanalyzed_game(
            game, metadata, critical_moments
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

if __name__ == '__main__':
    app.run(debug=True)
