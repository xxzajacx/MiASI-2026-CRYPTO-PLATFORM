import { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import zxcvbn from 'zxcvbn';

const RegisterForm = ({ 
  firstName, setFirstName, 
  lastName, setLastName, 
  birthDate, setBirthDate,
  username, setUsername, 
  password, setPassword, 
  passwordScore, setPasswordScore,
  email, setEmail,
  qrUrl, totpSecret, setTotpSecret,
  totpCode, setTotpCode,
  errorMsg, handleRegister, handleVerifyRegister, stage,
  setStage, setErrorMsg
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState('');

  const handlePasswordChange = (e) => {
    const val = e.target.value;
    setPassword(val);
    setPasswordScore(zxcvbn(val).score);
  };

  const onSubmit = (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setErrorMsg("Hasła nie są identyczne!");
      return;
    }
    handleRegister(e);
  };

  if (stage === 'QR') {
    return (
      <div className="flex-column animate-fade-in" style={{ alignItems: 'center' }}>
        <p style={{ fontSize: '14px', marginBottom: '16px' }}>
          1. Zeskanuj poniższy kod w aplikacji Google Authenticator
        </p>
        <div style={{ background: 'white', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
          <QRCodeSVG value={qrUrl} size={200} />
        </div>
        <p style={{ fontSize: '14px', marginBottom: '8px' }}>
          2. Wpisz kod z aplikacji, aby dokończyć rejestrację
        </p>
        <input 
          type="text" 
          placeholder="000 000" 
          className="input-field" 
          value={totpCode} 
          onChange={e => setTotpCode(e.target.value.replace(/\s/g, ''))} 
          style={{ letterSpacing: '4px', textAlign: 'center', fontSize: '20px' }} 
          required 
          minLength={6} 
          maxLength={6} 
        />
        <button 
          type="button" 
          className="btn btn-success" 
          style={{ width: '100%', marginTop: '8px' }} 
          onClick={handleVerifyRegister}
        >
          Weryfikuj i utwórz konto
        </button>
        <button 
          type="button" 
          className="btn" 
          style={{ marginTop: '8px' }} 
          onClick={() => { setStage('REGISTER'); setTotpSecret(''); setErrorMsg(''); }}
        >
          Wróć
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex-column">
      <input 
        type="text" 
        placeholder="Imię" 
        className="input-field" 
        value={firstName} 
        onChange={e => setFirstName(e.target.value)} 
        required 
      />
      <input 
        type="text" 
        placeholder="Nazwisko" 
        className="input-field" 
        value={lastName} 
        onChange={e => setLastName(e.target.value)} 
        required 
      />
      <div style={{ textAlign: 'left', marginBottom: '8px' }}>
        <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Data urodzenia (wymagane 18+)</label>
        <input 
          type="date" 
          max="9999-12-31" 
          className="input-field" 
          value={birthDate} 
          onChange={e => setBirthDate(e.target.value)} 
          required 
          style={{ marginTop: '4px' }} 
        />
      </div>
      <input 
        type="text" 
        placeholder="Nazwa użytkownika" 
        className="input-field" 
        value={username} 
        onChange={e => setUsername(e.target.value)} 
        required 
      />
      <input 
        type="email" 
        placeholder="E-mail (opcjonalnie, do potwierdzeń)" 
        className="input-field" 
        value={email || ''} 
        onChange={e => setEmail(e.target.value)} 
      />
      
      <div style={{ position: 'relative', width: '100%' }}>
        <input 
          type={showPassword ? "text" : "password"} 
          placeholder="Hasło" 
          className="input-field" 
          style={{ width: '100%', paddingRight: '40px' }}
          value={password} 
          onChange={handlePasswordChange} 
          required 
        />
        <button 
          type="button" 
          onClick={() => setShowPassword(!showPassword)}
          style={{
            position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
            background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer'
          }}
        >
          {showPassword ? "👁️" : "👁️‍🗨️"}
        </button>
      </div>

      <div style={{ position: 'relative', width: '100%', marginTop: '8px' }}>
        <input 
          type={showPassword ? "text" : "password"} 
          placeholder="Potwierdź hasło" 
          className="input-field" 
          style={{ width: '100%' }}
          value={confirmPassword} 
          onChange={e => setConfirmPassword(e.target.value)} 
          required 
        />
      </div>
      
      {password.length > 0 && (
        <div style={{ marginTop: '4px', marginBottom: '8px', textAlign: 'left' }}>
          <div style={{ display: 'flex', gap: '4px', height: '4px', marginBottom: '4px' }}>
            {[0, 1, 2, 3].map(i => (
              <div 
                key={i} 
                style={{
                  flex: 1,
                  background: passwordScore > i 
                    ? (passwordScore < 2 ? 'var(--danger)' : passwordScore === 2 ? '#eab308' : 'var(--success)')
                    : 'rgba(255,255,255,0.1)',
                  borderRadius: '2px',
                  transition: '0.3s'
                }} 
              />
            ))}
          </div>
          <small style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {passwordScore < 2 ? 'Słabe (użyj znaków specjalnych/liczb)' : passwordScore === 2 ? 'Średnie' : 'Silne'}
          </small>
        </div>
      )}
      
      <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '16px' }}>
        Zarejestruj
      </button>
      <button 
        type="button" 
        className="btn" 
        style={{ marginTop: '8px' }} 
        onClick={() => setStage('LOGIN')}
      >
        Wróć do logowania
      </button>
    </form>
  );
};

export default RegisterForm;

