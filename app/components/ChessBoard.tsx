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
  const ground = useRef<any>(null);
  const lastFenRef = useRef(fen);

  useEffect(() => {
    if (boardRef.current && !ground.current) {
      const chess = new Chess(fen);
      ground.current = Chessground(boardRef.current, {
        fen: fen,
        orientation: orientation,
        movable: {
          color: 'both',
          free: false,
          dests: getMapDests(chess),
        },
        events: {
          after: (orig: any, dest: any) => onMove && onMove(orig, dest)
        },
        animation: { enabled: true, duration: 250 },
        drawable: { enabled: true },
      });
    } else if (ground.current) {
      // Solo actualizar si el FEN ha cambiado externamente (navegación)
      if (lastFenRef.current !== fen) {
        const chess = new Chess(fen);
        ground.current.set({ 
          fen: fen, 
          orientation: orientation,
          movable: { dests: getMapDests(chess) } 
        });
        lastFenRef.current = fen;
      }
      if (lastMove) ground.current.set({ lastMove: [lastMove.from, lastMove.to] });
    }
  }, [fen, orientation, lastMove]);

  function getMapDests(chess: Chess) {
    const dests = new Map();
    chess.moves({ verbose: true }).forEach(m => {
      const ms = dests.get(m.from) || [];
      ms.push(m.to);
      dests.set(m.from, ms);
    });
    return dests;
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
