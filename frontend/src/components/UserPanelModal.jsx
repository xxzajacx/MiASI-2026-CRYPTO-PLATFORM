import { useState, useEffect } from 'react';
import axios from 'axios';
import SettingsPanel from './SettingsPanel';

const API_URL = 'http://localhost:8000/api';

const UserPanelModal = ({ showUserPanel, setShowUserPanel, hasBinanceKeys, setHasBinanceKeys }) => {
  const [userInfo, setUserInfo] = useState(null);

  useEffect(() => {
    if (showUserPanel) {
      axios.get(`${API_URL}/auth/me`)
        .then(res => setUserInfo(res.data))
        .catch(err => console.error("Failed to fetch user info", err));
    }
  }, [showUserPanel]);

  if (!showUserPanel) return null;

  return (
    <div style={{ 
      position: 'fixed', 
      top: 0, left: 0, right: 0, bottom: 0, 
      background: 'rgba(0,0,0,0.7)', 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      zIndex: 1000 
    }}>
      <div className="glass-panel animate-fade-in" style={{ width: '600px', maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="flex-between" style={{ marginBottom: '24px' }}>
          <h2 className="text-gradient" style={{ margin: 0 }}>Profil Użytkownika</h2>
          <button className="btn" onClick={() => setShowUserPanel(false)} style={{ padding: '4px 12px' }}>
            ✕
          </button>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ color: 'var(--text-muted)', marginBottom: '16px' }}>👤 Informacje o koncie</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Nazwa użytkownika</div>
              <div style={{ fontSize: '16px', fontWeight: '500' }}>{userInfo?.username || 'Ładowanie...'}</div>
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Email</div>
              <div style={{ fontSize: '16px', fontWeight: '500' }}>{userInfo?.email || 'Brak danych'}</div>
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Imię</div>
              <div style={{ fontSize: '16px', fontWeight: '500' }}>{userInfo?.first_name || 'Brak danych'}</div>
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Nazwisko</div>
              <div style={{ fontSize: '16px', fontWeight: '500' }}>{userInfo?.last_name || 'Brak danych'}</div>
            </div>
          </div>
        </div>

        <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', margin: '24px 0' }}></div>

        <SettingsPanel 
          hasBinanceKeys={hasBinanceKeys} 
          setHasBinanceKeys={setHasBinanceKeys} 
        />

        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
          <button 
            type="button" 
            className="btn" 
            onClick={() => setShowUserPanel(false)}
          >
            Zamknij
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserPanelModal;
