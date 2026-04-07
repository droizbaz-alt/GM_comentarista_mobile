'use client';

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';

const GameContainer = dynamic(() => import('./components/GameContainer'), { 
  ssr: false,
  loading: () => (
    <div style={{ 
      background: '#0f172a', 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      color: 'white',
      fontFamily: 'sans-serif'
    }}>
      <div style={{ textAlign: 'center' }}>
        <h2 style={{ marginBottom: '1rem', fontWeight: 800 }}>♟️ GM Móvil</h2>
        <p style={{ opacity: 0.6 }}>Iniciando tablero...</p>
      </div>
    </div>
  )
});

export default function Home() {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return <GameContainer />;
}
