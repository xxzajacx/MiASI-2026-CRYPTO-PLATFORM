# Giełda - Platforma Inwestycyjna

Uniwersalna platforma inwestycyjna do zarządzania portfelem aktywów z automatycznymi zleceniami warunkowymi (Stop-Loss, Take-Profit).

## Spis treści

- [Wymagania](#wymagania)
- [Technologie](#technologie)
- [Instalacja](#instalacja)
- [Konfiguracja](#konfiguracja)
- [Uruchomienie](#uruchomienie)
- [Testy](#testy)
- [Dokumentacja API](#dokumentacja-api)
- [Struktura projektu](#struktura-projektu)
- [Funkcjonalności](#funkcjonalności)

## Wymagania

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Docker (opcjonalnie)

## Technologie

### Backend
- **Framework:** FastAPI
- **Baza danych:** PostgreSQL z SQLAlchemy (async)
- **Uwierzytelnianie:** JWT + 2FA (TOTP)
- **API:** Binance Demo API

### Frontend
- **Framework:** React (Vite)
- **Wykresy:** TradingView Widget
- **HTTP Client:** Axios

### Infrastruktura
- **Konteneryzacja:** Docker + Docker Compose
- **Analiza kodu:** Pylint, Flake8
- **Testy:** Pytest + Pytest-cov

## Instalacja

### 1. Klonowanie repozytorium
```bash
git clone <repo-url>
cd Gielda
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Frontend
```bash
cd frontend
npm install
```

### 4. Baza danych
```bash
# Utworzenie bazy danych PostgreSQL
createdb gielda

# Lub użyj Dockera:
docker run -d \
  --name gielda_db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=gielda \
  -p 5432:5432 \
  postgres:15-alpine
```

## Konfiguracja

Utworz plik `.env` w katalogu `backend/`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/gielda
SECRET_KEY=your-super-secret-key-change-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
BINANCE_MODE=demo
BINANCE_API_KEY=your_binance_demo_api_key
BINANCE_SECRET_KEY=your_binance_demo_secret_key
TRACKED_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT
TRADING_FEE_RATE=0.001
```

### Generowanie klucza SECRET_KEY:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### Rejestracja admina:
```bash
cd backend
python make_admin.py username
```

## Uruchomienie

### Opcja 1: Lokalnie

**Backend:**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### Opcja 2: Docker

```bash
docker-compose up -d --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Dokumentacja API (Swagger): http://localhost:8000/docs

## Testy

### Backend
```bash
cd backend
pytest --cov=app --cov-report=html --cov-fail-under=75
```

Raport pokrycia znajduje się w `backend/htmlcov/index.html`.

### Frontend
```bash
cd frontend
npm test
```

## Dokumentacja API

Pełna dokumentacja API jest dostępna automatycznie pod adresem:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Główne endpointy:

#### Auth
- `POST /api/auth/register-init` - Inicjalizacja rejestracji
- `POST /api/auth/register-verify` - Weryfikacja 2FA i utworzenie konta
- `POST /api/auth/login` - Logowanie (krok 1)
- `POST /api/auth/verify-2fa` - Weryfikacja 2FA (krok 2)

#### Market
- `GET /api/market/prices` - Pobieranie aktualnych cen
- `GET /api/market/status` - Status połączenia z API

#### Orders
- `GET /api/orders/` - Lista zleceń
- `POST /api/orders/` - Utworzenie zlecenia SL/TP
- `DELETE /api/orders/{id}` - Anulowanie zlecenia

#### Portfolio
- `GET /api/portfolio/` - Portfel użytkownika
- `POST /api/portfolio/deposit` - Wpłata środków

#### Admin
- `GET /api/admin/users` - Lista użytkowników
- `POST /api/admin/users/{id}/block` - Blokowanie użytkownika
- `POST /api/admin/users/{id}/unblock` - Odblokowywanie
- `GET /api/admin/stats` - Statystyki systemu

## Struktura projektu

```
Gielda/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpointy API
│   │   ├── core/        # Konfiguracja, security
│   │   ├── models/      # Modele SQLAlchemy
│   │   └── services/    # Logika biznesowa
│   ├── tests/           # Testy jednostkowe
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/  # Komponenty React
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Funkcjonalności

### Zaimplementowane:

**Bezpieczna autoryzacja i uwierzytelnianie**
- Rejestracja z weryfikacją siły hasła (zxcvbn)
- 2FA (TOTP) z Google Authenticator
- JWT tokens z CSRF protection
- Blokada konta po 5 nieudanych próbach

**Zarządzanie portfelem**
- Wirtualny portfel inwestycyjny
- Wpłaty środków
- Podgląd balansu (dostępne/zablokowane)

**Zlecenia warunkowe**
- Stop-Loss (zabezpieczenie przed spadkami)
- Take-Profit (realizacja zysku)
- Automatyczna egzekucja
- Blokowanie aktywów przy składaniu zlecenia

**Integracja z rynkiem**
- Cykliczne pobieranie cen (co 5 sekund)
- Integracja z Binance Demo API
- Obsługa błędów (timeout, brak połączenia)

**Panel administratora**
- Zarządzanie użytkownikami (blokowanie/odblokowywanie)
- Resetowanie haseł
- Monitorowanie transakcji
- Statystyki systemu

**Wymagania niefunkcjonalne**
- Docker + konteneryzacja
- Transakcje bazodanowe (rollback na błędy)
- Python + React + PostgreSQL
- CSRF protection
- Statyczna analiza kodu (Pylint, Flake8)
- Testy jednostkowe (min. 75% pokrycia)

## Proces realizacji zleceń warunkowych (Stop-Loss / Take-Profit)

Silnik zleceń (`app/services/order_engine.py`) działa w tle jako asynchroniczna pętla monitorująca rynki, realizując transakcje automatycznie w bezpiecznym 5-etapowym potoku (Operational Pipeline):

1. **Fetch (Pobieranie cen i zleceń)**
   - Cykliczne pobieranie aktualnych kursów aktywów (co 5 sekund przez API Binance lub wewnętrzny serwis symulacyjny).
   - Pobranie listy wszystkich aktywnych zleceń warunkowych (`ACTIVE`) z bazy danych w celu weryfikacji.

2. **Validate (Weryfikacja i Walidacja)**
   - Sprawdzenie poprawności zablokowanego balansu w portfelu użytkownika (`locked_balance`).
   - Obliczenie symulowanej prowizji transakcyjnej (0.5%). Jeśli koszty transakcji przewyższają szacowaną wartość sprzedaży, zlecenie jest natychmiast przerywane i oznaczane jako `FAILED`, aby uchronić użytkownika przed stratą kapitału.

3. **Check Conditions (Weryfikacja warunków aktywacji)**
   - Porównanie aktualnej ceny rynkowej z zadeklarowaną ceną aktywacji (`target_price`) na podstawie typu zlecenia i kierunku:
     - **Stop-Loss (Sprzedaż):** aktywacja gdy cena rynkowa $\le$ `target_price`.
     - **Take-Profit (Sprzedaż):** aktywacja gdy cena rynkowa $\ge$ `target_price`.
     - **Stop-Loss (Kupno):** aktywacja gdy cena rynkowa $\ge$ `target_price`.
     - **Take-Profit (Kupno):** aktywacja gdy cena rynkowa $\le$ `target_price`.

4. **Transactional Settlement (Rozliczenie transakcyjne z Rollback)**
   - Realizacja zlecenia na giełdzie Binance (przy skonfigurowanych kluczach API) lub wykonanie precyzyjnej symulacji lokalnej.
   - Aktualizacja portfeli w izolowanej transakcji bazodanowej: odblokowanie i pobranie aktywów z `locked_balance` użytkownika oraz uznanie odpowiedniego konta docelowego.
   - **Sprzątanie OCO (One-Cancels-the-Other):** Jeśli zlecenie należy do powiązanej grupy (np. jednoczesne wystawienie TP i SL), udane wykonanie jednego zlecenia automatycznie anuluje drugie (`CANCELLED`).
   - W przypadku jakiegokolwiek nieoczekiwanego błędu, system wykonuje bezpieczny `db.rollback()`, przywraca zablokowane środki na saldo główne użytkownika, a status zlecenia aktualizuje na `FAILED` w oddzielnej bezpiecznej sesji.

5. **Audit Log Creation (Utworzenie wpisu audytowego)**
   - Trwałe zapisanie pełnego dziennika operacji w tabeli `TransactionHistory` zawierającego: typ transakcji, wykonaną ilość, cenę rynkową, pobraną prowizję oraz status wykonania wraz ze szczegółowym komunikatem diagnostycznym.

## Bezpieczeństwo

- Hasła hashowane (Argon2)
- 2FA (TOTP) obowiązkowe
- CSRF protection
- Walidacja siły hasła (min. 12 znaków, zxcvbn)
- Sprawdzanie wycieków haseł (HaveIBeenPwned API)
- Weryfikacja wieku (min. 18 lat)
- Blokada konta po próbach brut-force

## Testy i Jakość

### Backend
- **Framework:** Pytest
- **Pokrycie:** min. 75%
- **Raporty:** HTML + terminal

### Analiza statyczna
- **Pylint** (pyproject.toml)
- **Flake8** (.flake8)
- **Max line length:** 120 znaków

## Licencja

Projekt edukacyjny - wszystkie prawa zastrzeżone.


