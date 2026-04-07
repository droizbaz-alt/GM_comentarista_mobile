'use client';

import React, { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import SettingsPanel from './SettingsPanel';
import { Chess } from 'chess.js';
import { 
  Play, 
  ChevronLeft, 
  ChevronRight, 
  ChevronsLeft, 
  ChevronsRight, 
  Save, 
  Download, 
  Import,
  Cpu,
  BrainCircuit,
  Zap
} from 'lucide-react';

const ChessBoard = dynamic(() => import('./ChessBoard'), { 
  ssr: false,
  loading: () => <div className="board-wrapper" style={{ background: '#1e293b', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <p style={{ color: 'var(--text-muted)' }}>Cargando tablero...</p>
  </div>
});

export default function GameContainer() {
  const [game, setGame] = useState<Chess | null>(null);
  const [currentFen, setCurrentFen] = useState('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
  const [history, setHistory] = useState<string[]>([]);
  const [commentary, setCommentary] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState('import');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [pgnInput, setPgnInput] = useState('');

  useEffect(() => {
    setGame(new Chess());
  }, []);

  const updateBoard = useCallback((newGame: Chess) => {
    setGame(newGame);
    setCurrentFen(newGame.fen());
    setHistory(newGame.history());
  }, []);

  const onMove = (orig: string, dest: string) => {
    if (!game) return;
    try {
      const newGame = new Chess(game.fen());
      const move = newGame.move({ from: orig, to: dest, promotion: 'q' });
      if (move) updateBoard(newGame);
    } catch (e) {
      console.error("Illegal move", e);
    }
  };

  const loadPgn = () => {
    if (!game) return;
    try {
      const newGame = new Chess();
      newGame.loadPgn(pgnInput);
      updateBoard(newGame);
      setActiveTab('analysis');
    } catch (e) {
      alert("PGN inválido");
    }
  };

  const startAnalysis = async () => {
    if (!game) return;
    setIsAnalyzing(true);
    setProgress(0);
    
    const metadata = game.history({ verbose: true }).map((m, i) => ({
      m: Math.floor(i / 2) + 1,
      t: i % 2 === 0 ? 'Bl' : 'Ne',
      san: m.san,
      eval: 0.35,
      loss: 0.05,
      rank: 1,
      fen: m.after,
      cap: m.flags.includes('c'),
      estrp: false
    }));

    try {
      setProgress(70);
      const apiKey = localStorage.getItem('gemini_api_key');
      const quality = localStorage.getItem('analysis_quality') || 'Media';

      const response = await fetch('/api/commentate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pgn: game.pgn(),
          metadata: metadata,
          api_key: apiKey,
          quality: quality
        })
      });

      const result = await response.json();
      if (result.pgn) {
        setCommentary((prev) => ({ ...prev, [game.fen()]: "Análisis completado." }));
        const commentedGame = new Chess();
        commentedGame.loadPgn(result.pgn);
        updateBoard(commentedGame);
      } else {
        alert("Error: " + (result.error || "Desconocido"));
      }
    } catch (err) {
      alert("Error de conexión");
    }
    
    setProgress(100);
    setIsAnalyzing(false);
    setActiveTab('analysis');
  };

  return (
    <>
      <header className="header animate-fade-in">
        <h1>♟️ GM Móvil</h1>
        <p>Tu entrenador Gran Maestro personalizado</p>
      </header>

      <div className="tabs animate-fade-in">
        <button className={`tab ${activeTab === 'import' ? 'active' : ''}`} onClick={() => setActiveTab('import')}>
          <Import size={16} /> Cargar
        </button>
        <button className={`tab ${activeTab === 'analysis' ? 'active' : ''}`} onClick={() => setActiveTab('analysis')}>
          <BrainCircuit size={16} /> Análisis
        </button>
        <button className={`tab ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
          <Cpu size={16} /> Ajustes
        </button>
      </div>

      {activeTab === 'import' && (
        <div className="card animate-fade-in">
          <div className="section-title"><Import size={20} /> Importar Partida</div>
          <textarea 
            className="input" 
            placeholder="Pega aquí tu PGN..." 
            rows={5} 
            style={{ fontFamily: 'monospace', fontSize: '0.8rem', resize: 'none' }}
            value={pgnInput}
            onChange={(e) => setPgnInput(e.target.value)}
          />
          <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={loadPgn}>Cargar PGN</button>
        </div>
      )}

      {activeTab === 'settings' && <SettingsPanel />}

      <section className="card animate-fade-in" style={{ padding: '0.75rem' }}>
        <ChessBoard fen={currentFen} onMove={onMove} />
        <div className="nav-controls">
          <button className="nav-btn"><ChevronsLeft size={20} /></button>
          <button className="nav-btn"><ChevronLeft size={20} /></button>
          <button className="nav-btn" onClick={() => setGame(new Chess())}><Play size={20} /></button>
          <button className="nav-btn"><ChevronRight size={20} /></button>
          <button className="nav-btn"><ChevronsRight size={20} /></button>
        </div>
      </section>

      <section className="card analysis-card animate-fade-in">
        <div className="section-title">
          <BrainCircuit size={20} className="text-blue-400" />
          Análisis del GM
        </div>
        
        {isAnalyzing ? (
          <div>
            <div style={{ height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${progress}%`, height: '100%', background: 'var(--gradient)', transition: 'width 0.3s' }} />
            </div>
          </div>
        ) : (
          <p>{commentary[currentFen] || "Toca 'Generar Comentarios' para comenzar."}</p>
        )}
        
        {!isAnalyzing && (
          <button className="btn btn-primary" onClick={startAnalysis} style={{ marginTop: '1.25rem' }}>
            <Zap size={18} /> Generar Comentarios
          </button>
        )}
      </section>

      <div style={{ textAlign: 'center', opacity: 0.5, fontSize: '0.75rem', marginTop: '2rem' }}>
        GM Comentarista Mobile · 2026
      </div>
    </>
  );
}
