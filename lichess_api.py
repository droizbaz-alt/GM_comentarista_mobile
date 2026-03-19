import requests
import json
import time
import streamlit as st

def get_game_pgn(game_id):
    game_id = game_id.split("/")[-1]
    if len(game_id) > 8: game_id = game_id[:8]
    url = f"https://lichess.org/game/export/{game_id}"
    try:
        res = requests.get(url, headers={"Accept": "application/x-chess-pgn"}, params={"clocks": "true", "evals": "true", "literate": "true"}, timeout=10)
        if res.status_code == 200: return res.text, None
        return None, f"Error {res.status_code}"
    except Exception as e: return None, str(e)

def get_user_last_games(username, limit=10):
    username = username.strip().split("/")[-1]
    url = f"https://lichess.org/api/games/user/{username}"
    try:
        res = requests.get(url, headers={"Accept": "application/x-ndjson"}, params={"max": limit, "pgnInJson": "true"}, timeout=10)
        if res.status_code == 200:
            games = [json.loads(line) for line in res.text.strip().split('\n') if line]
            return games, None
        return None, f"Error {res.status_code}"
    except Exception as e: return None, str(e)

def format_game_label(game, target_username):
    try:
        white = game.get("players", {}).get("white", {}).get("user", {}).get("name", "Anon")
        black = game.get("players", {}).get("black", {}).get("user", {}).get("name", "Anon")
        playing_as = "Blancas" if white.lower() == target_username.lower() else "Negras"
        opponent = black if playing_as == "Blancas" else white
        winner = game.get("winner", None)
        res = "1-0" if winner == "white" else "0-1" if winner == "black" else "1/2-1/2"
        return f"[{res}] como {playing_as} vs {opponent} ({game.get('speed', 'chess')}) - ID: {game.get('id', '')}"
    except: return f"Partida {game.get('id', 'desconocida')}"

@st.cache_data(ttl=86400, max_entries=1000, show_spinner=False)
def get_opening_stats(fen, mode="lichess"):
    url = f"https://explorer.lichess.ovh/{mode}"
    try:
        res = requests.get(url, params={"fen": fen, "speeds": "blitz,rapid,classical", "ratings": "1600,1800,2000,2200,2500"}, timeout=5)
        if res.status_code == 200: return res.json(), None
        return None, f"Error {res.status_code}"
    except Exception as e: return None, str(e)
