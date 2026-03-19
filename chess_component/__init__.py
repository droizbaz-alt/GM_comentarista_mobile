import os
import streamlit.components.v1 as components

# Ruta al directorio del componente
_component_path = os.path.dirname(os.path.abspath(__file__))
_component_func = components.declare_component("chess_board", path=_component_path)

def chess_board(fen=None, key=None):
    """Llama al componente de tablero de ajedrez."""
    return _component_func(fen=fen, key=key, default="none", height=450)
