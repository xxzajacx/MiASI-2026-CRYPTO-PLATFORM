import { useState } from 'react';

const DepositModal = ({ showDepositModal, setShowDepositModal, depositAsset, setDepositAsset, depositAmount, setDepositAmount, handleDeposit }) => {
  if (!showDepositModal) return null;

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
      <div className="glass-panel animate-fade-in" style={{ width: '400px' }}>
        <h2 className="text-gradient" style={{ marginBottom: '16px' }}>Wpłać Środki</h2>
        <form onSubmit={handleDeposit} className="flex-column">
          <label style={{ fontSize: '14px', color: 'var(--text-muted)' }}>Aktywo</label>
          <select 
            className="input-field" 
            value={depositAsset} 
            onChange={e => setDepositAsset(e.target.value)}
          >
            <option value="USDT">USDT (Dolar)</option>
            <option value="BTC">BTC (Bitcoin)</option>
            <option value="ETH">ETH (Ethereum)</option>
            <option value="BNB">BNB (Binance Coin)</option>
          </select>
          
          <label style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '12px' }}>Ilość</label>
          <input 
            type="number" 
            step="any" 
            className="input-field" 
            placeholder="0.00" 
            value={depositAmount} 
            onChange={e => setDepositAmount(e.target.value)} 
            required 
          />
          
          <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
            <button type="submit" className="btn btn-success" style={{ flex: 1 }}>
              Wpłać
            </button>
            <button 
              type="button" 
              className="btn" 
              style={{ flex: 1 }} 
              onClick={() => setShowDepositModal(false)}
            >
              Anuluj
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DepositModal;
