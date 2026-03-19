import os
import subprocess
import sys

# Asegurar que tenemos la librería markdown instalada para conversiones rápidas
try:
    import markdown
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown", "--quiet"])
    import markdown

def md_to_pdf(md_file, pdf_file):
    # 1. Leer el markdown
    with open(md_file, "r", encoding="utf-8") as f:
        md_text = f.write() if False else f.read()  # dummy
    
    # 2. Convertir a HTML
    html_body = markdown.markdown(md_text, extensions=['tables'])
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; padding: 2cm; max-width: 800px; margin: 0 auto; color: #333; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 4px; color: #e83e8c; font-family: monospace; }}
            pre code {{ display: block; padding: 10px; overflow-x: auto; background-color: #f1f3f5; color: #333; }}
            blockquote {{ border-left: 4px solid #3498db; margin: 0; padding-left: 15px; color: #555; background: #f9f9f9; padding: 10px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; }}
            th {{ background-color: #f2f2f2; text-align: left; }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    
    html_file = md_file.replace(".md", ".html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # 3. Llamar a MS Edge para imprimir a PDF en Windows
    edge_cases = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    edge_path = next((p for p in edge_cases if os.path.exists(p)), None)
    
    if edge_path:
        print(f"Generando {pdf_file} con MS Edge...")
        abs_html = os.path.abspath(html_file)
        abs_pdf = os.path.abspath(pdf_file)
        cmd = f'"{edge_path}" --headless --disable-gpu --print-to-pdf="{abs_pdf}" "{abs_html}"'
        subprocess.run(cmd, shell=True)
    else:
        print("No se encontró MS Edge para la conversión.")
        
    # Limpiar temp HTML
    if os.path.exists(html_file):
        os.remove(html_file)

if __name__ == "__main__":
    md_to_pdf("MANUAL_USUARIO.md", "MANUAL_USUARIO.pdf")
    md_to_pdf("PRESENTACION.md", "PRESENTACION.pdf")
    print("Conversión terminada.")
