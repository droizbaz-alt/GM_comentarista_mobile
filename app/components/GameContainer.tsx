'use client';

import React, { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import SettingsPanel from './SettingsPanel';
import { Chess, Move } from 'chess.js';
import { 
  Play, 
  ChevronLeft, 
  ChevronRight, 
  ChevronsLeft, 
  ChevronsRight, 
  Search,
  Upload,
  Monitor,
  Import,
  Cpu,
  BrainCircuit,
  Zap,
  Loader2
} from 'lucide-react';

const ChessBoard = dynamic(() => import('./ChessBoard'), { 
  ssr: false,
  loading: () => <div className="board-wrapper" style={{ background: '#1e293b', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <p style={{ color: 'var(--text-muted)' }}>Cargando tablero...</p>
  </div>
});

type Platform = 'pgn' | 'lichess' | 'chesscom' | 'file';

export default function GameContainer() {
  const [mounted, setMounted] = useState(false);
  const [game, setGame] = useState<Chess | null>(null);
  const [currentFen, setCurrentFen] = useState('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
  const [commentary, setCommentary] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState('import');
  const [importMode, setImportMode] = useState<Platform>('pgn');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  
  // Advanced History Management
  const [masterHistory, setMasterHistory] = useState<string[]>([]);
  const [moveCursor, setMoveCursor] = useState(0);

  // Inputs
  const [pgnInput, setPgnInput] = useState('');
  const [lichessQuery, setLichessQuery] = useState('');
  const [chesscomQuery, setChesscomQuery] = useState('');
  const [remoteGames, setRemoteGames] = useState<any[]>([]);

  useEffect(() => {
    setMounted(true);
    const n = new Chess();
    setGame(n);
  }, []);

  const updateView = (tempGame: Chess, cursor: number) => {
    setCurrentFen(tempGame.fen());
    setMoveCursor(cursor);
    setGame(tempGame);
  };

  const loadPgnText = (text: string) => {
    try {
      const newGame = new Chess();
      newGame.loadPgn(text);
      const history = newGame.history();
      setMasterHistory(history);
      setMoveCursor(history.length);
      updateView(newGame, history.length);
      setActiveTab('analysis');
      setRemoteGames([]);
    } catch (e) {
      alert("PGN inválido");
    }
  };

  const onMove = (orig: string, dest: string) => {
    if (!game) return;
    try {
      const newGame = new Chess();
      newGame.loadPgn(game.pgn());
      const move = newGame.move({ from: orig, to: dest, promotion: 'q' });
      if (move) {
        // Branching: Si moveCursor no está al final, cortamos la historia master
        const newHistory = [...masterHistory.slice(0, moveCursor), move.san];
        setMasterHistory(newHistory);
        setMoveCursor(newHistory.length);
        updateView(newGame, newHistory.length);
      }
    } catch (e) {
      console.error("Illegal move", e);
    }
  };

  // Navigation Logic
  const handleFirst = () => {
    const n = new Chess();
    setMoveCursor(0);
    setCurrentFen(n.fen());
    setGame(n);
  };

  const handlePrev = () => {
    if (moveCursor <= 0) return;
    const newCursor = moveCursor - 1;
    const n = new Chess();
    for (let i = 0; i < newCursor; i++) {
        n.move(masterHistory[i]);
    }
    updateView(n, newCursor);
  };

  const handleNext = () => {
    if (moveCursor >= masterHistory.length) return;
    const newCursor = moveCursor + 1;
    const n = new Chess();
    for (let i = 0; i < newCursor; i++) {
        n.move(masterHistory[i]);
    }
    updateView(n, newCursor);
  };

  const handleLast = () => {
    const newCursor = masterHistory.length;
    const n = new Chess();
    for (let i = 0; i < newCursor; i++) {
        n.move(masterHistory[i]);
    }
    updateView(n, newCursor);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      loadPgnText(content);
    };
    reader.readAsText(file);
  };

  const fetchLichess = async () => {
    if (!lichessQuery) return alert("Introduce un usuario");
    setIsLoading(true);
    try {
      console.log("Fetching Lichess user:", lichessQuery);
      const res = await fetch('/api/lichess/user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: lichessQuery })
      });
      if (res.status === 404) throw new Error("API not found (404)");
      const data = await res.json();
      if (data.games) setRemoteGames(data.games);
      else alert(data.error || "Error al buscar usuario");
    } catch (e) {
      alert("Error de red: " + e);
    }
    setIsLoading(false);
  };

  const fetchChessCom = async () => {
    if (!chesscomQuery) return alert("Introduce un usuario");
    setIsLoading(true);
    try {
      console.log("Fetching Chess.com user:", chesscomQuery);
      const res = await fetch('/api/chesscom/user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: chesscomQuery })
      });
      if (res.status === 404) throw new Error("API not found (404)");
      const data = await res.json();
      if (data.games) setRemoteGames(data.games);
      else alert(data.error || "Error al buscar usuario");
    } catch (e) {
      alert("Error de red: " + e);
    }
    setIsLoading(false);
  };

  const startAnalysis = async () => {
    if (!game) return;
    setIsAnalyzing(true);
    setProgress(0);
    
    const historyVerbose = game.history({ verbose: true });
    const metadata = historyVerbose.map((m, i) => ({
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
      setProgress(50);
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
        loadPgnText(result.pgn);
      } else {
        alert("Error: " + (result.error || "Desconocido"));
      }
    } catch (err) {
      alert("Error de conexión: " + err);
    }
    
    setProgress(100);
    setIsAnalyzing(false);
    setActiveTab('analysis');
  };

  if (!mounted) return null;

  return (
    <>
      <header className="header animate-fade-in">
        <h1>♟️ GM Móvil <span style={{ fontSize: '0.6rem', padding: '2px 6px', background: 'var(--accent-blue)', borderRadius: '12px', verticalAlign: 'middle', marginLeft: '5px', opacity: 0.8 }}>v1.0.1</span></h1>
        <p>Tu entrenador Gran Maestro personalizado</p>
      </header>

      <div className="tabs animate-fade-in" style={{ marginBottom: '0.5rem' }}>
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
        <div className="card animate-fade-in" style={{ padding: '1rem' }}>
          <div className="tabs" style={{ marginBottom: '1rem', background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '12px' }}>
            <button className={`tab ${importMode === 'pgn' ? 'active' : ''}`} onClick={() => setImportMode('pgn')} style={{ flex: 1 }}><Monitor size={14} /></button>
            <button className={`tab ${importMode === 'lichess' ? 'active' : ''}`} onClick={() => setImportMode('lichess')} style={{ flex: 1 }}>L</button>
            <button className={`tab ${importMode === 'chesscom' ? 'active' : ''}`} onClick={() => setImportMode('chesscom')} style={{ flex: 1 }}>C</button>
            <button className={`tab ${importMode === 'file' ? 'active' : ''}`} onClick={() => setImportMode('file')} style={{ flex: 1 }}><Upload size={14} /></button>
          </div>

          {importMode === 'pgn' && (
            <div className="animate-fade-in">
              <textarea 
                className="input" 
                placeholder="Pega aquí tu PGN..." 
                rows={4} 
                style={{ fontFamily: 'monospace', fontSize: '0.75rem', resize: 'none', marginBottom: '0.75rem' }}
                value={pgnInput}
                onChange={(e) => setPgnInput(e.target.value)}
              />
              <button className="btn btn-primary" onClick={() => loadPgnText(pgnInput)}>Cargar Texto</button>
            </div>
          )}

          {importMode === 'lichess' && (
            <div className="animate-fade-in">
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <input 
                  className="input" 
                  placeholder="Usuario de Lichess..." 
                  value={lichessQuery}
                  onChange={(e) => setLichessQuery(e.target.value)}
                />
                <button className="btn btn-secondary" style={{ width: 'auto' }} onClick={fetchLichess} disabled={isLoading}>
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : <Search size={18} />}
                </button>
              </div>
              {remoteGames.length > 0 && (
                <div style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid var(--border)', borderRadius: '8px' }}>
                  {remoteGames.map(g => (
                    <div key={g.id} className="nav-btn" style={{ width: '100%', height: 'auto', padding: '8px', fontSize: '0.7rem', textAlign: 'left', justifyContent: 'flex-start', borderRadius: 0, borderBottom: '1px solid var(--border)' }} onClick={() => loadPgnText(g.pgn || g.label)}>
                      {g.label || `${g.players?.white?.user?.name} vs ${g.players?.black?.user?.name}`}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {importMode === 'chesscom' && (
            <div className="animate-fade-in">
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <input 
                  className="input" 
                  placeholder="Usuario de Chess.com..." 
                  value={chesscomQuery}
                  onChange={(e) => setChesscomQuery(e.target.value)}
                />
                <button className="btn btn-secondary" style={{ width: 'auto' }} onClick={fetchChessCom} disabled={isLoading}>
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : <Search size={18} />}
                </button>
              </div>
              {remoteGames.length > 0 && (
                <div style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid var(--border)', borderRadius: '8px' }}>
                  {remoteGames.map(g => (
                    <div key={g.id} className="nav-btn" style={{ width: '100%', height: 'auto', padding: '8px', fontSize: '0.7rem', textAlign: 'left', justifyContent: 'flex-start', borderRadius: 0, borderBottom: '1px solid var(--border)' }} onClick={() => loadPgnText(g.pgn)}>
                      {g.players?.white?.user?.name} vs {g.players?.black?.user?.name} ({g.speed})
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {importMode === 'file' && (
            <div className="animate-fade-in" style={{ textAlign: 'center', padding: '1rem', border: '2px dashed var(--border)', borderRadius: '12px' }}>
              <input type="file" id="pgnFile" accept=".pgn" onChange={handleFileUpload} style={{ display: 'none' }} />
              <label htmlFor="pgnFile" style={{ cursor: 'pointer' }}>
                <Upload size={32} style={{ marginBottom: '0.5rem', color: 'var(--accent-blue)' }} />
                <p style={{ fontSize: '0.85rem' }}>Toca para subir un archivo .pgn</p>
              </label>
            </div>
          )}
        </div>
      )}

      {activeTab === 'settings' && <SettingsPanel />}

      {/* Main Board View */}
      <section className="card animate-fade-in" style={{ padding: '0.75rem' }}>
        <ChessBoard 
          fen={currentFen} 
          onMove={onMove} 
        />
        <div style={{ padding: '10px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-accent)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '75%' }}>
             [{moveCursor}/{masterHistory.length}] {game?.pgn() || "Nueva Partida"}
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
            Turno: {game?.turn() === 'w' ? 'Bl' : 'Ne'}
          </div>
        </div>
        <div className="nav-controls">
          <button className="nav-btn" onClick={handleFirst}><ChevronsLeft size={20} /></button>
          <button className="nav-btn" onClick={handlePrev}><ChevronLeft size={20} /></button>
          <button className="nav-btn" onClick={() => { const n = new Chess(); setMasterHistory([]); updateView(n, 0); setCommentary({}); }}><Play size={20} /></button>
          <button className="nav-btn" onClick={handleNext}><ChevronRight size={20} /></button>
          <button className="nav-btn" onClick={handleLast}><ChevronsRight size={20} /></button>
        </div>
      </section>

      {activeTab === 'analysis' && (
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
            <p style={{ fontSize: '0.9rem' }}>{commentary[currentFen] || "Toca 'Generar Comentarios' para obtener la visión del GM sobre esta posición."}</p>
          )}
          
          {!isAnalyzing && (
            <button className="btn btn-primary" onClick={startAnalysis} style={{ marginTop: '1.25rem' }}>
              <Zap size={18} /> Generar Comentarios
            </button>
          )}
        </section>
      )}

      <div style={{ textAlign: 'center', opacity: 0.3, fontSize: '0.7rem', marginTop: '1rem', paddingBottom: '2rem' }}>
        GM Comentarista Mobile · 2026
      </div>
    </>
  );
}
