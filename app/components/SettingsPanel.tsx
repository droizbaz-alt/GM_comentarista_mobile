'use client';

import React, { useState, useEffect } from 'react';
import { Settings, Key, Zap, Shield, Trash2, Cpu } from 'lucide-react';

export default function SettingsPanel() {
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [quality, setQuality] = useState('Media');

  useEffect(() => {
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey) setApiKey(savedKey);
    const savedQuality = localStorage.getItem('analysis_quality');
    if (savedQuality) setQuality(savedQuality);
  }, []);

  const saveKey = (val: string) => {
    setApiKey(val);
    localStorage.setItem('gemini_api_key', val);
  };

  const saveQuality = (val: string) => {
    setQuality(val);
    localStorage.setItem('analysis_quality', val);
  };

  const clearCache = () => {
    if (confirm('¿Deseas borrar el historial de análisis local?')) {
      localStorage.removeItem('gm_history');
      window.location.reload();
    }
  };

  return (
    <div className="card animate-fade-in">
      <div className="section-title">
        <Settings size={20} className="text-blue-400" />
        Configuración
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Gemini API Key */}
        <div>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem', display: 'block' }}>
            🔑 API Key de Gemini
          </label>
          <div style={{ position: 'relative' }}>
            <input
              type={showKey ? 'text' : 'password'}
              className="input"
              placeholder="Pega aquí tu clave de AI Studio"
              value={apiKey}
              onChange={(e) => saveKey(e.target.value)}
            />
            <button
              onClick={() => setShowKey(!showKey)}
              style={{
                position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer'
              }}
            >
              {showKey ? 'Ocultar' : 'Ver'}
            </button>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
            Tus datos se guardan solo en este dispositivo.
          </p>
        </div>

        {/* Quality Profile */}
        <div>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem', display: 'block' }}>
            🏆 Calidad del Análisis
          </label>
          <div className="tabs">
            {['Básica', 'Media', 'Alta'].map((q) => (
              <button
                key={q}
                className={`tab ${quality === q ? 'active' : ''}`}
                onClick={() => saveQuality(q)}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <button className="btn btn-secondary" onClick={clearCache} style={{ marginTop: '0.5rem', color: '#ef4444' }}>
          <Trash2 size={18} />
          Borrar Historial Offline
        </button>
      </div>
    </div>
  );
}
