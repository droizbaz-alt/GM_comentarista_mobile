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

  useEffect(() => {
    if (boardRef.current && !ground.current) {
      ground.current = Chessground(boardRef.current, {
        fen: fen,
        orientation: orientation,
        movable: {
          color: 'both',
          free: false,
          dests: getDests(new Chess(fen)),
          events: {
            after: (orig, dest) => onMove && onMove(orig, dest)
          }
        },
        animation: { enabled: true, duration: 200 },
        drawable: { enabled: true },
      });
    } else if (ground.current) {
      ground.current.set({ fen: fen, orientation: orientation });
      if (lastMove) ground.current.set({ lastMove: [lastMove.from, lastMove.to] });
    }
  }, [fen, orientation, lastMove]);

  function getDests(chess: Chess) {
    const dests = new Map();
    chess.moves({ verbose: true }).forEach(m => {
      dests.set(m.from, (dests.get(m.from) || []).concat(m.to));
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
