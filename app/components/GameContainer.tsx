'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import SettingsPanel from './SettingsPanel';
import { Chess } from 'chess.js';
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
  Loader2,
  Trophy,
  Activity
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
  
  // LIVE Evaluation
  const [liveEval, setLiveEval] = useState<any>(null);
  const [liveTb, setLiveTb] = useState<any>(null);

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
    // @ts-ignore
    window.GM_VERSION = '1.0.5';
  }, []);

  const updatePositionEval = async (fen: string) => {
    try {
        const res = await fetch('/api/analyze/position', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fen }),
            signal: AbortSignal.timeout(3000) // Timeout de 3s para evitar bloqueos
        });
        if (res.ok) {
            const data = await res.json();
            setLiveEval(data.eval);
            setLiveTb(data.tb);
        }
    } catch(e) {
        // Silencio total en errores de red/timeout para el análisis en vivo
        console.log("Live eval skip:", e);
    }
  };

  const updateView = (tempGame: Chess, cursor: number) => {
    const fen = tempGame.fen();
    setCurrentFen(fen);
    setMoveCursor(cursor);
    setGame(tempGame);
    updatePositionEval(fen);
  };

  const jumpTo = (index: number) => {
    const n = new Chess();
    for (let i = 0; i < index; i++) {
        n.move(masterHistory[i]);
    }
    updateView(n, index);
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

  // Navigation UI
  const handleFirst = () => jumpTo(0);
  const handlePrev = () => jumpTo(Math.max(0, moveCursor - 1));
  const handleNext = () => jumpTo(Math.min(masterHistory.length, moveCursor + 1));
  const handleLast = () => jumpTo(masterHistory.length);

  const fetchLichess = async () => {
    if (!lichessQuery) return alert("Introduce un usuario");
    setIsLoading(true);
    try {
      const res = await fetch('/api/lichess/user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: lichessQuery })
      });
      const data = await res.json();
      if (data.games) setRemoteGames(data.games);
      else alert(data.error || "Error al buscar usuario");
    } catch (e) {
      alert("Error de red");
    }
    setIsLoading(false);
  };

  const startAnalysis = async () => {
    if (!game) return;
    setIsAnalyzing(true);
    setProgress(0);
    
    // Generar metadatos REALES
    const fullHistory = new Chess();
    const metadata = [];
    const critMoments = [];
    
    for (let i = 0; i < masterHistory.length; i++) {
        setProgress(Math.round((i / masterHistory.length) * 40));
        const moveSan = masterHistory[i];
        const res = await fetch('/api/analyze/position', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fen: fullHistory.fen() })
        });
        const evalData = await res.json();
        
        fullHistory.move(moveSan);
        
        metadata.push({
            m: Math.floor(i / 2) + 1,
            t: i % 2 === 0 ? 'Bl' : 'Ne',
            san: moveSan,
            eval: (evalData.eval?.cp || (evalData.eval?.mate * 1000) || 0) / 100,
            loss: 0,
            rank: 1,
            fen: fullHistory.fen(),
            tb: evalData.tb,
            cap: false, // Opcional: Refinar detección de captura
            estrp: false
        });
        
        // Detección básica de momento crítico (> 1.5 de diferencia)
        if (i > 0 && Math.abs(metadata[i].eval - (metadata[i-1]?.eval || 0)) > 1.5) {
            critMoments.push(i);
        }
    }

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
          critical_moments: critMoments,
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
      alert("Error de conexión");
    }
    
    setProgress(100);
    setIsAnalyzing(false);
    setActiveTab('analysis');
  };

  const getEvalText = () => {
    if (!liveEval) return "Evaluando...";
    if (liveEval.mate !== undefined && liveEval.mate !== null) return `#${liveEval.mate}`;
    const val = (liveEval.cp / 100).toFixed(1);
    return val > 0 ? `+${val}` : val;
  };

  if (!mounted) return null;

  return (
    <>
      <header className="header animate-fade-in">
        <h1>♟️ GM Móvil <span className="badge">v1.0.5</span></h1>
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
                <input className="input" placeholder="Usuario de Lichess..." value={lichessQuery} onChange={(e) => setLichessQuery(e.target.value)} />
                <button className="btn btn-secondary" style={{ width: 'auto' }} onClick={fetchLichess} disabled={isLoading}>
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : <Search size={18} />}
                </button>
              </div>
              {remoteGames.length > 0 && (
                <div style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid var(--border)', borderRadius: '8px' }}>
                  {remoteGames.map(g => (
                    <div key={g.id} className="nav-btn" style={{ width: '100%', height: 'auto', padding: '8px', fontSize: '0.7rem', textAlign: 'left', justifyContent: 'flex-start', borderRadius: 0, borderBottom: '1px solid var(--border)' }} onClick={() => loadPgnText(g.pgn || g.label)}>
                      {g.label}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'settings' && <SettingsPanel />}

      <section className="card animate-fade-in" style={{ padding: '0.75rem', position: 'relative' }}>
        {/* Evaluación Flotante */}
        <div style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'rgba(0,0,0,0.7)', padding: '4px 10px', borderRadius: '12px', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', gap: '6px', zIndex: 10 }}>
            <Activity size={14} className="text-blue-400" />
            <span style={{ fontSize: '0.75rem', fontWeight: 'bold' }}>{getEvalText()}</span>
            {liveTb && <span style={{ fontSize: '0.65rem', paddingLeft: '4px', borderLeft: '1px solid var(--border)' }}>TB: {liveTb.category || '...'}</span>}
        </div>

        <ChessBoard fen={currentFen} onMove={onMove} />
        
        {/* Lista de jugadas PGN */}
        <div className="pgn-scroll" style={{ height: '80px', background: 'rgba(0,0,0,0.15)', borderRadius: '8px', margin: '10px 0', padding: '8px', overflowY: 'auto', display: 'flex', flexWrap: 'wrap', gap: '4px', alignContent: 'flex-start' }}>
            {masterHistory.length === 0 && <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Mueve una pieza para empezar...</p>}
            {masterHistory.map((mv, i) => {
                const moveNum = Math.floor(i / 2) + 1;
                const isWhite = i % 2 === 0;
                return (
                    <span 
                        key={i} 
                        onClick={() => jumpTo(i + 1)}
                        style={{ 
                            fontSize: '0.8rem', 
                            cursor: 'pointer', 
                            padding: '2px 4px', 
                            borderRadius: '4px',
                            background: moveCursor === i + 1 ? 'var(--accent-blue)' : 'transparent',
                            color: moveCursor === i + 1 ? 'white' : 'inherit'
                        }}
                    >
                        {isWhite && <span style={{ color: 'var(--text-muted)', marginRight: '2px' }}>{moveNum}.</span>}
                        {mv}
                    </span>
                );
            })}
        </div>

        <div className="nav-controls">
          <button className="nav-btn" onClick={handleFirst}><ChevronsLeft size={20} /></button>
          <button className="nav-btn" onClick={handlePrev}><ChevronLeft size={20} /></button>
          <button className="nav-btn" onClick={() => { setMasterHistory([]); updateView(new Chess(), 0); }}><Play size={20} /></button>
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
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '4px' }}>
                <span>Preparando metadatos reales...</span>
                <span>{progress}%</span>
              </div>
              <div style={{ height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${progress}%`, height: '100%', background: 'var(--gradient)', transition: 'width 0.3s' }} />
              </div>
            </div>
          ) : (
            <p style={{ fontSize: '0.9rem' }}>{commentary[currentFen] || "Toca 'Generar Comentarios' para obtener la visión del GM basada en Stockfish 16.1."}</p>
          )}
          
          {!isAnalyzing && (
            <button className="btn btn-primary" onClick={startAnalysis} style={{ marginTop: '1.25rem' }}>
              <Zap size={18} /> Generar Comentarios
            </button>
          )}
        </section>
      )}

      <div style={{ textAlign: 'center', opacity: 0.3, fontSize: '0.7rem', marginTop: '1rem', paddingBottom: '2rem' }}>
        GM Móvil · v1.0.3 · Chess engine by Lichess
      </div>

      <style jsx>{`
        .badge {
            font-size: 0.6rem;
            padding: 2px 6px;
            background: var(--accent-blue);
            border-radius: 12px;
            vertical-align: middle;
            margin-left: 5px;
            opacity: 0.8;
        }
        .pgn-scroll::-webkit-scrollbar { width: 4px; }
        .pgn-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
      `}</style>
    </>
  );
}
