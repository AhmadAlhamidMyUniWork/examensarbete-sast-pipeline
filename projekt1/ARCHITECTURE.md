# Customer Management API – Teknisk dokumentation

---

## 1. Systemöversikt

Visar alla komponenter, protokoll och algoritmer på hög nivå.

```mermaid
graph TB
    Client(["👤 Klient\n(Browser / curl / app)"])

    subgraph Flask_API ["Flask REST API (HTTP/1.1)"]
        direction TB
        APP["app.py\nEntry point"]
        AUTH["auth.py\nBlueprint\n/register  /login"]
        CUST["customers.py\nBlueprint\nGET /customers"]
        EXT["external.py\nBlueprint\nGET /external"]
        MW["middleware.py\n@token_required"]
        CFG["config.py\nSECRET_KEY\nDB path\nTimeout"]
    end

    subgraph DB ["SQLite (fil på disk)"]
        T_USERS[("users\nid · username\npassword · created_at")]
        T_CUST[("customers\nid · name · email\nphone · created_at")]
    end

    EXTERNAL_API(["🌐 Externt API\njsonplaceholder.typicode.com\n(HTTPS / REST)"])

    Client -- "HTTP POST JSON" --> AUTH
    Client -- "HTTP GET\nAuthorization: Bearer JWT" --> CUST
    Client -- "HTTP GET\nAuthorization: Bearer JWT" --> EXT

    AUTH -- "SQL INSERT / SELECT" --> T_USERS
    CUST -- "SQL SELECT" --> T_CUST
    MW -- "Verifierar token\nHS256 + SECRET_KEY" --> AUTH
    MW -- "Verifierar token\nHS256 + SECRET_KEY" --> CUST
    MW -- "Verifierar token\nHS256 + SECRET_KEY" --> EXT
    EXT -- "HTTPS GET\nrequests lib\ntimeout=5s" --> EXTERNAL_API

    APP --> AUTH
    APP --> CUST
    APP --> EXT
    CFG --> APP
```

---

## 2. ER-diagram – Databas

```mermaid
erDiagram
    USERS {
        INTEGER id PK
        TEXT    username  "UNIQUE NOT NULL"
        TEXT    password  "pbkdf2:sha256 hash"
        TEXT    created_at "ISO-8601 UTC"
    }

    CUSTOMERS {
        INTEGER id PK
        TEXT    name       "NOT NULL"
        TEXT    email      "UNIQUE NOT NULL"
        TEXT    phone      "nullable"
        TEXT    created_at "ISO-8601 UTC"
    }
```

---

## 3. Komponentdiagram (UML)

Visar modulernas beroenden.

```mermaid
graph LR
    app["app.py"] --> auth["auth.py"]
    app --> customers["customers.py"]
    app --> external["external.py"]

    auth --> database["database.py"]
    auth --> config["config.py"]

    customers --> database
    customers --> middleware["middleware.py"]

    external --> middleware
    external --> config

    middleware --> config

    database --> config

    style app      fill:#4A90D9,color:#fff
    style middleware fill:#E67E22,color:#fff
    style config   fill:#27AE60,color:#fff
    style database fill:#8E44AD,color:#fff
```

---

## 4. Sekvensdiagram – POST /register

```mermaid
sequenceDiagram
    actor Client
    participant API as auth.py
    participant DB  as database.py
    participant SQLite

    Client->>API: POST /register\n{"username": "alice", "password": "secret"}
    API->>API: Validera att username\noch password finns

    alt användarnamn saknas / tomt
        API-->>Client: 400 Bad Request\n{"error": "username och password krävs"}
    end

    API->>DB: get_user_by_username("alice")
    DB->>SQLite: SELECT * FROM users WHERE username=?
    SQLite-->>DB: None
    DB-->>API: None

    alt användarnamn redan taget
        API-->>Client: 409 Conflict\n{"error": "användarnamnet är redan taget"}
    end

    API->>DB: create_user("alice", "secret")
    DB->>DB: generate_password_hash("secret")\n→ pbkdf2:sha256:...
    DB->>SQLite: INSERT INTO users (username, password, created_at)
    SQLite-->>DB: lastrowid = 1
    DB-->>API: 1

    API-->>Client: 201 Created\n{"message": "användare skapad"}
```

---

## 5. Sekvensdiagram – POST /login + JWT-utfärdning

```mermaid
sequenceDiagram
    actor Client
    participant API  as auth.py
    participant DB   as database.py
    participant SQLite
    participant JWT  as PyJWT (HS256)

    Client->>API: POST /login\n{"username": "alice", "password": "secret"}
    API->>DB: get_user_by_username("alice")
    DB->>SQLite: SELECT * FROM users WHERE username=?
    SQLite-->>DB: {id:1, username:"alice", password:"pbkdf2:..."}
    DB-->>API: user dict

    API->>API: check_password_hash(user.password, "secret")

    alt lösenord fel eller användare saknas
        API-->>Client: 401 Unauthorized\n{"error": "felaktigt användarnamn eller lösenord"}
    end

    API->>JWT: encode({sub:1, username:"alice",\niat:now, exp:now+24h}, SECRET_KEY, HS256)
    JWT-->>API: "eyJhbGci..."

    API-->>Client: 200 OK\n{"token": "eyJhbGci..."}
```

---

## 6. Sekvensdiagram – GET /customers (skyddad endpoint)

