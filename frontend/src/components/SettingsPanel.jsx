import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const SettingsPanel = ({ hasBinanceKeys, setHasBinanceKeys }) => {
  const [apiKey, setApiKey] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [showKeys, setShowKeys] = useState(false);

  const handleSaveKeys = async (e) => {
    e.preventDefault();
    if (!apiKey.trim() || !secretKey.trim()) {
      setMessage('Oba klucze są wymagane.');
      return;
    }
    setSaving(true);
    setMessage('');
    try {
      const res = await axios.put(`${API_URL}/auth/binance-keys`, {
        binance_api_key: apiKey,
        binance_secret_key: secretKey
      });
      setMessage(res.data.message);
      setHasBinanceKeys(true);
      setApiKey('');
      setSecretKey('');
      setShowKeys(false);
    } catch (err) {
      setMessage('Błąd: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteKeys = async () => {
    if (!window.confirm('Czy na pewno chcesz usunąć klucze Binance?')) return;
    try {
      const res = await axios.delete(`${API_URL}/auth/binance-keys`);
      setMessage(res.data.message);
      setHasBinanceKeys(false);
    } catch (err) {
      setMessage('Błąd: ' + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="glass-panel">
      <h3 style={{ color: 'var(--text-muted)', marginBottom: '16px' }}>
        ⚙️ Ustawienia – Klucze Binance API
      </h3>

      <div style={{ 
        padding: '12px', 
        background: 'rgba(255,255,255,0.03)', 
        borderRadius: '8px', 
        marginBottom: '16px',
        fontSize: '13px',
        color: 'var(--text-muted)'
      }}>
        <p style={{ margin: '0 0 8px 0' }}>
          <strong style={{ color: 'var(--accent)' }}>ℹ️ Info:</strong> Podaj własne klucze API z
          {' '}<a href="https://demo.binance.com" target="_blank" rel="noopener" style={{ color: 'var(--accent)' }}>
            demo.binance.com
          </a>{' '}
          aby handlować na swoim koncie demo. Bez kluczy transakcje będą realizowane lokalnie (symulacja).
        </p>
        <p style={{ margin: 0, fontSize: '11px' }}>
          🔒 Klucze są przechowywane bezpiecznie w bazie danych i używane wyłącznie do realizacji Twoich zleceń.
        </p>
      </div>

      {/* Status */}
      <div className="flex-between" style={{ marginBottom: '12px' }}>
        <span>Status kluczy:</span>
        <span style={{ 
          color: hasBinanceKeys ? 'var(--success)' : 'var(--text-muted)',
          fontWeight: 600 
        }}>
          {hasBinanceKeys ? '✅ Skonfigurowane' : '❌ Brak kluczy'}
        </span>
      </div>

      {/* Form */}
      {!showKeys && !hasBinanceKeys && (
        <button 
          className="btn btn-primary" 
          style={{ width: '100%' }}
          onClick={() => setShowKeys(true)}
        >
          Dodaj klucze Binance
        </button>
      )}

      {showKeys && (
        <form onSubmit={handleSaveKeys} className="flex-column" style={{ gap: '8px' }}>
          <input 
            type="text" 
            placeholder="API Key" 
            className="input-field" 
            value={apiKey} 
            onChange={e => setApiKey(e.target.value)}
            style={{ fontFamily: 'monospace', fontSize: '12px' }}
            required 
          />
          <input 
            type="password" 
            placeholder="Secret Key" 
            className="input-field" 
            value={secretKey} 
            onChange={e => setSecretKey(e.target.value)}
            style={{ fontFamily: 'monospace', fontSize: '12px' }}
            required 
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              type="submit" 
              className="btn btn-success" 
              style={{ flex: 1 }}
              disabled={saving}
            >
              {saving ? 'Zapisywanie...' : 'Zapisz klucze'}
            </button>
            <button 
              type="button" 
              className="btn" 
              onClick={() => { setShowKeys(false); setApiKey(''); setSecretKey(''); }}
            >
              Anuluj
            </button>
          </div>
        </form>
      )}

      {hasBinanceKeys && !showKeys && (
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            className="btn btn-primary" 
            style={{ flex: 1 }}
            onClick={() => setShowKeys(true)}
          >
            Zmień klucze
          </button>
          <button 
            className="btn btn-danger" 
            onClick={handleDeleteKeys}
          >
            Usuń klucze
          </button>
        </div>
      )}

      {message && (
        <div style={{ 
          marginTop: '12px', 
          padding: '8px', 
          borderRadius: '6px',
          background: message.startsWith('Błąd') ? 'rgba(255,50,50,0.1)' : 'rgba(0,212,170,0.1)',
          color: message.startsWith('Błąd') ? 'var(--danger)' : 'var(--success)',
          fontSize: '13px'
        }}>
          {message}
        </div>
      )}
    </div>
  );
};

export default SettingsPanel;
