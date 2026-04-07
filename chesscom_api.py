import requests
import json

def get_user_last_games_chesscom(username, limit=10):
    username = username.strip()
    # 1. Obtener archivos mensuales
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    try:
        headers = {"User-Agent": "GM-Comentarista-Mobile (droizbaz-alt)"}
        res = requests.get(archives_url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None, f"Error Chess.com: {res.status_code}"
        
        archives = res.json().get("archives", [])
        if not archives:
            return [], None
            
        # 2. Obtener el último mes de actividad
        last_archive_url = archives[-1]
        res_games = requests.get(last_archive_url, headers=headers, timeout=10)
        if res_games.status_code != 200:
            return None, f"Error Archive: {res_games.status_code}"
            
        all_games = res_games.json().get("games", [])
        # Invertir para tener las más recientes al principio
        recent_games = all_games[::-1][:limit]
        
        # Formatear para que se parezca a la estructura que espera el frontend (similar a lichess)
        formatted_games = []
        for g in recent_games:
            game_id = g.get("url", "").split("/")[-1]
            formatted_games.append({
                "id": game_id,
                "pgn": g.get("pgn", ""),
                "url": g.get("url", ""),
                "players": {
                    "white": {"user": {"name": g.get("white", {}).get("username", "Anon")}},
                    "black": {"user": {"name": g.get("black", {}).get("username", "Anon")}}
                },
                "winner": "white" if g.get("white", {}).get("result") == "win" else "black" if g.get("black", {}).get("result") == "win" else "draw",
                "speed": g.get("time_class", "chess")
            })
            
        return formatted_games, None
    except Exception as e:
        return None, str(e)
