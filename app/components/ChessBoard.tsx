'use client';

import React, { useEffect, useRef } from 'react';
import { Chessground } from 'chessground';
import { Chess } from 'chess.js';
import 'chessground/assets/chessground.base.css';
import 'chessground/assets/chessground.brown.css';
import 'chessground/assets/chessground.cburnett.css';

interface BoardProps {
  fen: string;
  onMove?: (orig: any, dest: any) => void;
  orientation?: 'white' | 'black';
  lastMove?: any;
}

export default function ChessBoard({ fen, onMove, orientation = 'white', lastMove }: BoardProps) {
  const boardRef = useRef<HTMLDivElement>(null);
  const cgInstance = useRef<any>(null);
  const lastFenRef = useRef(fen);

  useEffect(() => {
    console.log("🧩 ChessBoard v1.0.2 Mounted/Updated");
    if (boardRef.current && !cgInstance.current) {
      const chess = new Chess(fen);
      cgInstance.current = Chessground(boardRef.current, {
        fen: fen,
        orientation: orientation,
        movable: {
          color: 'both',
          free: false,
          dests: getMapDests(chess) as any,
        },
        events: {
          after: (orig: any, dest: any) => {
            console.log("♟️ Move detected:", orig, dest);
            if (onMove) onMove(orig, dest);
          }
        },
        animation: { enabled: true, duration: 250 },
        drawable: { enabled: true },
      });
    } else if (cgInstance.current) {
      if (lastFenRef.current !== fen) {
        console.log("🔄 Adjusting board to FEN:", fen);
        const chess = new Chess(fen);
        cgInstance.current.set({ 
          fen: fen, 
          orientation: orientation,
          movable: { dests: getMapDests(chess) as any } 
        });
        lastFenRef.current = fen;
      }
      if (lastMove) cgInstance.current.set({ lastMove: [lastMove.from, lastMove.to] });
    }
  }, [fen, orientation, lastMove]);

  function getMapDests(chess: Chess) {
    // Usar objeto plano para máxima compatibilidad y evitar .get() errors
    const dests: Record<string, string[]> = {};
    chess.moves({ verbose: true }).forEach(m => {
      if (!dests[m.from]) dests[m.from] = [];
      dests[m.from].push(m.to);
    });
    
    // Convertir a Map solo para la librería Chessground si es necesario, 
    // pero Chessground también acepta Map nativo de JS.
    const destsMap = new Map();
    for (const key in dests) {
        destsMap.set(key, dests[key]);
    }
    return destsMap;
  }

  return (
    <div className="board-wrapper">
      <div 
        ref={boardRef} 
        style={{ width: '100%', height: '100%' }} 
        className="merida"
      />
    </div>
  );
}
