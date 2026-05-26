import { useState } from 'react';

const Portfolio = ({ wallet, prices, setShowDepositModal, isAdmin, systemStatus }) => {
  const isLive = systemStatus?.binance_connected;
  const showDeposit = !isAdmin && !isLive;
  const [activeTab, setActiveTab] = useState('SPOT');

  const filteredWallet = wallet.filter(w => (w.wallet_type || 'SPOT') === activeTab);

  return (
    <div className="glass-panel" style={{ gridColumn: 'span 3' }}>
      <div className="flex-between" style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <h3 style={{ color: 'var(--text-muted)', margin: 0 }}>Mój Portfel</h3>
          <div style={{ display: 'flex', gap: '8px', background: 'var(--bg-card)', padding: '4px', borderRadius: '8px' }}>
            <button 
              className={`btn ${activeTab === 'SPOT' ? 'btn-success' : ''}`} 
              onClick={() => setActiveTab('SPOT')}
              style={{ padding: '4px 12px', fontSize: '13px' }}
            >
              SPOT
            </button>
            <button 
              className={`btn ${activeTab === 'FUTURES' ? 'btn-success' : ''}`} 
              onClick={() => setActiveTab('FUTURES')}
              style={{ padding: '4px 12px', fontSize: '13px' }}
            >
              FUTURES
            </button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {showDeposit && (
            <button className="btn btn-success" onClick={() => setShowDepositModal(true)}>+ Wpłać USDT</button>
          )}
        </div>
      </div>
      
      {filteredWallet.length === 0 ? (
        <p className="text-muted">
          {isAdmin 
            ? 'Konto administratora — brak funkcji portfela inwestycyjnego.'
            : isLive
              ? `Brak aktywów na koncie Binance (${activeTab}).`
              : `Brak aktywów w portfelu ${activeTab}. Skorzystaj z opcji "Wpłać USDT", aby zasilić konto symulacyjne.`}
        </p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Aktywo</th>
              <th>Dostępne</th>
              <th>Zablokowane (Zlecenia)</th>
              <th>Wartość (USD)</th>
            </tr>
          </thead>
          <tbody>
            {filteredWallet.map(w => (
              <tr key={w.asset_symbol}>
                <td style={{ fontWeight: 600 }}>{w.asset_symbol}</td>
                <td>{w.balance.toFixed(w.asset_symbol === 'USDT' ? 2 : 5)}</td>
                <td>{w.locked_balance.toFixed(w.asset_symbol === 'USDT' ? 2 : 5)}</td>
                <td>
                  {w.asset_symbol === 'USDT' 
                    ? `$${(w.balance + w.locked_balance).toFixed(2)}` 
                    : `$${((w.balance + w.locked_balance) * (prices[`${w.asset_symbol}USDT`] || 0)).toFixed(2)}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default Portfolio;
