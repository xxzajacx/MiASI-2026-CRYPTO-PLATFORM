import { useState } from 'react';

const ResetPasswordForm = ({ username, setUsername, password, handlePasswordChange, passwordScore, errorMsg, handleResetPassword, setStage }) => {
  const [totpCode, setTotpCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  return (
    <form onSubmit={(e) => handleResetPassword(e, totpCode)} className="flex-column">
      <h2 style={{ textAlign: 'center', marginBottom: '16px' }}>Zmień hasło</h2>
      
      <input 
        type="text" 
        placeholder="Nazwa użytkownika" 
        className="input-field" 
        value={username} 
        onChange={e => setUsername(e.target.value)} 
        required 
      />
      
      <input 
        type="text" 
        placeholder="Kod z Google Authenticator (6 cyfr)" 
        className="input-field" 
        value={totpCode} 
        onChange={e => setTotpCode(e.target.value)}
        maxLength={6}
        required 
      />
      
      <div style={{ position: 'relative', width: '100%', marginBottom: '4px' }}>
        <input 
          type={showPassword ? "text" : "password"} 
          placeholder="Nowe hasło" 
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
            background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          {showPassword ? "Ukryj" : "Pokaż"}
        </button>
      </div>

      {password && (
        <div style={{ fontSize: '12px', marginBottom: '12px', textAlign: 'left', width: '100%' }}>
          <div style={{ display: 'flex', gap: '4px', marginBottom: '4px' }}>
            {[0,1,2,3,4].map(s => (
              <div 
                key={s} 
                style={{
                  height: '4px', flex: 1, borderRadius: '2px',
                  background: s <= passwordScore 
                    ? (passwordScore < 2 ? 'var(--danger)' : passwordScore < 3 ? 'var(--warning)' : 'var(--success)') 
                    : 'rgba(255,255,255,0.1)'
                }} 
              />
            ))}
          </div>
          <span style={{ color: passwordScore < 2 ? 'var(--danger)' : passwordScore < 3 ? 'var(--warning)' : 'var(--success)' }}>
            {passwordScore < 2 ? 'Słabe (min. 12 znaków, duża litera, cyfra, znak specjalny)' : passwordScore < 3 ? 'Średnie' : 'Silne'}
          </span>
        </div>
      )}

      <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '16px' }}>
        Resetuj hasło
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

export default ResetPasswordForm;
