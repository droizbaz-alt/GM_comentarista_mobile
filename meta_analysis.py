import os
import chess.pgn
from google import genai
import streamlit as st

def parse_folder_stats(folder_path, user_name_query):
    stats = {'total_games': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'as_white': 0, 'as_black': 0, 'openings_white': {}, 'openings_black': {}}
    if not os.path.exists(folder_path): return stats
    for filename in os.listdir(folder_path):
        if not filename.endswith('.pgn'): continue
        try:
            with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
                game = chess.pgn.read_game(f)
                if not game: continue
                headers = game.headers
                white, black = headers.get("White", "").lower(), headers.get("Black", "").lower()
                res, op = headers.get("Result", "*"), headers.get("Opening", headers.get("ECO", "Desconocida"))
                user_q = user_name_query.lower().strip()
                is_w = user_q in white if user_q else True
                is_b = user_q in black if user_q else False
                if not is_w and not is_b: continue
                stats['total_games'] += 1
                if is_w:
                    stats['as_white'] += 1
                    stats['openings_white'][op] = stats['openings_white'].get(op, 0) + 1
                    if res == "1-0": stats['wins'] += 1
                    elif res == "0-1": stats['losses'] += 1
                    else: stats['draws'] += 1
                else:
                    stats['as_black'] += 1
                    stats['openings_black'][op] = stats['openings_black'].get(op, 0) + 1
                    if res == "0-1": stats['wins'] += 1
                    elif res == "1-0": stats['losses'] += 1
                    else: stats['draws'] += 1
        except: pass
    return stats

def generate_trend_report(folder_path, user_name, api_key, model_name='gemini-2.0-flash', max_games=20):
    if not os.path.exists(folder_path): return "La carpeta no existe."
    pgn_files = [f for f in os.listdir(folder_path) if f.endswith('.pgn')]
    if not pgn_files: return "No hay partidas."
    pgn_files.sort(key=lambda x: os.path.getctime(os.path.join(folder_path, x)), reverse=True)
    all_texts = []
    for filename in pgn_files[:max_games]:
        try:
            with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) > 50: all_texts.append(f"--- {filename} ---\n{content}")
        except: pass
    if not all_texts: return "No se pudieron leer las partidas."
    combined = "\n\n".join(all_texts)
    prompt = f"Analiza estas partidas del jugador '{user_name}' y extrae patrones críticos:\n\n{combined}"
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model_name, contents=prompt)
        return response.text
    except Exception as e: return f"Error IA: {e}"

def generate_pdf_report(stats, trend_report_text, folder_name):
    from fpdf import FPDF
    class PDFReport(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 16)
            self.cell(0, 10, f"Reporte de Rendimiento - Carpeta: {folder_name}", border=False, align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(5)
        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 10, f"Pagina {self.page_no()}", align="C")

    pdf = PDFReport()
    pdf.add_page()
    def clean_text(txt):
        if not txt: return ""
        replacements = {'🏆': '', '🤝': '', '❌': '', '🧠': '', '📊': '', '⚠️': '', '✅': '', '♟️': '', '“': '"', '”': '"', "‘": "'", "’": "'", "—": "-", 'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'ñ': 'n', 'Ñ': 'N', '¿': '?', '¡': '!'}
        for k, v in replacements.items(): txt = txt.replace(k, v)
        return txt.encode('latin-1', 'ignore').decode('latin-1')

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, clean_text("1. Resumen Estadistico"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, clean_text(f"Total Partidas: {stats.get('total_games', 0)}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, clean_text(f"V: {stats.get('wins', 0)} | T: {stats.get('draws', 0)} | D: {stats.get('losses', 0)}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12); pdf.cell(0, 8, clean_text("Aperturas (Blancas):"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for op, val in stats.get('openings_white', {}).items(): pdf.cell(0, 6, clean_text(f"- {op}: {val}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5); pdf.set_font("Helvetica", "B", 12); pdf.cell(0, 8, clean_text("Aperturas (Negras):"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for op, val in stats.get('openings_black', {}).items(): pdf.cell(0, 6, clean_text(f"- {op}: {val}"), new_x="LMARGIN", new_y="NEXT")
    
    pdf.add_page(); pdf.set_font("Helvetica", "B", 14); pdf.cell(0, 10, clean_text("2. Reporte de Tendencias (IA)"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5); pdf.set_font("Helvetica", "", 11)
    clean_report = clean_text(trend_report_text).replace("**", "").replace("#", "")
    pdf.multi_cell(0, 6, clean_report)
    return bytes(pdf.output(dest='S'))
