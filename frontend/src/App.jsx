import { useState, useEffect } from 'react';
import axios from 'axios';
import { QRCodeSVG } from 'qrcode.react';
import zxcvbn from 'zxcvbn';
import './index.css';

const API_URL = 'http://127.0.0.1:8000/api';

// TradingView Widget Component moved outside to prevent re-renders on data refresh
const TradingViewChart = ({ symbol = "BTCUSDT" }) => {
  return (
    <div className="glass-panel" style={{ height: '450px', padding: '0', overflow: 'hidden', gridColumn: 'span 2' }}>
      <iframe
        title="TradingView Chart"
        src={`https://s.tradingview.com/widgetembed/?frameElementId=tradingview_76d87&symbol=BINANCE%3A${symbol}&interval=D&hidesidetoolbar=1&hidetoptoolbar=1&symboledit=1&saveimage=1&toolbarbg=f1f3f6&theme=dark&style=1&timezone=Etc%2FUTC&locale=pl`}
        style={{ width: '100%', height: '100%', border: 'none' }}
      />
    </div>
  );
};

function App() {
  // Navigation stage: LOGIN -> REGISTER -> QR -> 2FA -> DASHBOARD
  const [stage, setStage] = useState(localStorage.getItem('token') ? 'DASHBOARD' : 'LOGIN'); 
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [passwordScore, setPasswordScore] = useState(0);
  const [totpCode, setTotpCode] = useState('');
  const [qrUrl, setQrUrl] = useState('');
  
  // Auth tokens
  const [tempToken, setTempToken] = useState('');
  const [accessToken, setAccessToken] = useState(localStorage.getItem('token') || '');

  // Dashboard states
  const [prices, setPrices] = useState({ BTCUSDT: 0, ETHUSDT: 0 });
  const [marketStatus, setMarketStatus] = useState('offline');
  const [minOrderSizes, setMinOrderSizes] = useState({});
  const [wallet, setWallet] = useState([]);
  const [orders, setOrders] = useState([]);
  const [history, setHistory] = useState([]);
  
  // Modals state
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [depositAmount, setDepositAmount] = useState('');
  const [depositAsset, setDepositAsset] = useState('USDT');
  
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradeSymbol, setTradeSymbol] = useState('BTCUSDT');
  const [tradeSide, setTradeSide] = useState('BUY');
  const [tradeAmount, setTradeAmount] = useState('');
  const [tradeAmountType, setTradeAmountType] = useState('crypto'); // 'crypto' or 'usdt'
  const [tradeSL, setTradeSL] = useState('');
  const [tradeTP, setTradeTP] = useState('');
  const [tradeLeverage, setTradeLeverage] = useState(1);

  const [errorMsg, setErrorMsg] = useState('');

  // Session handlers
  const handleLogout = () => {
    setAccessToken('');
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUsername('');
    setPassword('');
    setFirstName('');
    setLastName('');
    setBirthDate('');
    setTotpCode('');
    setStage('LOGIN');
  };

  // Axios authorization persistence
  useEffect(() => {
    if (accessToken) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [accessToken]);

  const [systemStatus, setSystemStatus] = useState({ mode: 'SIMULATION', binance_connected: false });

  // Real-time data polling
  useEffect(() => {
    if (stage !== 'DASHBOARD') return;
    
    const fetchDashboardData = async () => {
      try {
        const [pricesRes, walletRes, ordersRes, historyRes, statusRes] = await Promise.all([
          axios.get(`${API_URL}/market/prices`),
          axios.get(`${API_URL}/portfolio/`),
          axios.get(`${API_URL}/orders/`),
          axios.get(`${API_URL}/transactions/`),
          axios.get(`${API_URL}/market/status`)
        ]);
        
        if (pricesRes.data.prices) setPrices(pricesRes.data.prices);
        setWallet(walletRes.data.items || []);
        setOrders(ordersRes.data.items || []);
        setHistory(historyRes.data.items || []);
        setSystemStatus(statusRes.data);
        setMarketStatus(statusRes.data.status);
        if (statusRes.data.min_order_sizes) setMinOrderSizes(statusRes.data.min_order_sizes);
      } catch (err) {
        console.error("Failed to fetch dashboard data", err);
        if (err.response?.status === 401) {
          handleLogout();
        }
      }
    };

    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000);
    return () => clearInterval(interval);
  }, [stage]);

  // Handle forms
  const handlePasswordChange = (e) => {
    const val = e.target.value;
    setPassword(val);
    setPasswordScore(zxcvbn(val).score);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    try {
      const res = await axios.post(`${API_URL}/auth/register`, { 
        username, 
        password,
        first_name: firstName,
        last_name: lastName,
        birth_date: birthDate
      });
      setQrUrl(res.data.totp_uri);
      setStage('QR');
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Błąd rejestracji');
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const res = await axios.post(`${API_URL}/auth/login`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      setTempToken(res.data.access_token);
      setStage('2FA');
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Błędny login lub hasło');
    }
  };

  const handle2FA = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    try {
      const res = await axios.post(`${API_URL}/auth/verify-2fa`, {
        temp_token: tempToken,
        totp_code: totpCode
      });
      
      const token = res.data.access_token;
      setAccessToken(token);
      localStorage.setItem('token', token);
      setStage('DASHBOARD');
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Błędny kod 2FA');
    }
  };

  const handleDeposit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/portfolio/deposit`, {
        asset: depositAsset,
        amount: parseFloat(depositAmount)
      });
      setShowDepositModal(false);
      setDepositAmount('');
      // Dane odświeżą się w następnym interwale
    } catch(err) {
      alert("Błąd podczas wpłaty: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleMarketTrade = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/market/trade`, {
        symbol: tradeSymbol,
        side: tradeSide,
        amount: parseFloat(tradeAmount),
        amount_type: tradeAmountType,
        leverage: parseInt(tradeLeverage),
        stop_loss: tradeSL ? parseFloat(tradeSL) : null,
        take_profit: tradeTP ? parseFloat(tradeTP) : null
      });
      setShowTradeModal(false);
      setTradeAmount('');
      setTradeSL('');
      setTradeTP('');
      setTradeLeverage(1);
      alert("Transakcja wykonana pomyślnie! (W trybie symulacji dane zostały zapisane lokalnie)");
    } catch(err) {
      alert("Błąd transakcji: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleCancelOrder = async (orderId) => {
    try {
      await axios.delete(`${API_URL}/orders/${orderId}`);
    } catch(err) {
      console.error("Failed to cancel order:", err);
      alert("Błąd anulowania zlecenia.");
    }
  };

  if (stage !== 'DASHBOARD') {
    return (
      <div className="layout flex-column" style={{ justifyContent: 'center', alignItems: 'center', height: '100vh', padding: 0 }}>
        <div className="glass-panel animate-fade-in" style={{ width: '400px', textAlign: 'center' }}>
          <div style={{ marginBottom: '24px' }}>
            <h1 className="text-gradient" style={{ fontSize: '32px', marginBottom: '8px' }}>Giełda Premium</h1>
            <p className="text-muted">Inwestuj inteligentnie dzięki automatyzacji.</p>
          </div>
          
          {errorMsg && <div style={{ color: 'var(--danger)', marginBottom: '12px', fontSize: '14px' }}>{errorMsg}</div>}

          {stage === 'LOGIN' && (
            <form onSubmit={handleLogin} className="flex-column">
              <input type="text" placeholder="Nazwa użytkownika" className="input-field" value={username} onChange={e => setUsername(e.target.value)} required />
              <input type="password" placeholder="Hasło" className="input-field" value={password} onChange={e => setPassword(e.target.value)} required />
              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '8px' }}>Zaloguj się</button>
              <button type="button" className="btn" style={{ marginTop: '8px' }} onClick={() => setStage('REGISTER')}>Nie masz konta? Zarejestruj się</button>
            </form>
          )}

          {stage === 'REGISTER' && (
            <form onSubmit={handleRegister} className="flex-column">
              <input type="text" placeholder="Imię" className="input-field" value={firstName} onChange={e => setFirstName(e.target.value)} required />
              <input type="text" placeholder="Nazwisko" className="input-field" value={lastName} onChange={e => setLastName(e.target.value)} required />
              <div style={{ textAlign: 'left', marginBottom: '8px' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Data urodzenia (wymagane 18+)</label>
                <input type="date" max="9999-12-31" className="input-field" value={birthDate} onChange={e => setBirthDate(e.target.value)} required style={{ marginTop: '4px' }} />
              </div>
              <input type="text" placeholder="Nazwa użytkownika" className="input-field" value={username} onChange={e => setUsername(e.target.value)} required />
              <input type="password" placeholder="Hasło" className="input-field" value={password} onChange={handlePasswordChange} required />
              
              {password.length > 0 && (
                <div style={{ marginTop: '4px', marginBottom: '8px', textAlign: 'left' }}>
                  <div style={{ display: 'flex', gap: '4px', height: '4px', marginBottom: '4px' }}>
                    {[0, 1, 2, 3].map(i => (
                      <div key={i} style={{
                        flex: 1,
                        background: passwordScore > i 
                          ? (passwordScore < 2 ? 'var(--danger)' : passwordScore === 2 ? '#eab308' : 'var(--success)')
                          : 'rgba(255,255,255,0.1)',
                        borderRadius: '2px',
                        transition: '0.3s'
                      }} />
                    ))}
                  </div>
                  <small style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {passwordScore < 2 ? 'Słabe (użyj znaków specjalnych/liczb)' : passwordScore === 2 ? 'Średnie' : 'Silne'}
                  </small>
                </div>
              )}

              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '8px' }}>Zarejestruj</button>
              <button type="button" className="btn" style={{ marginTop: '8px' }} onClick={() => setStage('LOGIN')}>Wróć do logowania</button>
            </form>
          )}

          {stage === 'QR' && (
            <div className="flex-column animate-fade-in" style={{ alignItems: 'center' }}>
              <p style={{ fontSize: '14px', marginBottom: '16px' }}>Zeskanuj poniższy kod w aplikacji Google Authenticator</p>
              <div style={{ background: 'white', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                <QRCodeSVG value={qrUrl} size={200} />
              </div>
              <button type="button" className="btn btn-success" style={{ width: '100%' }} onClick={() => setStage('LOGIN')}>Przejdź do logowania</button>
            </div>
          )}

          {stage === '2FA' && (
            <form onSubmit={handle2FA} className="flex-column animate-fade-in">
              <p style={{ fontSize: '14px', marginBottom: '8px' }}>Wpisz kod z Google Authenticator (TOTP)</p>
              <input type="text" placeholder="000 000" className="input-field" value={totpCode} onChange={e => setTotpCode(e.target.value)} style={{ letterSpacing: '4px', textAlign: 'center', fontSize: '20px' }} required minLength={6} maxLength={6} />
              <button type="submit" className="btn btn-success" style={{ width: '100%', marginTop: '8px' }}>Weryfikuj</button>
              <button type="button" className="btn" style={{ marginTop: '8px' }} onClick={() => setStage('LOGIN')}>Wróć</button>
            </form>
          )}
        </div>
      </div>
    );
  }


  return (
    <div className="layout animate-fade-in">
      <header className="flex-between glass-panel" style={{ marginBottom: '24px', padding: '16px 24px' }}>
        <div>
          <h1 className="text-gradient" style={{ fontSize: '24px' }}>Giełda Premium</h1>
        </div>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div style={{ textAlign: 'right' }}>
             <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Status Systemu</div>
             <div style={{ fontSize: '14px', color: systemStatus.binance_connected ? 'var(--success)' : 'var(--accent)' }}>
               {systemStatus.binance_connected ? '🟢 LIVE' : '🔵 SYMULACJA'}
             </div>
          </div>
          <button className="btn" onClick={handleLogout}>Wyloguj</button>
        </div>
      </header>

      <div className="grid grid-cols-3">
        {/* Row 1: Chart and Market Watch */}
        <TradingViewChart symbol={tradeSymbol} />

        <div className="glass-panel">
           <h3 style={{ marginBottom: '16px', color: 'var(--text-muted)' }}>Rynek (Live)</h3>
           <div className="flex-column" style={{ gap: '12px' }}>
             {['BTCUSDT', 'ETHUSDT', 'BNBUSDT'].map(sym => (
               <div key={sym} className="flex-between" style={{ padding: '8px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', cursor: 'pointer', border: tradeSymbol === sym ? '1px solid var(--primary)' : '1px solid transparent' }} onClick={() => setTradeSymbol(sym)}>
                 <span style={{ fontWeight: '600' }}>{sym.replace('USDT', '/USDT')}</span>
                 <span className="text-success" style={{ fontWeight: '700' }}>
                   ${prices[sym]?.toFixed(2) || '---'}
                 </span>
               </div>
             ))}
           </div>
           <div style={{ marginTop: '24px' }}>
              <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => setShowTradeModal(true)}>🛒 Otwórz Pozycję</button>
           </div>
        </div>

        {/* Portfolio Widget */}
        <div className="glass-panel" style={{ gridColumn: 'span 3' }}>
           <div className="flex-between" style={{ marginBottom: '16px' }}>
             <h3 style={{ color: 'var(--text-muted)' }}>Mój Portfel</h3>
             <button className="btn btn-success" onClick={() => setShowDepositModal(true)}>+ Wpłać USDT</button>
           </div>
           
           {wallet.length === 0 ? <p className="text-muted">Brak aktywów w portfelu. Skorzystaj z opcji "Wpłać USDT", aby zasilić konto symulacyjne.</p> : (
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
                 {wallet.map(w => (
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

        {/* Orders Panel */}
        <div className="glass-panel" style={{ gridColumn: 'span 3' }}>
          <h3 style={{ color: 'var(--text-muted)', marginBottom: '16px' }}>Aktywne Zlecenia Ochronne (TP/SL)</h3>
          {orders.filter(o => o.status === 'ACTIVE').length === 0 ? <p className="text-muted">Brak oczekujących zleceń.</p> : (
            <table>
               <thead>
                 <tr>
                   <th>Para</th>
                   <th>Typ</th>
                   <th>Akcja</th>
                   <th>Ilość</th>
                   <th>Cena Aktywacji</th>
                   <th>Aktualna Cena</th>
                   <th>Status</th>
                 </tr>
               </thead>
               <tbody>
                 {orders.filter(o => o.status === 'ACTIVE').map(o => (
                   <tr key={o.id}>
                     <td style={{ fontWeight: 600 }}>{o.symbol}</td>
                     <td>
                        <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', background: o.order_type === 'STOP_LOSS' ? 'var(--danger-glow)' : 'var(--success-glow)', color: o.order_type === 'STOP_LOSS' ? 'var(--danger)' : 'var(--success)' }}>
                          {o.order_type.replace('_', ' ')}
                        </span>
                     </td>
                     <td style={{ color: o.side === 'BUY' ? 'var(--success)' : 'var(--danger)' }}>{o.side}</td>
                     <td>{o.amount}</td>
                     <td style={{ fontWeight: 600 }}>${o.target_price}</td>
                     <td className={prices[o.symbol] > o.target_price ? 'text-success' : 'text-danger'}>
                        ${prices[o.symbol]?.toFixed(2) || '---'}
                     </td>
                     <td><span className="animate-pulse">Aktywne</span></td>
                     <td>
                       <button className="btn" style={{ padding: '4px 12px', fontSize: '12px', color: 'var(--danger)', borderColor: 'var(--danger-glow)' }} onClick={() => handleCancelOrder(o.id)}>Anuluj</button>
                     </td>
                   </tr>
                 ))}
               </tbody>
             </table>
          )}
        </div>

        {/* History Panel */}
        <div className="glass-panel" style={{ gridColumn: 'span 3' }}>
          <h3 style={{ marginBottom: '16px', color: 'var(--text-muted)' }}>Historia Operacji</h3>
          {history.length === 0 ? <p className="text-muted">Brak historii.</p> : (
            <table>
               <thead>
                 <tr>
                   <th>Data</th>
                   <th>Typ</th>
                   <th>Aktywo</th>
                   <th>Ilość</th>
                   <th>Cena</th>
                   <th>Status</th>
                   <th>Informacje</th>
                 </tr>
               </thead>
               <tbody>
                 {history.map(h => (
                   <tr key={h.id}>
                     <td style={{ fontSize: '12px' }}>{new Date(h.created_at).toLocaleString()}</td>
                     <td style={{ fontWeight: 600, color: h.type === 'BUY' || h.type === 'DEPOSIT' ? 'var(--success)' : 'var(--danger)' }}>{h.type}</td>
                     <td>{h.asset}</td>
                     <td>{h.amount}</td>
                     <td>{h.price ? `$${h.price.toFixed(2)}` : '-'}</td>
                     <td><span className={h.status === 'COMPLETED' ? "text-success" : "text-danger"}>{h.status}</span></td>
                     <td className="text-muted" style={{ fontSize: '12px' }}>{h.log_message}</td>
                   </tr>
                 ))}
               </tbody>
             </table>
          )}
        </div>
      </div>

      {/* Modals Overlay */}
      {(showDepositModal || showTradeModal) && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          
          {showDepositModal && (
            <div className="glass-panel animate-fade-in" style={{ width: '400px' }}>
              <h2 className="text-gradient" style={{ marginBottom: '16px' }}>Wpłać Środki</h2>
              <form onSubmit={handleDeposit} className="flex-column">
                <label style={{ fontSize: '14px', color: 'var(--text-muted)' }}>Aktywo</label>
                <select className="input-field" value={depositAsset} onChange={e => setDepositAsset(e.target.value)}>
                  <option value="USDT">USDT (Dolar)</option>
                  <option value="BTC">BTC (Bitcoin)</option>
                  <option value="ETH">ETH (Ethereum)</option>
                  <option value="BNB">BNB (Binance Coin)</option>
                </select>

                <label style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '8px', marginBottom: '4px' }}>Ilość</label>
                <input type="number" step="0.0001" min="0.0001" className="input-field" placeholder="np. 1.5" value={depositAmount} onChange={e => setDepositAmount(e.target.value)} required />
                <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
                  <button type="submit" className="btn btn-success" style={{ flex: 1 }}>Wpłać</button>
                  <button type="button" className="btn" style={{ flex: 1 }} onClick={() => setShowDepositModal(false)}>Anuluj</button>
                </div>
              </form>
            </div>
          )}

          {showTradeModal && (() => {
            const baseAsset = tradeSymbol.replace('USDT', '');
            const quoteAsset = 'USDT';
            const currentBalanceAsset = tradeSide === 'BUY' ? quoteAsset : baseAsset;
            const walletItem = wallet.find(w => w.asset_symbol === currentBalanceAsset);
            const available = walletItem ? walletItem.balance : 0;

            const handleMax = () => {
              if (tradeSide === 'BUY') {
                if (tradeAmountType === 'usdt') {
                  setTradeAmount(available.toFixed(2));
                } else {
                  const price = prices[tradeSymbol];
                  if (price) {
                    const maxAmount = (available * tradeLeverage) / price;
                    setTradeAmount(maxAmount.toFixed(5));
                  }
                }
              } else {
                if (tradeAmountType === 'usdt') {
                  const price = prices[tradeSymbol];
                  if (price) {
                    setTradeAmount((available * price).toFixed(2));
                  }
                } else {
                  setTradeAmount(available.toFixed(5));
                }
              }
            };

            return (
              <div className="glass-panel animate-fade-in" style={{ width: '450px' }}>
                <div className="flex-between" style={{ marginBottom: '16px' }}>
                  <h2 className="text-gradient">Handel {tradeSymbol.replace('USDT', '/USDT')}</h2>
                  <button className="btn" onClick={() => setShowTradeModal(false)}>✕</button>
                </div>

                <form onSubmit={handleMarketTrade} className="flex-column">
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                    <button type="button" className={`btn ${tradeSide === 'BUY' ? 'btn-success' : ''}`} style={{ flex: 1, opacity: tradeSide === 'BUY' ? 1 : 0.5 }} onClick={() => setTradeSide('BUY')}>KUP</button>
                    <button type="button" className={`btn ${tradeSide === 'SELL' ? 'btn-danger' : ''}`} style={{ flex: 1, opacity: tradeSide === 'SELL' ? 1 : 0.5 }} onClick={() => setTradeSide('SELL')}>SPRZEDAJ</button>
                  </div>

                  <div className="input-group">
                    <div className="flex-between" style={{ marginBottom: '8px' }}>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Ilość ({tradeAmountType === 'crypto' ? baseAsset : 'USDT'})</label>
                        <div className="flex-row" style={{ background: 'var(--bg-card)', borderRadius: '4px', padding: '2px' }}>
                          <button type="button" className={`btn ${tradeAmountType === 'crypto' ? 'btn-success' : ''}`} style={{ padding: '2px 8px', fontSize: '10px' }} onClick={() => setTradeAmountType('crypto')}>{baseAsset}</button>
                          <button type="button" className={`btn ${tradeAmountType === 'usdt' ? 'btn-success' : ''}`} style={{ padding: '2px 8px', fontSize: '10px' }} onClick={() => setTradeAmountType('usdt')}>USDT</button>
                        </div>
                      </div>
                      <span style={{ fontSize: '12px', color: 'var(--accent)' }}>
                        Dostępne: {tradeAmountType === 'crypto' 
                          ? available.toFixed(5) + ' ' + currentBalanceAsset 
                          : (available * (prices[tradeSymbol] || 0)).toFixed(2) + ' USDT'}
                      </span>
                    </div>
                    <div style={{ position: 'relative' }}>
                      <input type="number" step="any" className="input-field" placeholder={tradeAmountType === 'crypto' ? "0.00000" : "0.00"} value={tradeAmount} onChange={e => setTradeAmount(e.target.value)} required />
                      <button type="button" className="btn" style={{ position: 'absolute', right: '5px', top: '5px', padding: '5px 10px', fontSize: '11px', height: '30px' }} onClick={handleMax}>MAX</button>
                    </div>
                  </div>

                  <div className="input-group" style={{ marginTop: '12px' }}>
                    <label style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>Dźwignia (Leverage)</label>
                    <select className="input-field" value={tradeLeverage} onChange={e => setTradeLeverage(e.target.value)}>
                      {[1, 2, 5, 10, 20, 50, 100].map(lv => (
                        <option key={lv} value={lv}>{lv}x</option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2" style={{ gap: '12px', marginTop: '12px' }}>
                    <div className="input-group">
                      <label style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>Take Profit ($)</label>
                      <input type="number" step="any" className="input-field" placeholder="Cena" value={tradeTP} onChange={e => setTradeTP(e.target.value)} />
                    </div>
                    <div className="input-group">
                      <label style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>Stop Loss ($)</label>
                      <input type="number" step="any" className="input-field" placeholder="Cena" value={tradeSL} onChange={e => setTradeSL(e.target.value)} />
                    </div>
                  </div>

                  <div style={{ padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', marginTop: '16px', fontSize: '13px' }}>
                    <div className="flex-between">
                      <span className="text-muted">Szacowany koszt (Margin):</span>
                      <span style={{ fontWeight: 600 }}>
                        ${(() => {
                          const amt = parseFloat(tradeAmount || 0);
                          const price = prices[tradeSymbol] || 0;
                          const notional = tradeAmountType === 'crypto' ? (amt * price) : amt;
                          return (notional / tradeLeverage).toFixed(2);
                        })()}
                      </span>
                    </div>
                    {parseFloat(tradeAmount || 0) > 0 && (() => {
                      const amt = parseFloat(tradeAmount || 0);
                      const price = prices[tradeSymbol] || 0;
                      const notional = tradeAmountType === 'crypto' ? (amt * price) : amt;
                      const cryptoAmt = tradeAmountType === 'usdt' ? (amt / price) : amt;
                      const minSize = minOrderSizes[tradeSymbol] || 0.001;

                      if (notional < 5) {
                        return <div style={{ color: 'var(--danger)', fontSize: '11px', marginTop: '4px' }}>⚠ Wartość min. to 5 USDT (Obecnie: ${notional.toFixed(2)})</div>;
                      }
                      if (cryptoAmt < minSize) {
                        return <div style={{ color: 'var(--danger)', fontSize: '11px', marginTop: '4px' }}>⚠ Min. ilość dla {tradeSymbol.replace('USDT','')} to {minSize} (Obecnie: {cryptoAmt.toFixed(6)})</div>;
                      }
                      return null;
                    })()}
                  </div>

                  <button 
                    type="submit" 
                    className={`btn ${tradeSide === 'BUY' ? 'btn-success' : 'btn-danger'}`} 
                    style={{ marginTop: '16px', width: '100%', height: '50px', fontSize: '16px', fontWeight: 'bold' }}
                    disabled={!tradeAmount || parseFloat(tradeAmount) <= 0 || (() => {
                      const amt = parseFloat(tradeAmount || 0);
                      const price = prices[tradeSymbol] || 0;
                      const notional = tradeAmountType === 'crypto' ? (amt * price) : amt;
                      const cryptoAmt = tradeAmountType === 'usdt' ? (amt / price) : amt;
                      const minSize = minOrderSizes[tradeSymbol] || 0.001;
                      return notional < 5 || cryptoAmt < minSize;
                    })()}
                  >
                    Złóż zlecenie {tradeSide}
                  </button>
                </form>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}

export default App;

