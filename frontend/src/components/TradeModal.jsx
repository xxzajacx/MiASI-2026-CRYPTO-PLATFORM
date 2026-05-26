import { useEffect } from 'react';

const TradeModal = ({ 
  showTradeModal, setShowTradeModal, 
  tradeSymbol, setTradeSymbol, 
  tradeSide, setTradeSide, 
  tradeAmount, setTradeAmount, 
  tradeAmountType, setTradeAmountType,
  tradeSL, setTradeSL, 
  tradeTP, setTradeTP, 
  tradeLeverage, setTradeLeverage,
  prices, minOrderSizes, handleMarketTrade,
  wallet, setErrorMsg
}) => {
  if (!showTradeModal) return null;

  const baseAsset = tradeSymbol.replace('USDT', '');
  
  const assetWallet = wallet.find(w => w.asset_symbol === baseAsset);
  const usdtWallet = wallet.find(w => w.asset_symbol === 'USDT');
  const currentPrice = prices[tradeSymbol] || 0;

  const spendAsset = tradeSide === 'BUY' ? 'USDT' : baseAsset;
  const spendBalance = tradeSide === 'BUY' ? (usdtWallet?.balance || 0) : (assetWallet?.balance || 0);
  const effectiveAmountType = tradeSide === 'BUY' ? 'usdt' : 'crypto';

  useEffect(() => {
    setTradeAmountType(effectiveAmountType);
  }, [effectiveAmountType, setTradeAmountType]);

  const handleMax = () => {
    setTradeAmount(spendBalance.toString());
  };

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
      <div className="glass-panel animate-fade-in" style={{ width: '450px' }}>
        <div className="flex-between" style={{ marginBottom: '16px' }}>
          <h2 className="text-gradient" style={{ margin: 0 }}>Otwórz Pozycję</h2>
          <button 
            type="button" 
            className="btn" 
            style={{ padding: '4px 8px', background: 'var(--danger)', color: 'white', border: 'none', borderRadius: '4px' }}
            onClick={() => setShowTradeModal(false)}
          >
            ✕
          </button>
        </div>
        
        <form onSubmit={handleMarketTrade} className="flex-column">
          {/* Symbol Selection */}
          <div className="input-group">
            <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Para handlowa</label>
            <select 
              className="input-field" 
              value={tradeSymbol} 
              onChange={e => setTradeSymbol(e.target.value)}
            >
              <option value="BTCUSDT">BTC/USDT</option>
              <option value="ETHUSDT">ETH/USDT</option>
              <option value="BNBUSDT">BNB/USDT</option>
            </select>
          </div>

          {/* Buy/Sell Toggle */}
          <div className="flex-between" style={{ margin: '16px 0' }}>
            <button 
              type="button" 
              className={`btn ${tradeSide === 'BUY' ? 'btn-success' : ''}`} 
              style={{ flex: 1, opacity: tradeSide === 'BUY' ? 1 : 0.5 }} 
              onClick={() => setTradeSide('BUY')}
            >
              KUP
            </button>
            <button 
              type="button" 
              className={`btn ${tradeSide === 'SELL' ? 'btn-danger' : ''}`} 
              style={{ flex: 1, opacity: tradeSide === 'SELL' ? 1 : 0.5 }} 
              onClick={() => setTradeSide('SELL')}
            >
              SPRZEDAJ
            </button>
          </div>

          {/* Amount */}
          <div className="input-group">
            <div className="flex-between" style={{ marginBottom: '8px' }}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  Ilość ({spendAsset})
                </label>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--accent)' }}>
                Dostępne: {spendBalance.toFixed(spendAsset === 'USDT' ? 2 : 5)} {spendAsset}
              </span>
            </div>
            <div style={{ position: 'relative' }}>
              <input 
                type="number" 
                step="any" 
                className="input-field" 
                placeholder={effectiveAmountType === 'crypto' ? "0.00000" : "0.00"} 
                value={tradeAmount} 
                onChange={e => setTradeAmount(e.target.value)} 
                required 
              />
              <button 
                type="button" 
                className="btn" 
                style={{ position: 'absolute', right: '5px', top: '5px', padding: '5px 10px', fontSize: '11px', height: '30px' }} 
                onClick={handleMax}
              >
                MAX
              </button>
            </div>
          </div>

          {/* Leverage */}
          <div className="input-group" style={{ marginTop: '12px' }}>
            <label style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>
              Dźwignia (Leverage)
            </label>
            <select 
              className="input-field" 
              value={tradeLeverage} 
              onChange={e => setTradeLeverage(e.target.value)}
            >
              {[1, 2, 5, 10, 20, 50, 100].map(lv => (
                <option key={lv} value={lv}>{lv}x</option>
              ))}
            </select>
          </div>

          {/* Stop Loss & Take Profit */}
          <div className="grid grid-cols-2" style={{ gap: '12px', marginTop: '12px' }}>
            <div className="input-group">
              <label style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>
                Take Profit ($)
              </label>
              <input 
                type="number" 
                step="any" 
                className="input-field" 
                placeholder="Cena" 
                value={tradeTP} 
                onChange={e => setTradeTP(e.target.value)} 
              />
            </div>
            <div className="input-group">
              <label style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>
                Stop Loss ($)
              </label>
              <input 
                type="number" 
                step="any" 
                className="input-field" 
                placeholder="Cena" 
                value={tradeSL} 
                onChange={e => setTradeSL(e.target.value)} 
              />
            </div>
          </div>

          {/* Cost Estimation & Limits */}
          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', marginTop: '16px', fontSize: '13px' }}>
            <div className="flex-between" style={{ marginBottom: '8px' }}>
              <span className="text-muted">Szacowany koszt (Margin):</span>
              <span style={{ fontWeight: 600 }}>
                {(() => {
                  const amt = parseFloat(tradeAmount || 0);
                  const price = prices[tradeSymbol] || 0;
                  const notional = tradeAmountType === 'crypto' ? (amt * price) : amt;
                  return `$${(notional / tradeLeverage).toFixed(2)}`;
                })()}
              </span>
            </div>
            <div className="flex-between" style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '8px' }}>
              <span className="text-muted" style={{ fontSize: '11px' }}>Minimum Binance:</span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {(() => {
                  const minCrypto = minOrderSizes?.[tradeSymbol] || 0.001;
                  const price = prices[tradeSymbol] || 0;
                  const minUsdtTotal = minCrypto * price;
                  return `${minCrypto} ${baseAsset} (~$${minUsdtTotal.toFixed(2)} łącznej pozycji)`;
                })()}
              </span>
            </div>
            {tradeAmount && (
              <div className="flex-between" style={{ marginTop: '4px' }}>
                <span className="text-muted" style={{ fontSize: '11px' }}>Twoja pozycja:</span>
                <span style={{ fontSize: '11px', color: (() => {
                  const amt = parseFloat(tradeAmount || 0);
                  const price = prices[tradeSymbol] || 0;
                  const notional = effectiveAmountType === 'crypto' ? (amt * price) : amt;
                  const minUsdtTotal = (minOrderSizes?.[tradeSymbol] || 0.001) * price;
                  return notional >= minUsdtTotal ? 'var(--success)' : 'var(--danger)';
                })() }}>
                  {(() => {
                    const amt = parseFloat(tradeAmount || 0);
                    const price = prices[tradeSymbol] || 0;
                    const notional = effectiveAmountType === 'crypto' ? (amt * price) : amt;
                    const cryptoEquiv = effectiveAmountType === 'crypto' ? amt : (amt / price);
                    return `${cryptoEquiv.toFixed(4)} ${baseAsset} (~$${notional.toFixed(2)})`;
                  })()}
                </span>
              </div>
            )}
          </div>

          <button 
            type="submit" 
            className={`btn ${tradeSide === 'BUY' ? 'btn-success' : 'btn-danger'}`} 
            style={{ marginTop: '16px', width: '100%', height: '50px', fontSize: '16px', fontWeight: 'bold' }}
          >
            Złóż zlecenie {tradeSide}
          </button>
        </form>
      </div>
    </div>
  );
};

export default TradeModal;
