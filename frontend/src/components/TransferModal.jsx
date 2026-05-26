import { useState } from 'react';

const TransferModal = ({ showTransferModal, setShowTransferModal, handleTransfer, wallet }) => {
  const [asset, setAsset] = useState('USDT');
  const [amount, setAmount] = useState('');
  const [direction, setDirection] = useState('SPOT_TO_FUTURES'); // SPOT_TO_FUTURES or FUTURES_TO_SPOT

  if (!showTransferModal) return null;

  const fromType = direction === 'SPOT_TO_FUTURES' ? 'SPOT' : 'FUTURES';
  const toType = direction === 'SPOT_TO_FUTURES' ? 'FUTURES' : 'SPOT';

  const available = wallet.find(w => w.asset_symbol === asset && (w.wallet_type || 'SPOT') === fromType)?.balance || 0;

  const onSubmit = (e) => {
    e.preventDefault();
    handleTransfer(asset, parseFloat(amount), fromType, toType);
  };

  return (
    <div style={{ 
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
      background: 'rgba(0,0,0,0.7)', display: 'flex', 
      justifyContent: 'center', alignItems: 'center', zIndex: 1000 
    }}>
      <div className="glass-panel animate-fade-in" style={{ width: '400px' }}>
        <div className="flex-between" style={{ marginBottom: '16px' }}>
          <h2 className="text-gradient" style={{ margin: 0 }}>Transfer Środków</h2>
          <button 
            type="button" 
            className="btn" 
            style={{ padding: '4px 8px', background: 'var(--danger)', color: 'white', border: 'none', borderRadius: '4px' }}
            onClick={() => setShowTransferModal(false)}
          >
            ✕
          </button>
        </div>

        <form onSubmit={onSubmit} className="flex-column">
          <div className="flex-between" style={{ marginBottom: '16px', background: 'var(--bg-card)', borderRadius: '8px', padding: '4px' }}>
            <button 
              type="button" 
              className={`btn ${direction === 'SPOT_TO_FUTURES' ? 'btn-success' : ''}`} 
              style={{ flex: 1, padding: '8px' }} 
              onClick={() => setDirection('SPOT_TO_FUTURES')}
            >
              Spot ➔ Futures
            </button>
            <button 
              type="button" 
              className={`btn ${direction === 'FUTURES_TO_SPOT' ? 'btn-success' : ''}`} 
              style={{ flex: 1, padding: '8px' }} 
              onClick={() => setDirection('FUTURES_TO_SPOT')}
            >
              Futures ➔ Spot
            </button>
          </div>

          <div className="input-group">
            <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Aktywo</label>
            <select 
              className="input-field" 
              value={asset} 
              onChange={e => setAsset(e.target.value)}
            >
              <option value="USDT">USDT</option>
              <option value="BTC">BTC</option>
              <option value="ETH">ETH</option>
              <option value="BNB">BNB</option>
            </select>
          </div>

          <div className="input-group" style={{ marginTop: '12px' }}>
            <div className="flex-between" style={{ marginBottom: '8px' }}>
              <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Ilość</label>
              <span style={{ fontSize: '12px', color: 'var(--accent)' }}>Dostępne: {available.toFixed(2)} {asset}</span>
            </div>
            <div style={{ position: 'relative' }}>
              <input 
                type="number" 
                step="any" 
                className="input-field" 
                placeholder="Wpisz kwotę" 
                value={amount} 
                onChange={e => setAmount(e.target.value)} 
                required 
                max={available}
              />
              <button 
                type="button" 
                className="btn" 
                style={{ position: 'absolute', right: '5px', top: '5px', padding: '5px 10px', fontSize: '11px', height: '30px' }} 
                onClick={() => setAmount(available.toString())}
              >
                MAX
              </button>
            </div>
          </div>

          <button type="submit" className="btn btn-success" style={{ marginTop: '16px', width: '100%', height: '40px' }}>
            Potwierdź Transfer
          </button>
        </form>
      </div>
    </div>
  );
};

export default TransferModal;
