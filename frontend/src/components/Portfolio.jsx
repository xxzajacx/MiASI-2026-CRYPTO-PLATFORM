const Portfolio = ({ wallet, prices, setShowDepositModal }) => {
  return (
    <div className="glass-panel" style={{ gridColumn: 'span 3' }}>
      <div className="flex-between" style={{ marginBottom: '16px' }}>
        <h3 style={{ color: 'var(--text-muted)' }}>Mój Portfel</h3>
        <button className="btn btn-success" onClick={() => setShowDepositModal(true)}>+ Wpłać USDT</button>
      </div>
      
      {wallet.length === 0 ? (
        <p className="text-muted">Brak aktywów w portfelu. Skorzystaj z opcji "Wpłać USDT", aby zasilić konto symulacyjne.</p>
      ) : (
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
  );
};

export default Portfolio;
