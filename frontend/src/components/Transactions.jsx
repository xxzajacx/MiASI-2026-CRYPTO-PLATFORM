import React, { useState } from 'react';

const Transactions = ({ history }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const totalPages = Math.ceil(history.length / itemsPerPage);
  
  const paginatedHistory = history.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const getStatusLabel = (status) => {
    switch (status) {
      case 'COMPLETED':
        return 'Wykonane';
      case 'FAILED':
        return 'Przerwane/Błąd';
      case 'PENDING':
        return 'Oczekujące';
      default:
        return status;
    }
  };

  const getTypeLabel = (type) => {
    switch (type) {
      case 'BUY':
        return 'Kupno';
      case 'SELL':
        return 'Sprzedaż';
      case 'DEPOSIT':
        return 'Wpłata';
      default:
        return type;
    }
  };

  return (
    <div className="glass-panel" style={{ gridColumn: 'span 3' }}>
      <h3 style={{ marginBottom: '16px', color: 'var(--text-muted)' }}>Historia Operacji</h3>
      {history.length === 0 ? (
        <p className="text-muted">Brak historii.</p>
      ) : (
        <>
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
              {paginatedHistory.map(h => (
                <tr key={h.id}>
                  <td style={{ fontSize: '12px' }}>{new Date(h.created_at).toLocaleString()}</td>
                  <td style={{ 
                    fontWeight: 600, 
                    color: h.type === 'BUY' || h.type === 'DEPOSIT' ? 'var(--success)' : 'var(--danger)' 
                  }}>
                    {getTypeLabel(h.type)}
                  </td>
                  <td>{h.asset}</td>
                  <td>{h.amount}</td>
                  <td>{h.price ? `$${h.price.toFixed(2)}` : '-'}</td>
                  <td>
                    <span className={h.status === 'COMPLETED' ? "text-success" : "text-danger"}>
                      {getStatusLabel(h.status)}
                    </span>
                  </td>
                  <td className="text-muted" style={{ fontSize: '12px' }}>{h.log_message}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px', marginTop: '16px' }}>
              <button 
                className="btn btn-outline" 
                disabled={currentPage === 1} 
                onClick={() => setCurrentPage(p => p - 1)}
                style={{ padding: '4px 12px', fontSize: '12px' }}
              >
                Poprzednia
              </button>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Strona {currentPage} z {totalPages}
              </span>
              <button 
                className="btn btn-outline" 
                disabled={currentPage === totalPages} 
                onClick={() => setCurrentPage(p => p + 1)}
                style={{ padding: '4px 12px', fontSize: '12px' }}
              >
                Następna
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Transactions;
