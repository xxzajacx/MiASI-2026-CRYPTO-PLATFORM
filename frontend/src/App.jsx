import { useState, useEffect } from 'react';
import axios from 'axios';
import zxcvbn from 'zxcvbn';
import './index.css';

// Global axios configuration for CSRF and cookies
axios.defaults.withCredentials = true;

// Funkcja do pobierania ciasteczek
const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
};

// Dodajemy interceptor, ponieważ Axios domyślnie nie wysyła CSRF dla cross-origin (port 5173 -> 8000)
axios.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrf_token');
  if (csrfToken) {
    config.headers['X-CSRF-TOKEN'] = csrfToken;
  }
  return config;
}, (error) => Promise.reject(error));

import Header from './components/Header';
import TradingViewChart from './components/TradingViewChart';
import MarketPrices from './components/MarketPrices';
import Portfolio from './components/Portfolio';
import Orders from './components/Orders';
import Transactions from './components/Transactions';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import TwoFAVerify from './components/TwoFAVerify';
import ResetPasswordForm from './components/ResetPasswordForm';
import DepositModal from './components/DepositModal';
import TradeModal from './components/TradeModal';
import SettingsPanel from './components/SettingsPanel';
import UserPanelModal from './components/UserPanelModal';
import AdminPanelModal from './components/AdminPanelModal';
import FluidBackground from './components/FluidBackground';

const API_URL = 'http://localhost:8000/api';



