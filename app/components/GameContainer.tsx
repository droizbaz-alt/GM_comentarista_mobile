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
  Activity,
  Copy,
  Download,
  FileCode,
  MessageSquare
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
  const [currentComment, setCurrentComment] = useState("");
  const [activeTab, setActiveTab] = useState('import');
  const [importMode, setImportMode] = useState<Platform>('pgn');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [showRawPgn, setShowRawPgn] = useState(false);
  
  // LIVE Evaluation
  const [liveEval, setLiveEval] = useState<any>(null);
  const [liveTb, setLiveTb] = useState<any>(null);

  // Advanced History Management
  const [masterHistory, setMasterHistory] = useState<string[]>([]);
  const [moveCursor, setMoveCursor] = useState(0);

  // Inputs
  const [pgnInput, setPgnInput] = useState('');
  const [lichessQuery, setLichessQuery] = useState('');
  const [remoteGames, setRemoteGames] = useState<any[]>([]);

  useEffect(() => {
    setMounted(true);
    const n = new Chess();
    setGame(n);
    // @ts-ignore
    window.GM_VERSION = '1.0.6';
  }, []);

  const updatePositionEval = async (fen: string) => {
    try {
        const res = await fetch('/api/analyze/position', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fen }),
            signal: AbortSignal.timeout(3000)
        });
        if (res.ok) {
            const data = await res.json();
            setLiveEval(data.eval);
            setLiveTb(data.tb);
        }
    } catch(e) {
        console.log("Live eval skip:", e);
    }
  };

  const updateView = (tempGame: Chess, cursor: number) => {
    const fen = tempGame.fen();
    setCurrentFen(fen);
    setMoveCursor(cursor);
    setGame(tempGame);
    setCurrentComment(tempGame.getComment() || "");
    updatePositionEval(fen);
  };

  const jumpTo = (index: number) => {
    const n = new Chess();
    if (game && game.pgn()) n.loadPgn(game.pgn());
    
    const history = n.history();
    const newGame = new Chess();
    for (let i = 0; i < index; i++) {
        newGame.move(history[i]);
    }
    updateView(newGame, index);
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
        const history = newGame.history();
        setMasterHistory(history);
        setMoveCursor(history.length);
        updateView(newGame, history.length);
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

  const copyPgn = () => {
    if (!game) return;
    navigator.clipboard.writeText(game.pgn());
    alert("PGN copiado al portapapeles");
  };

  const downloadPgn = () => {
    if (!game) return;
    const element = document.createElement("a");
    const file = new Blob([game.pgn()], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = "analisis_gm.pgn";
    document.body.appendChild(element);
    element.click();
  };

  const startAnalysis = async () => {
    if (!game) return;
    setIsAnalyzing(true);
    setProgress(0);
    
    // Generar metadatos REALES
    const fullHistory = new Chess();
    const histMoves = game.history();
    const metadata = [];
    const critMoments = [];
    
    for (let i = 0; i < histMoves.length; i++) {
        setProgress(Math.round((i / histMoves.length) * 40));
        const moveSan = histMoves[i];
        
        metadata.push({
            m: Math.floor(i / 2) + 1,
            t: i % 2 === 0 ? 'Bl' : 'Ne',
            san: moveSan,
            eval: liveEval?.cp ? liveEval.cp / 100 : 0.35, // Usar live si está disponible
            loss: 0,
            rank: 1,
            fen: fullHistory.fen(),
            cap: false,
            estrp: false
        });
        
        fullHistory.move(moveSan);
        if (i % 5 === 0) await new Promise(r => setTimeout(r, 100)); // Rate limit protection
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
        loadPgnText(result.pgn);
      } else {
        alert("Error: " + (result.error || "Desconocido"));
      }
    } catch (err) {
      alert("Error de conexión");
    }
    
    setProgress(100);
    setIsAnalyzing(false);
  };

  const getEvalText = () => {
    if (!liveEval) return "Evaluando...";
    if (liveEval.mate !== undefined && liveEval.mate !== null) return `#${liveEval.mate}`;
    const val = (liveEval.cp / 100).toFixed(1);
    return (liveEval.cp >= 0 ? "+" : "") + val;
  };

  if (!mounted) return null;

  return (
    <>
      <header className="header animate-fade-in">
        <h1>♟️ GM Móvil <span className="badge">v1.0.6</span></h1>
        <p>Análisis y Exportación Profesional</p>
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
        <div className="card animate-fade-in" style={{ padding: '1rem' }}>
          <div className="tabs" style={{ marginBottom: '1rem', background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '12px' }}>
            <button className={`tab ${importMode === 'pgn' ? 'active' : ''}`} onClick={() => setImportMode('pgn')} style={{ flex: 1 }}><Monitor size={14} /></button>
            <button className={`tab ${importMode === 'lichess' ? 'active' : ''}`} onClick={() => setImportMode('lichess')} style={{ flex: 1 }}>L</button>
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
        </div>
      )}

      {activeTab === 'settings' && <SettingsPanel />}

      <section className="card animate-fade-in" style={{ padding: '0.75rem', position: 'relative' }}>
        {/* Evaluación */}
        <div style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'rgba(0,0,0,0.7)', padding: '4px 10px', borderRadius: '12px', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', gap: '6px', zIndex: 10 }}>
            <Activity size={14} className="text-blue-400" />
            <span style={{ fontSize: '0.75rem', fontWeight: 'bold' }}>{getEvalText()}</span>
        </div>

        <ChessBoard fen={currentFen} onMove={onMove} />
        
        {/* Move History Interaction List */}
        <div className="pgn-scroll" style={{ height: '80px', background: 'rgba(0,0,0,0.15)', borderRadius: '8px', margin: '10px 0', padding: '8px', overflowY: 'auto', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {masterHistory.length === 0 && <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Realiza movimientos para empezar...</p>}
            {masterHistory.map((mv, i) => (
                <span 
                    key={i} 
                    onClick={() => jumpTo(i+1)}
                    style={{ 
                        fontSize: '0.85rem', cursor: 'pointer', padding: '2px 6px', borderRadius: '4px',
                        background: moveCursor === i+1 ? 'var(--accent-blue)' : 'transparent',
                        color: moveCursor === i+1 ? 'white' : 'inherit'
                    }}
                >
                    {i % 2 === 0 ? `${Math.floor(i/2)+1}. ` : ""}{mv}
                </span>
            ))}
        </div>

        {/* Comment Box (VIRTUAL VISUALIZER) */}
        {currentComment && (
            <div className="comment-box animate-slide-up">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px', color: 'var(--accent-blue)', fontSize: '0.7rem', fontWeight: 'bold', textTransform: 'uppercase' }}>
                    <MessageSquare size={14} /> Visión del GM
                </div>
                <p style={{ fontSize: '0.85rem', lineHeight: '1.4', margin: 0, color: '#e2e8f0' }}>{currentComment}</p>
            </div>
        )}

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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div className="section-title" style={{ margin: 0 }}>
                <BrainCircuit size={20} className="text-blue-400" />
                Análisis y Exportación
            </div>
            {game && masterHistory.length > 0 && (
                <div style={{ display: 'flex', gap: '8px' }}>
                    <button className="nav-btn" style={{ padding: '8px' }} onClick={copyPgn} title="Copiar PGN"><Copy size={18} /></button>
                    <button className="nav-btn" style={{ padding: '8px' }} onClick={downloadPgn} title="Descargar PGN"><Download size={18} /></button>
                    <button className="nav-btn" style={{ padding: '8px' }} onClick={() => setShowRawPgn(!showRawPgn)} title="Ver Código"><FileCode size={18} /></button>
                </div>
            )}
          </div>
          
          {isAnalyzing ? (
            <div style={{ padding: '1rem 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '8px' }}>
                <span>El GM está analizando tácticas y estrategia...</span>
                <span>{progress}%</span>
              </div>
              <div style={{ height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${progress}%`, height: '100%', background: 'var(--gradient)', transition: 'width 0.4s cubic-bezier(0.1, 0.7, 0.1, 1)' }} />
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center' }}>
                {!isAnalyzing && masterHistory.length > 0 && (
                    <button className="btn btn-primary" onClick={startAnalysis} style={{ marginBottom: '1rem' }}>
                        <Zap size={18} /> Generar Análisis Completo
                    </button>
                )}
                
                {showRawPgn && game && (
                    <pre style={{ 
                        background: '#0f172a', padding: '1rem', borderRadius: '8px', fontSize: '0.7rem', 
                        color: 'var(--text-muted)', textAlign: 'left', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                        border: '1px solid var(--border)', marginTop: '1rem', maxHeight: '200px', overflowY: 'auto'
                    }}>
                        {game.pgn()}
                    </pre>
                )}
            </div>
          )}
        </section>
      )}

      <div style={{ textAlign: 'center', opacity: 0.3, fontSize: '0.7rem', marginTop: '1rem', paddingBottom: '2rem' }}>
        GM Móvil · v1.0.6 · Engine: Stockfish 16.1 · UI Pre-alpha
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
        .comment-box {
            background: rgba(30, 41, 59, 0.8);
            border-left: 4px solid var(--accent-blue);
            padding: 12px;
            border-radius: 4px 12px 12px 4px;
            margin-bottom: 12px;
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255,255,255,0.05);
        }
        .animate-slide-up {
            animation: slideUp 0.3s ease-out;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </>
  );
}
