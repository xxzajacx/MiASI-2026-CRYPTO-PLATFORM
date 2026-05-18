# Giełda Frontend

Interfejs użytkownika dla platformy inwestycyjnej Giełda zbudowany w React + Vite.

## 🚀 Szybki start

```bash
# Instalacja zależności
npm install

# Uruchomienie serwera deweloperskiego
npm run dev

# http://localhost:5173
```

## 📦 Dependencje

- **React 18** - Biblioteka UI
- **Axios** - Klient HTTP
- **qrcode.react** - Generowanie kodów QR (2FA)
- **zxcvbn** - Sprawdzanie siły haseł
- **TradingView Widget** - Wykresy giełdowe

## 📁 Struktura

```
frontend/
├── src/
│   ├── components/        # Komponenty React
│   │   ├── AdminPanel.jsx
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Dashboard.jsx
│   │   ├── MarketPrices.jsx
│   │   ├── Portfolio.jsx
│   │   ├── Orders.jsx
│   │   └── Transactions.jsx
│   ├── App.jsx           # Główny komponent
│   ├── main.jsx          # Punkt wejściowy
│   ├── index.css         # Style globalne
│   └── App.css          # Style komponentów
├── public/
├── Dockerfile
├── nginx.conf
├── vite.config.js
└── package.json
```

## 🔧 Konfiguracja

Plik `.env`:

```env
VITE_API_URL=http://localhost:8000/api
```

## 🏗️ Budowanie

```bash
# Budowanie produkcyjne
npm run build

# Podgląd budowania
npm run preview
```

## 🐳 Docker

```bash
# Budowanie obrazu
docker build -t gielda-frontend .

# Uruchomienie kontenera
docker run -p 80:80 gielda-frontend
```

## ✨ Funkcjonalności

- 🔐 **Logowanie i rejestracja** z 2FA (Google Authenticator)
- 📈 **Wykresy giełdowe** (TradingView)
- 💰 **Zarządzanie portfelem** (wpłaty, podgląd balansu)
- 🛡️ **Zlecenia ochronne** (Stop-Loss, Take-Profit)
- 📊 **Historia transakcji**
- 👥 **Panel administratora** (dla uprawnionych użytkowników)
- 🔒 **CSRF Protection**

## 🎨 Style

Aplikacja używa nowoczesnego, ciemnego motywu z efektami "glassmorphism". Kolory:

- `--bg-primary`: #0a0a1a (tło)
- `--bg-card)`: rgba(255, 255, 255, 0.03) (karty)
- `--primary)`: #00d4aa (akcent)
- `--danger)`: #ff4757 (czerwony)
- `--success)`: #2ed573 (zielony)
