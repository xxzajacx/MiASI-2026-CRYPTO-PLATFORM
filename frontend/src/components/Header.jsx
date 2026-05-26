const Header = ({ systemStatus, handleLogout, setShowUserPanel, isAdmin, setShowAdminPanel }) => {
  return (
    <header className="flex-between glass-panel" style={{ marginBottom: '24px', padding: '16px 24px' }}>
      <div>
        <h1 className="text-gradient" style={{ fontSize: '24px' }}>Giełda Premium</h1>
      </div>
      <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        <div style={{ textAlign: 'right', marginRight: '16px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Status Systemu</div>
          <div style={{ 
            fontSize: '14px', 
            color: systemStatus?.binance_connected ? 'var(--success)' : 'var(--accent)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            justifyContent: 'flex-end'
          }}>
            {systemStatus?.binance_connected && (
              <span style={{ 
                display: 'inline-block',
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                backgroundColor: 'var(--success)',
                boxShadow: '0 0 8px var(--success)'
              }}></span>
            )}
            {systemStatus?.binance_connected ? 'LIVE' : 'SYMULACJA'}
          </div>
        </div>
        
        {isAdmin && (
          <button className="btn btn-primary" style={{ background: 'var(--accent)' }} onClick={() => setShowAdminPanel(true)}>
            Zarządzanie użytkownikami
          </button>
        )}
        
        <button className="btn btn-primary" onClick={() => setShowUserPanel(true)}>
          Profil Użytkownika
        </button>
        <button className="btn" onClick={handleLogout}>Wyloguj</button>
      </div>
    </header>
  );
};

export default Header;
