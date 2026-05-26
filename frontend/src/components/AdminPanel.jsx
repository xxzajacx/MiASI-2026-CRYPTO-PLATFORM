import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const AdminPanel = ({ token }) => {
  const [users, setUsers] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('users');
  const [csrfToken, setCsrfToken] = useState('');
  const [txSearch, setTxSearch] = useState('');

  // Sorting state
  const [userSort, setUserSort] = useState({ key: 'id', direction: 'asc' });
  const [txSort, setTxSort] = useState({ key: 'created_at', direction: 'desc' });

  useEffect(() => {
    const cookies = document.cookie.split(';');
    const csrfCookie = cookies.find(c => c.trim().startsWith('csrf_token='));
    if (csrfCookie) {
      setCsrfToken(csrfCookie.split('=')[1]);
    }
  }, []);

  const getHeaders = () => ({
    'Authorization': `Bearer ${token}`,
    'X-CSRF-TOKEN': csrfToken
  });

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_URL}/admin/users`, { headers: getHeaders() });
      setUsers(response.data);
    } catch (err) {
      setError('Failed to fetch users: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const fetchTransactions = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_URL}/admin/transactions`, { headers: getHeaders() });
      setTransactions(response.data);
    } catch (err) {
      setError('Failed to fetch transactions: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_URL}/admin/stats`, { headers: getHeaders() });
      setStats(response.data);
    } catch (err) {
      setError('Failed to fetch stats: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const blockUser = async (userId) => {
    const daysInput = window.prompt(
      'Na ile dni zablokować konto?\n\n' +
      '• Wpisz liczbę dni (np. 7 = tydzień)\n' +
      '• Wpisz 0 = permanentny ban\n' +
      '• Anuluj = rezygnacja',
      '1'
    );
    if (daysInput === null) return; // user cancelled
    const days = parseInt(daysInput, 10);
    if (isNaN(days) || days < 0) {
      alert('Nieprawidłowa wartość. Podaj liczbę >= 0.');
      return;
    }
    const confirmMsg = days === 0 
      ? 'Czy na pewno chcesz PERMANENTNIE zablokować to konto? Tej akcji nie da się cofnąć automatycznie.'
      : `Czy na pewno chcesz zablokować to konto na ${days} dni?`;
    if (!window.confirm(confirmMsg)) return;
    try {
      const res = await axios.post(`${API_URL}/admin/users/${userId}/block`, 
        { lock_duration_days: days },
        { headers: getHeaders() }
      );
      alert(res.data.message || 'Użytkownik został zablokowany');
      fetchUsers();
    } catch (err) {
      alert('Błąd: ' + (err.response?.data?.detail || err.message));
    }
  };

  const unblockUser = async (userId) => {
    try {
      await axios.post(`${API_URL}/admin/users/${userId}/unblock`, 
        {}, 
        { headers: getHeaders() }
      );
      alert('Użytkownik został odblokowany');
      fetchUsers();
    } catch (err) {
      alert('Błąd: ' + (err.response?.data?.detail || err.message));
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm('Czy na pewno chcesz bezpowrotnie usunąć tego użytkownika i całą jego historię? Tej akcji nie da się cofnąć!')) return;
    try {
      await axios.delete(`${API_URL}/admin/users/${userId}`, { headers: getHeaders() });
      alert('Użytkownik został pomyślnie usunięty');
      fetchUsers();
    } catch (err) {
      alert('Błąd: ' + (err.response?.data?.detail || err.message));
    }
  };

  const resetPassword = async (userId) => {
    const newPassword = window.prompt('Wpisz nowe hasło dla użytkownika:');
    if (!newPassword) return;
    if (newPassword.length < 12) {
      alert('Hasło musi mieć co najmniej 12 znaków!');
      return;
    }
    try {
      await axios.post(`${API_URL}/admin/users/${userId}/reset-password`, 
        { new_password: newPassword }, 
        { headers: getHeaders() }
      );
      alert('Hasło zostało pomyślnie zresetowane');
    } catch (err) {
      alert('Błąd resetowania hasła: ' + (err.response?.data?.detail || err.message));
    }
  };

  useEffect(() => {
    if (activeTab === 'users') fetchUsers();
    else if (activeTab === 'transactions') fetchTransactions();
    else if (activeTab === 'stats') fetchStats();
  }, [activeTab]);

  // Sorting logic
  const handleSortUsers = (key) => {
    let direction = 'asc';
    if (userSort.key === key && userSort.direction === 'asc') direction = 'desc';
    setUserSort({ key, direction });
  };

  const sortedUsers = useMemo(() => {
    let sortable = [...users];
    sortable.sort((a, b) => {
      if (a[userSort.key] < b[userSort.key]) return userSort.direction === 'asc' ? -1 : 1;
      if (a[userSort.key] > b[userSort.key]) return userSort.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sortable;
  }, [users, userSort]);

  const handleSortTx = (key) => {
    let direction = 'asc';
    if (txSort.key === key && txSort.direction === 'asc') direction = 'desc';
    setTxSort({ key, direction });
  };

  const sortedTx = useMemo(() => {
    // 1. Filter
    let filtered = transactions;
    if (txSearch) {
      const lowerSearch = txSearch.toLowerCase();
      filtered = transactions.filter(tx => 
        tx.username.toLowerCase().includes(lowerSearch) || 
        tx.type.toLowerCase().includes(lowerSearch) ||
        tx.asset.toLowerCase().includes(lowerSearch)
      );
    }
    
    // 2. Sort
    let sortable = [...filtered];
    sortable.sort((a, b) => {
      if (a[txSort.key] < b[txSort.key]) return txSort.direction === 'asc' ? -1 : 1;
      if (a[txSort.key] > b[txSort.key]) return txSort.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sortable;
  }, [transactions, txSort, txSearch]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {error && <div style={{ color: 'var(--danger)', background: 'rgba(239, 68, 68, 0.1)', padding: '12px', borderRadius: '8px' }}>{error}</div>}
      
      <div style={{ display: 'flex', gap: '12px', borderBottom: '1px solid var(--glass-border)', paddingBottom: '16px' }}>
        <button className={`btn ${activeTab === 'users' ? 'btn-primary' : ''}`} onClick={() => setActiveTab('users')}>
          Użytkownicy
        </button>
        <button className={`btn ${activeTab === 'transactions' ? 'btn-primary' : ''}`} onClick={() => setActiveTab('transactions')}>
          Transakcje
        </button>
        <button className={`btn ${activeTab === 'stats' ? 'btn-primary' : ''}`} onClick={() => setActiveTab('stats')}>
          Statystyki
        </button>
      </div>

      {loading && <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>Pobieranie danych...</div>}

      {activeTab === 'users' && !loading && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ cursor: 'pointer', padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }} onClick={() => handleSortUsers('id')}>
                  ID {userSort.key === 'id' ? (userSort.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th style={{ cursor: 'pointer', padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }} onClick={() => handleSortUsers('username')}>
                  Username {userSort.key === 'username' ? (userSort.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th style={{ cursor: 'pointer', padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }} onClick={() => handleSortUsers('first_name')}>
                  Imię {userSort.key === 'first_name' ? (userSort.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th style={{ cursor: 'pointer', padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }} onClick={() => handleSortUsers('last_name')}>
                  Nazwisko {userSort.key === 'last_name' ? (userSort.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }}>Status</th>
                <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }}>Akcje</th>
              </tr>
            </thead>
            <tbody>
              {sortedUsers.map(user => (
                <tr key={user.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td style={{ padding: '12px' }}>{user.id}</td>
                  <td style={{ padding: '12px' }}>{user.username}</td>
                  <td style={{ padding: '12px' }}>{user.first_name}</td>
                  <td style={{ padding: '12px' }}>{user.last_name}</td>
                  <td style={{ padding: '12px', color: user.is_active ? 'var(--success)' : 'var(--danger)' }}>
                    {user.is_active ? 'Aktywny' : 'Zablokowany'}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      {user.is_active ? (
                        <button onClick={() => blockUser(user.id)} className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '12px', background: 'var(--accent)', boxShadow: 'none' }}>
                          Zablokuj
                        </button>
                      ) : (
                        <button onClick={() => unblockUser(user.id)} className="btn btn-success" style={{ padding: '6px 12px', fontSize: '12px', boxShadow: 'none' }}>
                          Odblokuj
                        </button>
                      )}
                      <button onClick={() => resetPassword(user.id)} className="btn" style={{ padding: '6px 12px', fontSize: '12px', color: 'var(--primary)', borderColor: 'var(--primary-glow)', boxShadow: 'none' }}>
                        Resetuj Hasło
                      </button>
                      <button onClick={() => deleteUser(user.id)} className="btn btn-danger" style={{ padding: '6px 12px', fontSize: '12px', boxShadow: 'none' }}>
                        Usuń
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {sortedUsers.length === 0 && (
                <tr><td colSpan="6" style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>Brak użytkowników</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'transactions' && !loading && (
        <div style={{ overflowX: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <input 
              type="text" 
              className="input-field" 
              style={{ width: '300px' }}
              placeholder="Filtruj (użytkownik, typ, aktywo)..." 
              value={txSearch}
              onChange={(e) => setTxSearch(e.target.value)}
            />
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ cursor: 'pointer', padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }} onClick={() => handleSortTx('id')}>
                  ID {txSort.key === 'id' ? (txSort.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th style={{ cursor: 'pointer', padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }} onClick={() => handleSortTx('username')}>
                  Użytkownik {txSort.key === 'username' ? (txSort.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th style={{ cursor: 'pointer', padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }} onClick={() => handleSortTx('type')}>
                  Typ {txSort.key === 'type' ? (txSort.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th style={{ cursor: 'pointer', padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }} onClick={() => handleSortTx('amount')}>
                  Ilość {txSort.key === 'amount' ? (txSort.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }}>Aktywo</th>
                <th style={{ cursor: 'pointer', padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }} onClick={() => handleSortTx('price')}>
                  Cena {txSort.key === 'price' ? (txSort.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th style={{ cursor: 'pointer', padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }} onClick={() => handleSortTx('created_at')}>
                  Data {txSort.key === 'created_at' ? (txSort.direction === 'asc' ? '↑' : '↓') : ''}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedTx.map(tx => (
                <tr key={tx.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td style={{ padding: '12px' }}>{tx.id}</td>
                  <td style={{ padding: '12px' }}>{tx.username}</td>
                  <td style={{ padding: '12px', color: tx.type === 'BUY' || tx.type === 'DEPOSIT' ? 'var(--success)' : 'var(--danger)' }}>
                    {tx.type === 'BUY' ? 'Kupno' : tx.type === 'SELL' ? 'Sprzedaż' : tx.type === 'DEPOSIT' ? 'Wpłata' : tx.type}
                  </td>
                  <td style={{ padding: '12px' }}>{tx.amount}</td>
                  <td style={{ padding: '12px' }}>{tx.asset}</td>
                  <td style={{ padding: '12px' }}>{tx.price !== null ? tx.price : '-'}</td>
                  <td style={{ padding: '12px', whiteSpace: 'nowrap' }}>{new Date(tx.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {sortedTx.length === 0 && (
                <tr><td colSpan="7" style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>Brak transakcji</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'stats' && !loading && stats && (
        <div className="grid grid-cols-2" style={{ gap: '20px' }}>
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h4 style={{ color: 'var(--text-muted)', marginBottom: '8px', fontSize: '14px' }}>Wszyscy użytkownicy</h4>
            <div style={{ fontSize: '28px', fontWeight: 'bold' }}>{stats.total_users}</div>
          </div>
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h4 style={{ color: 'var(--text-muted)', marginBottom: '8px', fontSize: '14px' }}>Aktywni użytkownicy</h4>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--success)' }}>{stats.active_users}</div>
          </div>
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h4 style={{ color: 'var(--text-muted)', marginBottom: '8px', fontSize: '14px' }}>Wszystkie transakcje</h4>
            <div style={{ fontSize: '28px', fontWeight: 'bold' }}>{stats.total_transactions}</div>
          </div>
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h4 style={{ color: 'var(--text-muted)', marginBottom: '8px', fontSize: '14px' }}>Łączna wartość portfeli</h4>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--primary)' }}>{stats.total_wallet_value?.toFixed(2)} USDT</div>
          </div>
          
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h4 style={{ color: 'var(--text-muted)', marginBottom: '8px', fontSize: '14px' }}>Portfele SPOT</h4>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--success)' }}>{stats.spot_wallet_value?.toFixed(2) || '0.00'} USDT</div>
          </div>
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h4 style={{ color: 'var(--text-muted)', marginBottom: '8px', fontSize: '14px' }}>Portfele FUTURES</h4>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--accent)' }}>{stats.futures_wallet_value?.toFixed(2) || '0.00'} USDT</div>
          </div>
          
          <div className="glass-panel" style={{ gridColumn: 'span 2', padding: '20px' }}>
            <h4 style={{ color: 'var(--text-muted)', marginBottom: '16px', fontSize: '14px' }}>Zlecenia wg statusu</h4>
            <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
              {Object.entries(stats.orders_by_status || {}).map(([status, count]) => (
                <div key={status} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ 
                    width: '10px', height: '10px', borderRadius: '50%',
                    background: status === 'COMPLETED' ? 'var(--success)' : status === 'CANCELLED' ? 'var(--danger)' : 'var(--accent)'
                  }}></div>
                  <span>
                    {status === 'COMPLETED' ? 'Wykonane' : status === 'CANCELLED' ? 'Anulowane' : status === 'ACTIVE' ? 'Aktywne' : status === 'FAILED' ? 'Błąd/Przerwane' : status}: <strong>{count}</strong>
                  </span>
                </div>
              ))}
              {Object.keys(stats.orders_by_status || {}).length === 0 && (
                <span style={{ color: 'var(--text-muted)' }}>Brak zleceń</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPanel;
