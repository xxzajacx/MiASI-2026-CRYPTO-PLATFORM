const Orders = ({ orders, prices, handleCancelOrder }) => {
  const activeOrders = orders.filter(o => o.status === 'ACTIVE');
  
  return (
    <div className="glass-panel" style={{ gridColumn: 'span 3' }}>
      <h3 style={{ color: 'var(--text-muted)', marginBottom: '16px' }}>Aktywne Zlecenia Ochronne (TP/SL)</h3>
      {activeOrders.length === 0 ? (
        <p className="text-muted">Brak oczekujących zleceń.</p>
      ) : (
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
              <th>Akcje</th>
            </tr>
          </thead>
          <tbody>
            {activeOrders.map(o => (
              <tr key={o.id}>
                <td style={{ fontWeight: 600 }}>{o.symbol}</td>
                <td>
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    background: o.order_type === 'STOP_LOSS' ? 'var(--danger-glow)' : 'var(--success-glow)',
                    color: o.order_type === 'STOP_LOSS' ? 'var(--danger)' : 'var(--success)'
                  }}>
                    {o.order_type === 'STOP_LOSS' ? 'Stop Loss' : 'Take Profit'}
                  </span>
                </td>
                <td style={{ color: o.side === 'BUY' ? 'var(--success)' : 'var(--danger)' }}>
                  {o.side === 'BUY' ? 'Kupno' : 'Sprzedaż'}
                </td>
                <td>{o.amount}</td>
                <td style={{ fontWeight: 600 }}>${o.target_price}</td>
                <td className={prices[o.symbol] > o.target_price ? 'text-success' : 'text-danger'}>
                  ${prices[o.symbol]?.toFixed(2) || '---'}
                </td>
                <td><span className="animate-pulse">Aktywne</span></td>
                <td>
                  <button 
                    className="btn" 
                    style={{ padding: '4px 12px', fontSize: '12px', color: 'var(--danger)', borderColor: 'var(--danger-glow)' }} 
                    onClick={() => handleCancelOrder(o.id)}
                  >
                    Anuluj
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default Orders;