```mermaid
sequenceDiagram
    actor Client
    participant MW  as middleware.py\n@token_required
    participant API as customers.py
    participant DB  as database.py
    participant SQLite

    Client->>MW: GET /customers\nAuthorization: Bearer eyJhbGci...

    alt Authorization-header saknas
        MW-->>Client: 401 {"error": "token saknas"}
    end

    MW->>MW: jwt.decode(token, SECRET_KEY, HS256)

    alt token ogiltig / manipulerad
        MW-->>Client: 401 {"error": "ogiltig token"}
    end

    alt token utgången (exp passerat)
        MW-->>Client: 401 {"error": "token har gått ut"}
    end

    MW->>MW: g.current_user = {id, username}
    MW->>API: Anrop vidarebefordras

    API->>DB: get_all_customers()
    DB->>SQLite: SELECT id,name,email,phone,created_at\nFROM customers ORDER BY id
    SQLite-->>DB: [row, row, ...]
    DB-->>API: [{...}, {...}]

    API-->>Client: 200 OK\n{"customers": [{...}, ...]}
```

---

## 7. Sekvensdiagram – GET /external (proxy + felhantering)

```mermaid
sequenceDiagram
    actor Client
    participant MW  as middleware.py
    participant API as external.py
    participant EXT as Externt API\njsonplaceholder

    Client->>MW: GET /external\nAuthorization: Bearer <token>
    MW->>MW: Validera JWT (se diagram 6)
    MW->>API: Vidarebefordra

    API->>EXT: HTTPS GET /users\ntimeout=5s

    alt Lyckat svar
        EXT-->>API: 200 OK [{"id":1,"name":"..."}, ...]
        API-->>Client: 200 OK\n{"source": "https://...", "data": [...]}
    else Timeout (>5s)
        EXT-->>API: (ingen respons)
        API-->>Client: 504 Gateway Timeout\n{"error": "extern tjänst svarade inte i tid"}
    else HTTP-fel (4xx/5xx)
        EXT-->>API: 404 / 500
        API-->>Client: 502 Bad Gateway\n{"error": "extern tjänst returnerade fel: 404"}
    else Nätverksfel / DNS
        EXT-->>API: ConnectionError
        API-->>Client: 502 Bad Gateway\n{"error": "kunde inte ansluta till extern tjänst"}
    end
```

---

## 8. Tillståndsdiagram – JWT-tokens livscykel

```mermaid
stateDiagram-v2
    [*] --> Obefintlig

    Obefintlig --> Utfärdad : POST /login\n(korrekt credentials)

    Utfärdad --> Giltig : jwt.decode() OK\nexp > now

    Giltig --> Använd : Skyddad endpoint\nbesvaras med 200

    Använd --> Giltig : Nästa anrop\n(inom giltighetstid)

    Giltig --> Utgången : exp <= now

    Utgången --> [*] : Klienten måste\nlogga in igen

    Utfärdad --> Ogiltig : Manipulerad /\nfel SECRET_KEY

    Ogiltig --> [*] : 401 Unauthorized
```

---

## 9. Säkerhetsmodell – Sammanfattning

| Lager | Mekanism | Implementation |
|---|---|---|
| Lösenordslagring | PBKDF2-SHA256 + salt | `werkzeug.security.generate_password_hash` |
| Autentisering | JWT Bearer Token | `PyJWT`, algoritm `HS256` |
| Token-integritet | HMAC-signatur | `SECRET_KEY` i `config.py` |
| Token-utgång | `exp`-claim | `JWT_EXPIRATION_HOURS = 24` |
| SQL-injektion | Parametriserade queries | `sqlite3` med `?`-platshållare |
| Timeout-skydd | Request timeout | `EXTERNAL_API_TIMEOUT = 5s` |

---

## 10. Dataflöde – Storyboard

```
┌─────────────────────────────────────────────────────────────┐
│  Scen 1: Ny användare registrerar sig                       │
│                                                             │
│  [Klient] ──POST /register──► [Flask]                      │
│                                   │                         │
│                            Validering OK?                   │
│                            Hash lösenord                    │
│                            Spara i SQLite                   │
│                                   │                         │
│  [Klient] ◄── 201 "användare skapad" ──────────────────    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Scen 2: Användaren loggar in och får token                 │
│                                                             │
│  [Klient] ──POST /login──────► [Flask]                     │
│                                   │                         │
│                            Hämta user från DB               │
│                            Verifiera lösenord               │
│                            Generera JWT (24h)               │
│                                   │                         │
│  [Klient] ◄── 200 {"token": "eyJ..."} ─────────────────    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Scen 3: Hämta kunder med token                             │
│                                                             │
│  [Klient] ──GET /customers──► [@token_required]             │
│           Authorization:          │                         │
│           Bearer eyJ...       Dekoda JWT                    │
│                               Verifiera signatur            │
│                               Kontrollera exp               │
│                                   │                         │
│                              [customers.py]                 │
│                            SELECT FROM customers            │
│                                   │                         │
│  [Klient] ◄── 200 {"customers": [...]} ────────────────    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Scen 4: Proxyanrop till externt API                        │
│                                                             │
│  [Klient] ──GET /external────► [@token_required]            │
│                                   │                         │
│                              [external.py]                  │
│                            requests.get(url, timeout=5s)    │
│                                   │                         │
│                         ┌─────────▼──────────┐             │
│                         │  Externt API       │             │
│                         │  jsonplaceholder   │             │
│                         └─────────┬──────────┘             │
│                                   │                         │
│  [Klient] ◄── 200 {"data": [...]} ──────────────────────   │
└─────────────────────────────────────────────────────────────┘
```
