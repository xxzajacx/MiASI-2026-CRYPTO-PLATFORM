const Transactions = ({ history }) => {
  return (
    <div className="glass-panel" style={{ gridColumn: 'span 3' }}>
      <h3 style={{ marginBottom: '16px', color: 'var(--text-muted)' }}>Historia Operacji</h3>
      {history.length === 0 ? (
        <p className="text-muted">Brak historii.</p>
      ) : (
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
                <td style={{ 
                  fontWeight: 600, 
                  color: h.type === 'BUY' || h.type === 'DEPOSIT' ? 'var(--success)' : 'var(--danger)' 
                }}>
                  {h.type}
                </td>
                <td>{h.asset}</td>
                <td>{h.amount}</td>
                <td>{h.price ? `$${h.price.toFixed(2)}` : '-'}</td>
                <td>
                  <span className={h.status === 'COMPLETED' ? "text-success" : "text-danger"}>
                    {h.status}
                  </span>
                </td>
                <td className="text-muted" style={{ fontSize: '12px' }}>{h.log_message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default Transactions;
