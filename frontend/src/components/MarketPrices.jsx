const MarketPrices = ({ prices, tradeSymbol, setTradeSymbol, setShowTradeModal }) => {
  const symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];
  
  return (
    <div className="glass-panel">
      <h3 style={{ marginBottom: '16px', color: 'var(--text-muted)' }}>Rynek (Live)</h3>
      <div className="flex-column" style={{ gap: '12px' }}>
        {symbols.map(sym => (
          <div 
            key={sym} 
            className="flex-between" 
            style={{ 
              padding: '8px', 
              background: 'rgba(255,255,255,0.03)', 
              borderRadius: '8px', 
              cursor: 'pointer', 
              border: tradeSymbol === sym ? '1px solid var(--primary)' : '1px solid transparent' 
            }} 
            onClick={() => setTradeSymbol(sym)}
          >
            <span style={{ fontWeight: '600' }}>{sym.replace('USDT', '/USDT')}</span>
            <span className="text-success" style={{ fontWeight: '700' }}>
              ${prices[sym]?.toFixed(2) || '---'}
            </span>
          </div>
        ))}
      </div>
      <div style={{ marginTop: '24px' }}>
        <button 
          className="btn btn-primary" 
          style={{ width: '100%' }} 
          onClick={() => setShowTradeModal(true)}
        >
          🛒 Otwórz Pozycję
        </button>
      </div>
    </div>
  );
};

export default MarketPrices;
