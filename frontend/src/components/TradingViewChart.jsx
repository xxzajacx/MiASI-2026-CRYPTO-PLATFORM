import { useEffect, useRef } from 'react';

/**
 * TradingViewChart component.
 * Embeds TradingView's Advanced Chart widget for the selected trading pair.
 *
 * @param {string} symbol - Trading pair symbol, e.g. "BTCUSDT"
 */
const TradingViewChart = ({ symbol = 'BTCUSDT' }) => {
  const containerRef = useRef(null);

  // Map internal symbol names to TradingView format
  const tvSymbol = `BINANCE:${symbol}`;

  useEffect(() => {
    if (!containerRef.current) return;

    // Clear previous widget instance
    containerRef.current.innerHTML = '';

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: tvSymbol,
      interval: '15',
      timezone: 'Europe/Warsaw',
      theme: 'dark',
      style: '1',
      locale: 'pl',
      allow_symbol_change: false,
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: false,
      calendar: false,
      support_host: 'https://www.tradingview.com',
      backgroundColor: 'rgba(15, 15, 25, 1)',
      gridColor: 'rgba(255, 255, 255, 0.04)',
    });

    containerRef.current.appendChild(script);

    // Cleanup on unmount or symbol change
    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [tvSymbol]);

  return (
    <div
      className="glass-panel"
      style={{ gridColumn: 'span 2', minHeight: '480px', padding: 0, overflow: 'hidden' }}
    >
      <div
        className="tradingview-widget-container"
        ref={containerRef}
        style={{ width: '100%', height: '100%', minHeight: '480px' }}
      />
    </div>
  );
};

export default TradingViewChart;