function App() {
  // Navigation stage: LOGIN -> REGISTER -> QR -> 2FA -> DASHBOARD
  const [stage, setStage] = useState(localStorage.getItem('token') ? 'DASHBOARD' : 'LOGIN'); 
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [email, setEmail] = useState('');
  const [passwordScore, setPasswordScore] = useState(0);
  const [totpCode, setTotpCode] = useState('');
  const [qrUrl, setQrUrl] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  
  // Auth tokens
  const [tempToken, setTempToken] = useState('');
  const [accessToken, setAccessToken] = useState(localStorage.getItem('token') || '');
  const [isAdmin, setIsAdmin] = useState(false);
  const [hasBinanceKeys, setHasBinanceKeys] = useState(false);
  
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
  const [showUserPanel, setShowUserPanel] = useState(false);
  const [showAdminPanel, setShowAdminPanel] = useState(false);
  
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradeSymbol, setTradeSymbol] = useState('BTCUSDT');
  const [tradeSide, setTradeSide] = useState('BUY');
  const [tradeAmount, setTradeAmount] = useState('');
  const [tradeAmountType, setTradeAmountType] = useState('crypto');
  const [tradeSL, setTradeSL] = useState('');
  const [tradeTP, setTradeTP] = useState('');
  const [tradeLeverage, setTradeLeverage] = useState(1);

  // Email confirmation state for high-value trades
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmToken, setConfirmToken] = useState('');
  const [confirmCode, setConfirmCode] = useState('');
  const [confirmMessage, setConfirmMessage] = useState('');

  const [errorMsg, setErrorMsg] = useState('');
  
  // Session handlers
  const handleLogout = () => {
    setAccessToken('');
    setIsAdmin(false);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    setUsername('');
    setPassword('');
    setFirstName('');
    setLastName('');
    setBirthDate('');
    setTotpCode('');
    setTotpSecret('');
    setStage('LOGIN');
  };

  // Extract CSRF token from cookie
  const extractCsrfToken = () => {
    const cookies = document.cookie.split(';');
    const csrfCookie = cookies.find(c => c.trim().startsWith('csrf_token='));
    if (csrfCookie) {
      const token = csrfCookie.split('=')[1];
      setCsrfToken(token);
      return token;
    }
    return '';
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
    
    // Fetch user info once on dashboard load (handles page refresh)
    axios.get(`${API_URL}/auth/me`)
      .then(res => {
        setIsAdmin(res.data.is_admin || false);
        setHasBinanceKeys(res.data.has_binance_keys || false);
      })
      .catch(err => console.error("Failed to fetch user info", err));

    const fetchDashboardData = async () => {
      try {
        const [pricesRes, walletRes, ordersRes, historyRes, statusRes] = await Promise.all([
          axios.get(`${API_URL}/market/prices`),
          axios.get(`${API_URL}/portfolio/`),
          axios.get(`${API_URL}/orders/`),
          axios.get(`${API_URL}/transactions/`),
          axios.get(`${API_URL}/market/status`)
        ]);
        
        if (pricesRes.data && typeof pricesRes.data === 'object') {
          // Backend returns Dict[str, float] directly
          setPrices(pricesRes.data);
        }
        setWallet(Array.isArray(walletRes.data) ? walletRes.data : (walletRes.data.items || []));
        setOrders(Array.isArray(ordersRes.data) ? ordersRes.data : (ordersRes.data.items || []));
        setHistory(Array.isArray(historyRes.data) ? historyRes.data : (historyRes.data.items || []));
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
      const res = await axios.post(`${API_URL}/auth/register-init`, { 
        username, 
        password,
        first_name: firstName,
        last_name: lastName,
        birth_date: birthDate,
        email: email || null
      });
      setQrUrl(res.data.totp_uri);
      setTotpSecret(res.data.totp_secret);
      setTotpCode('');
      setStage('QR');
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Błąd rejestracji');
    }
  };

  const handleVerifyRegister = async () => {
    setErrorMsg('');
    if (!totpCode || totpCode.length !== 6) {
      setErrorMsg('Wpisz poprawny 6-cyfrowy kod z aplikacji Google Authenticator');
      return;
    }
    try {
      const res = await axios.post(`${API_URL}/auth/register-verify`, {
        username,
        password,
        first_name: firstName,
        last_name: lastName,
        birth_date: birthDate,
        email: email || null,
        totp_secret: totpSecret,
        totp_code: totpCode
      });
      alert('Konto zostało utworzone! Możesz się teraz zalogować.');
      setStage('LOGIN');
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Błąd weryfikacji');
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

  const handleResetPassword = async (e, code) => {
    e.preventDefault();
    setErrorMsg('');
    try {
      await axios.post(`${API_URL}/auth/reset-password`, {
        username,
        totp_code: code,
        new_password: password
      });
      alert('Hasło zostało pomyślnie zmienione! Możesz się teraz zalogować.');
      setStage('LOGIN');
      setPassword('');
      setPasswordScore(0);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Błąd resetowania hasła');
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
      
      // Check if user is admin and fetch user info
      try {
        const userRes = await axios.get(`${API_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setIsAdmin(userRes.data.is_admin || false);
        setHasBinanceKeys(userRes.data.has_binance_keys || false);
      } catch {
        setIsAdmin(false);
      }
      
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
    } catch(err) {
      alert("Błąd podczas wpłaty: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleMarketTrade = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post(`${API_URL}/market/trade`, {
        symbol: tradeSymbol,
        side: tradeSide,
        amount: parseFloat(tradeAmount),
        amount_type: tradeAmountType,
        leverage: parseInt(tradeLeverage),
        stop_loss: tradeSL ? parseFloat(tradeSL) : null,
        take_profit: tradeTP ? parseFloat(tradeTP) : null
      });

      // Check if email confirmation is required
      if (res.data.requires_confirmation) {
        setConfirmToken(res.data.confirmation_token);
        setConfirmMessage(res.data.message);
        setConfirmCode('');
        setShowTradeModal(false);
        setShowConfirmModal(true);
        return;
      }

      setShowTradeModal(false);
      setTradeAmount('');
      setTradeSL('');
      setTradeTP('');
      setTradeLeverage(1);
      alert("Transakcja wykonana pomyślnie!");
    } catch(err) {
      alert("Błąd transakcji: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleConfirmTrade = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/market/trade/confirm`, {
        confirmation_token: confirmToken,
        confirmation_code: confirmCode
      });
      setShowConfirmModal(false);
      setConfirmToken('');
      setConfirmCode('');
      setTradeAmount('');
      setTradeSL('');
      setTradeTP('');
      setTradeLeverage(1);
      alert("Transakcja potwierdzona i wykonana pomyślnie!");
    } catch(err) {
      alert("Błąd potwierdzenia: " + (err.response?.data?.detail || err.message));
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
      <>
        <FluidBackground />
        <div className="layout flex-column" style={{ justifyContent: 'center', alignItems: 'center', height: '100vh', padding: 0 }}>
          <div className="glass-panel animate-fade-in" style={{ width: '400px', textAlign: 'center', position: 'relative', zIndex: 10 }}>
            <div style={{ marginBottom: '24px' }}>
              <h1 className="text-gradient" style={{ fontSize: '32px', marginBottom: '8px' }}>Giełda Premium</h1>
              <p className="text-muted">Inwestuj inteligentnie dzięki automatyzacji.</p>
            </div>
           
          {errorMsg && <div style={{ color: 'var(--danger)', marginBottom: '12px', fontSize: '14px' }}>{errorMsg}</div>}

          {stage === 'LOGIN' && (
            <LoginForm 
              username={username} 
              setUsername={setUsername} 
              password={password} 
              setPassword={setPassword}
              handlePasswordChange={handlePasswordChange}
              errorMsg={errorMsg}
              handleLogin={handleLogin}
              setStage={setStage}
            />
          )}

          {stage === 'REGISTER' && (
            <RegisterForm 
              firstName={firstName} setFirstName={setFirstName}
              lastName={lastName} setLastName={setLastName}
              birthDate={birthDate} setBirthDate={setBirthDate}
              username={username} setUsername={setUsername}
              password={password} setPassword={setPassword}
              passwordScore={passwordScore} setPasswordScore={setPasswordScore}
              email={email} setEmail={setEmail}
              qrUrl={qrUrl} totpSecret={totpSecret} setTotpSecret={setTotpSecret}
              totpCode={totpCode} setTotpCode={setTotpCode}
              errorMsg={errorMsg}
              handleRegister={handleRegister}
              handleVerifyRegister={handleVerifyRegister}
              stage={stage}
              setStage={setStage}
              setErrorMsg={setErrorMsg}
            />
          )}

          {stage === 'RESET_PASSWORD' && (
            <ResetPasswordForm
              username={username}
              setUsername={setUsername}
              password={password}
              handlePasswordChange={handlePasswordChange}
              passwordScore={passwordScore}
              errorMsg={errorMsg}
              handleResetPassword={handleResetPassword}
              setStage={setStage}
            />
          )}

          {stage === 'QR' && (
            <RegisterForm 
              qrUrl={qrUrl}
              totpCode={totpCode} setTotpCode={setTotpCode}
              errorMsg={errorMsg}
              handleVerifyRegister={handleVerifyRegister}
              stage={stage}
              setStage={setStage}
              setTotpSecret={setTotpSecret}
              setErrorMsg={setErrorMsg}
            />
          )}

          {stage === '2FA' && (
            <TwoFAVerify 
              totpCode={totpCode} setTotpCode={setTotpCode}
              errorMsg={errorMsg}
              handle2FA={handle2FA}
              setStage={setStage}
            />
          )}
        </div>
      </div>
      </>
    );
  }

  return (
    <>
      <FluidBackground />
      <div className="layout animate-fade-in" style={{ position: 'relative', zIndex: 10 }}>
        <Header 
        systemStatus={systemStatus} 
        handleLogout={handleLogout} 
        setShowUserPanel={setShowUserPanel} 
        isAdmin={isAdmin}
        setShowAdminPanel={setShowAdminPanel}
      />

      <div className="grid grid-cols-3">
        {/* Row 1: Chart and Market Watch */}
        <TradingViewChart symbol={tradeSymbol} />

        <MarketPrices 
          prices={prices}
          tradeSymbol={tradeSymbol}
          setTradeSymbol={setTradeSymbol}
          setShowTradeModal={setShowTradeModal}
          isAdmin={isAdmin}
        />

        {/* Portfolio Widget */}
        <Portfolio 
          wallet={wallet}
          prices={prices}
          setShowDepositModal={setShowDepositModal}
          isAdmin={isAdmin}
          systemStatus={systemStatus}
        />

        {/* Orders Panel */}
        <Orders 
          orders={orders}
          prices={prices}
          handleCancelOrder={handleCancelOrder}
        />

        {/* History Panel */}
        <Transactions history={history} />

        {/* Admin Panel (visible only to admins) */}
      </div>

      {/* Modals Overlay */}
      <UserPanelModal
        showUserPanel={showUserPanel}
        setShowUserPanel={setShowUserPanel}
        hasBinanceKeys={hasBinanceKeys}
        setHasBinanceKeys={setHasBinanceKeys}
      />
      <AdminPanelModal 
        showAdminPanel={showAdminPanel} 
        setShowAdminPanel={setShowAdminPanel} 
        token={accessToken} 
      />
      {!isAdmin && !systemStatus?.binance_connected && (
        <DepositModal 
          showDepositModal={showDepositModal}
          setShowDepositModal={setShowDepositModal}
          depositAsset={depositAsset}
          setDepositAsset={setDepositAsset}
          depositAmount={depositAmount}
          setDepositAmount={setDepositAmount}
          handleDeposit={handleDeposit}
        />
      )}

      {!isAdmin && (
        <TradeModal 
          showTradeModal={showTradeModal}
          setShowTradeModal={setShowTradeModal}
          tradeSymbol={tradeSymbol}
          setTradeSymbol={setTradeSymbol}
          tradeSide={tradeSide}
          setTradeSide={setTradeSide}
          tradeAmount={tradeAmount}
          setTradeAmount={setTradeAmount}
          tradeAmountType={tradeAmountType}
          setTradeAmountType={setTradeAmountType}
          tradeSL={tradeSL}
          setTradeSL={setTradeSL}
          tradeTP={tradeTP}
          setTradeTP={setTradeTP}
          tradeLeverage={tradeLeverage}
          setTradeLeverage={setTradeLeverage}
          prices={prices}
          minOrderSizes={minOrderSizes}
          handleMarketTrade={handleMarketTrade}
          wallet={wallet}
          setErrorMsg={setErrorMsg}
        />
      )}

      {/* Email Confirmation Modal for high-value trades */}
      {showConfirmModal && (
        <div style={{ 
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          background: 'rgba(0,0,0,0.7)', display: 'flex', 
          justifyContent: 'center', alignItems: 'center', zIndex: 1000 
        }}>
          <div className="glass-panel animate-fade-in" style={{ width: '400px', textAlign: 'center' }}>
            <h2 className="text-gradient" style={{ marginBottom: '16px' }}>Potwierdzenie e-mail</h2>
            <p style={{ fontSize: '14px', marginBottom: '16px', color: 'var(--text-muted)' }}>
              {confirmMessage}
            </p>
            <form onSubmit={handleConfirmTrade} className="flex-column">
              <input 
                type="text" 
                placeholder="Wpisz 6-cyfrowy kod" 
                className="input-field" 
                value={confirmCode} 
                onChange={e => setConfirmCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                style={{ letterSpacing: '6px', textAlign: 'center', fontSize: '24px' }}
                maxLength={6}
                required 
              />
              <button type="submit" className="btn btn-success" style={{ width: '100%', marginTop: '12px' }}>
                Potwierdź transakcję
              </button>
              <button 
                type="button" 
                className="btn" 
                style={{ marginTop: '8px' }}
                onClick={() => { setShowConfirmModal(false); setConfirmToken(''); setConfirmCode(''); }}
              >
                Anuluj
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
    </>
  );
}

export default App;
