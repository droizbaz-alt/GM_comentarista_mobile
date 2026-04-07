from flask import Flask, request, jsonify
import sys
import os
import io
import chess.pgn

# Añadir directorio raíz al path para importar módulos locales
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commentary_engine import CommentaryEngine
from ai_client import QUALITY_PROFILES

app = Flask(__name__)

@app.route('/api/commentate', methods=['POST'])
def commentate():
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
