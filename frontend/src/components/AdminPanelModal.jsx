import AdminPanel from './AdminPanel';

const AdminPanelModal = ({ showAdminPanel, setShowAdminPanel, token }) => {
  if (!showAdminPanel) return null;

  return (
    <div style={{ 
      position: 'fixed', 
      top: 0, left: 0, right: 0, bottom: 0, 
      background: 'rgba(0,0,0,0.85)', 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      zIndex: 1000 
    }}>
      <div className="glass-panel animate-fade-in" style={{ width: '900px', maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="flex-between" style={{ marginBottom: '24px' }}>
          <h2 className="text-gradient" style={{ margin: 0 }}>Panel Administratora</h2>
          <button className="btn" onClick={() => setShowAdminPanel(false)} style={{ padding: '4px 12px' }}>
            ✕
          </button>
        </div>
        
        <AdminPanel token={token} />
        
        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
          <button 
            type="button" 
            className="btn" 
            onClick={() => setShowAdminPanel(false)}
          >
            Zamknij
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminPanelModal;
