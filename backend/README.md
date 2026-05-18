# Giełda Backend API

Backend dla platformy inwestycyjnej Giełda zbudowany w FastAPI.

## 🚀 Szybki start

```bash
# Instalacja zależności
pip install -r requirements.txt

# Uruchomienie serwera deweloperskiego
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API Docs
# http://localhost:8000/docs
```

## 📦 Dependencje

- **FastAPI** - Framework webowy
- **SQLAlchemy** (async) - ORM
- **PostgreSQL** (asyncpg) - Baza danych
- **PyJWT** - Tokeny JWT
- **PyOTP** - 2FA TOTP
- **Argon2-cffi** - Hashowanie haseł
- **httpx** - Klient HTTP (Binance API)
- **zxcvbn** - Sprawdzanie siły haseł

## 📁 Struktura

```
backend/
├── app/
│   ├── api/              # Endpointy API
│   │   ├── auth.py      # Rejestracja, logowanie, 2FA
│   │   ├── market.py    # Dane rynkowe
│   │   ├── orders.py    # Zlecenia SL/TP
│   │   ├── trading.py   # Handel (market buy/sell)
│   │   ├── portfolio.py # Portfel użytkownika
│   │   ├── transactions.py # Historia transakcji
│   │   └── admin.py    # Panel administratora
│   ├── core/            # Konfiguracja
│   │   ├── config.py    # Zmienne środowiskowe
│   │   ├── security.py  # JWT, hashowanie, 2FA
│   │   ├── database.py  # Połączenie z bazą
│   │   └── csrf.py     # Ochrona CSRF
│   ├── models/          # Modele bazy danych
│   │   ├── user.py
│   │   ├── wallet.py
│   │   ├── order.py
│   │   └── transaction.py
│   └── services/        # Logika biznesowa
│       ├── market_data.py  # Integracja z Binance
│       └── order_engine.py # Silnik zleceń
├── tests/              # Testy jednostkowe
├── Dockerfile
└── requirements.txt
```

## 🔧 Konfiguracja

Plik `.env` w katalogu `backend/`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/gielda
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
BINANCE_MODE=demo
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
TRACKED_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT
TRADING_FEE_RATE=0.001
```

## 🧪 Testy

```bash
# Uruchomienie testów z pokryciem
pytest --cov=app --cov-report=html --cov-fail-under=75

# Raport HTML: htmlcov/index.html
```

## 📊 API Endpoints

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/api/auth/register-init` | POST | Inicjalizacja rejestracji |
| `/api/auth/register-verify` | POST | Weryfikacja 2FA i utworzenie konta |
| `/api/auth/login` | POST | Logowanie (krok 1) |
| `/api/auth/verify-2fa` | POST | Weryfikacja 2FA (krok 2) |
| `/api/auth/me` | GET | Dane zalogowanego użytkownika |
| `/api/market/prices` | GET | Aktualne ceny |
| `/api/market/status` | GET | Status API |
| `/api/orders/` | GET | Lista zleceń |
| `/api/orders/` | POST | Utworzenie zlecenia |
| `/api/orders/{id}` | DELETE | Anulowanie zlecenia |
| `/api/portfolio/` | GET | Portfel |
| `/api/portfolio/deposit` | POST | Wpłata |
| `/api/transactions/` | GET | Historia transakcji |
| `/api/trading/buy` | POST | Kupno (market) |
| `/api/trading/market-sell` | POST | Sprzedaż (market) |
| `/api/admin/*` | * | Panel administratora |

## 🔒 Bezpieczeństwo

- **JWT** + **2FA (TOTP)** obowiązkowe
- **CSRF Protection** (Double Submit Cookie)
- **Argon2** do hashowania haseł
- **Zxcvbn** - sprawdzanie siły haseł
- **HaveIBeenPwned API** - sprawdzanie wycieków
- **Account Lockout** - blokada po 5 nieudanych próbach
- **CORS** skonfigurowane
- **SQL Injection** - zapobieganie (SQLAlchemy ORM)

## 🐳 Docker

```bash
# Budowanie obrazu
docker build -t gielda-backend .

# Uruchomienie kontenera
docker run -p 8000:8000 --env-file .env gielda-backend
```

## 📝 Migracje bazy danych

```bash
# Dodanie kolumny is_admin
python migrate_admin.py

# Tworzenie tabel (automatycznie przy starcie)
# app.main startup_event
```
