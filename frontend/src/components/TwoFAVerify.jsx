import { useState } from 'react';

const TwoFAVerify = ({ totpCode, setTotpCode, errorMsg, handle2FA, setStage, tempToken }) => {
  return (
    <form onSubmit={handle2FA} className="flex-column animate-fade-in">
      <p style={{ fontSize: '14px', marginBottom: '8px' }}>
        Wpisz kod z Google Authenticator (TOTP)
      </p>
      <input 
        type="text" 
        placeholder="000 000" 
        className="input-field" 
        value={totpCode} 
        onChange={e => setTotpCode(e.target.value)} 
        style={{ letterSpacing: '4px', textAlign: 'center', fontSize: '20px' }} 
        required 
        minLength={6} 
        maxLength={6} 
      />
      <button type="submit" className="btn btn-success" style={{ width: '100%', marginTop: '8px' }}>
        Weryfikuj
      </button>
      <button 
        type="button" 
        className="btn" 
        style={{ marginTop: '8px' }} 
        onClick={() => setStage('LOGIN')}
      >
        Wróć
      </button>
    </form>
  );
};

export default TwoFAVerify;
