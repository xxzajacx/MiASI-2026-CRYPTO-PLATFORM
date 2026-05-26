import { useState } from 'react';

const LoginForm = ({ username, setUsername, password, handlePasswordChange, errorMsg, handleLogin, setStage }) => {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <form onSubmit={handleLogin} className="flex-column">
      <input 
        type="text" 
        placeholder="Nazwa użytkownika" 
        className="input-field" 
        value={username} 
        onChange={e => setUsername(e.target.value)} 
        required 
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
            background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          {showPassword ? "Ukryj" : "Pokaż"}
        </button>
      </div>

      <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '16px' }}>
        Zaloguj się
      </button>
      <button 
        type="button" 
        className="btn" 
        style={{ marginTop: '8px' }} 
        onClick={() => setStage('REGISTER')}
      >
        Nie masz konta? Zarejestruj się
      </button>
      <button 
        type="button" 
        className="btn" 
        style={{ marginTop: '4px', fontSize: '12px', color: 'var(--text-muted)' }} 
        onClick={() => setStage('RESET_PASSWORD')}
      >
        Zapomniałeś hasła? Zmień za pomocą TOTP
      </button>
    </form>
  );
};

export default LoginForm;
