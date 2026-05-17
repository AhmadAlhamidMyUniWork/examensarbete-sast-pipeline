# Task Management System — Arkitektur & Tekniska Detaljer

> Alla figurer är i **Mermaid-syntax** — renderas direkt i VS Code, GitHub, Obsidian m.fl.

---

## Innehållsförteckning

| # | Figur | Typ |
|---|-------|-----|
| 1 | Systemöversikt — komponenter, protokoll, algoritmer | Komponentdiagram |
| 2 | Databasschema — tabeller, kolumner, relationer | ER-diagram |
| 3 | Modulberoenden — intern pakestruktur | UML Komponentdiagram |
| 4 | POST /register — registreringsflöde | Sekvensdiagram |
| 5 | POST /login — autentisering + JWT-utfärdning | Sekvensdiagram |
| 6 | GET /tasks — rollbaserad åtkomst | Sekvensdiagram |
| 7 | PUT /tasks/{id} — uppdateringsflöde | Sekvensdiagram |
| 8 | GET /recommend — AI-anrop med fallback | Sekvensdiagram |
| 9 | JWT-tokens livscykel | Tillståndsdiagram |
| 10 | Tasks livscykel | Tillståndsdiagram |
| 11 | Säkerhetsmodell per lager | Tabell |
| 12 | Storyboard — 5 huvudscenarier | Storyboard |

---

## Figur 1 — Systemöversikt

Visar samtliga systemkomponenter, vilka protokoll de kommunicerar med och vilka
algoritmer/bibliotek som hanterar säkerhet och datapersistens.

```mermaid
graph TB
    subgraph CLIENT["🖥️  Klient (Browser)"]
        FE["index.html + Vanilla JS\n──────────────────\nfetch() API\nLocalStorage (JWT)"]
    end

    subgraph FASTAPI["⚡  FastAPI Backend (Python 3.11)"]
        MW["CORSMiddleware\nallow_origins=[*]"]
        AUTH["🔐 /register  /login\napp/api/auth.py"]
        TASKS["📋 /tasks  /tasks/{id}\napp/api/tasks.py"]
        REC["🤖 /recommend\napp/api/recommend.py"]
        DEPS["get_current_user()\nget_current_admin()\napp/api/deps.py"]
        SEC["app/core/security.py\n──────────────────\nJWT: HS256 / pyjwt 2.6\nPW:  PBKDF2-SHA256 / werkzeug 2.3\nTTL: 60 min"]
        CFG["app/core/config.py\n──────────────────\nSECRET_KEY (hardcoded)\nALGORITHM = HS256\nEXPIRE = 60 min"]
    end

    subgraph DB["🗄️  Datapersistens"]
        ORM["SQLAlchemy ORM 1.4\nSessionLocal / Base"]
        SQLITE["SQLite\ntasks.db"]
    end

    subgraph EXT["🌐  Extern tjänst (simulerad)"]
        EXTAPI["Mock AI API\nhttps://api.mock-ai-service.example.com\nrequests 2.28 · timeout 2s\nAuthorization: Bearer API_KEY"]
    end

    FE -- "HTTP/1.1 REST\nJSON payloads\nAuthorization: Bearer JWT" --> MW
    MW --> AUTH
    MW --> TASKS
    MW --> REC
    AUTH -- "hash / verify" --> SEC
    AUTH -- "encode / decode JWT" --> SEC
    TASKS -- "Depends(get_current_user)" --> DEPS
    REC  -- "Depends(get_current_user)" --> DEPS
    DEPS -- "decode_access_token()" --> SEC
    AUTH -- "CRUD" --> ORM
    TASKS -- "CRUD" --> ORM
    REC  -- "SELECT tasks" --> ORM
    ORM  -- "SQLite driver\ncheck_same_thread=False" --> SQLITE
    REC  -- "POST + API-nyckel\n(faller alltid tillbaka)" --> EXTAPI

    style CLIENT  fill:#eaf4fb,stroke:#2980b9
    style FASTAPI fill:#eafaf1,stroke:#27ae60
    style DB      fill:#fef9e7,stroke:#f39c12
    style EXT     fill:#fdedec,stroke:#e74c3c
```

---

## Figur 2 — Databasschema (ER-diagram)

Visar de två tabellerna med alla kolumner, datatyper, constraints och relationen däremellan.

```mermaid
erDiagram
    USERS {
        INTEGER id PK "AUTO INCREMENT"
        STRING  email UK "NOT NULL · INDEX"
        STRING  password   "NOT NULL · PBKDF2 hash"
        ENUM    role       "user | admin · DEFAULT user"
    }

    TASKS {
        INTEGER id          PK "AUTO INCREMENT"
        STRING  title          "NOT NULL · max 255"
        TEXT    description    "NULLABLE"
        DATE    due_date       "NULLABLE"
        ENUM    priority       "low | medium | high · DEFAULT medium"
        ENUM    status         "pending | in_progress | done · DEFAULT pending"
        INTEGER owner_id    FK "NOT NULL → USERS.id"
    }

    USERS ||--o{ TASKS : "äger (cascade delete)"
```

---

## Figur 3 — Modulberoenden

Visar hur paketen i `app/` beror på varandra och vad varje paket exporterar.

```mermaid
graph LR
    subgraph core["app/core"]
        CFG["config.py\nSECRET_KEY\nALGORITHM\nEXPIRE_MIN"]
        SEC["security.py\nhash_password()\nverify_password()\ncreate_access_token()\ndecode_access_token()\noauth2_scheme"]
    end

    subgraph db["app/db"]
        DBS["database.py\nengine\nSessionLocal\nBase\nget_db()\nraw SQL helpers"]
    end

    subgraph models["app/models"]
        UM["user.py\nUser · UserRole"]
        TM["task.py\nTask · TaskPriority · TaskStatus"]
        MI["__init__.py\nimport User, Task\n→ registrerar i Base.metadata"]
    end

    subgraph schemas["app/schemas"]
        US["user.py\nUserCreate · UserLogin · UserOut"]
        TS["task.py\nTaskCreate · TaskUpdate · TaskOut"]
        TO["token.py\nToken · TokenData"]
    end

    subgraph api["app/api"]
        DE["deps.py\nget_current_user()\nget_current_admin()"]
        AU["auth.py\nPOST /register\nPOST /login"]
        TA["tasks.py\nGET POST PUT DELETE /tasks"]
        RE["recommend.py\nGET /recommend"]
    end

    MAIN["main.py\nFastAPI app\nCORSMiddleware\nStaticFiles\non_startup()"]

    CFG --> SEC
    DBS --> UM
    DBS --> TM
    UM  --> MI
    TM  --> MI
    SEC --> DE
    DBS --> DE
    UM  --> DE
    TO  --> DE
    SEC --> AU
    DBS --> AU
    UM  --> AU
    US  --> AU
    TO  --> AU
    DE  --> TA
    DBS --> TA
    TM  --> TA
    TS  --> TA
    DE  --> RE
    DBS --> RE
    TM  --> RE
    AU  --> MAIN
    TA  --> MAIN
    RE  --> MAIN
    MI  --> MAIN
    DBS --> MAIN

    style core    fill:#eaf4fb,stroke:#2980b9
    style db      fill:#fef9e7,stroke:#f39c12
    style models  fill:#eafaf1,stroke:#27ae60
    style schemas fill:#f9ebea,stroke:#e74c3c
    style api     fill:#f5eef8,stroke:#8e44ad
```

---

## Figur 4 — POST /register (Sekvensdiagram)

```mermaid
sequenceDiagram
    actor U as Användare
    participant FE as Frontend (JS)
    participant FA as FastAPI /register
    participant VAL as Pydantic UserCreate
    participant DB as SQLAlchemy / SQLite
    participant WZ as werkzeug.security

    U->>FE: Fyller i email + lösenord, klickar Register
    FE->>FA: POST /register {"email":"x@y.com","password":"abc123"}

    FA->>VAL: Validerar payload
    alt Valideringsfel (email ogiltig / pw < 6 tecken)
        VAL-->>FA: ValidationError
        FA-->>FE: 422 Unprocessable Entity
        FE-->>U: Visar felmeddelande
    end

    VAL-->>FA: UserCreate OK

    FA->>DB: SELECT * FROM users WHERE email = ?
    alt E-post finns redan
        DB-->>FA: User-objekt
        FA-->>FE: 400 "A user with this email already exists"
        FE-->>U: Visar felmeddelande
    end

    DB-->>FA: None (ny e-post)

    FA->>WZ: generate_password_hash("abc123")
    Note over WZ: PBKDF2-HMAC-SHA256<br/>salt genereras automatiskt<br/>format: pbkdf2:sha256:$iterations$salt$hash
    WZ-->>FA: hashed_password (sträng)

    FA->>DB: INSERT INTO users (email, password, role="user")
    DB-->>FA: User {id=1, email, role=user}

    FA-->>FE: 201 Created {id, email, role}
    FE-->>U: "Account created! You can now log in."
```

---

## Figur 5 — POST /login + JWT-utfärdning (Sekvensdiagram)

```mermaid
sequenceDiagram
    actor U as Användare
    participant FE as Frontend (JS)
    participant FA as FastAPI /login
    participant DB as SQLAlchemy / SQLite
    participant WZ as werkzeug.security
    participant JWT as pyjwt (HS256)

    U->>FE: Fyller i email + lösenord, klickar Login
    FE->>FA: POST /login {"email":"x@y.com","password":"abc123"}

    FA->>DB: SELECT * FROM users WHERE email = ?

    alt Användare finns ej
        DB-->>FA: None
        FA-->>FE: 401 "Invalid email or password"
        FE-->>U: Visar felmeddelande
    end

    DB-->>FA: User {id=1, role="user", password=hash}

    FA->>WZ: check_password_hash(hash, "abc123")
    alt Lösenord matchar ej
        WZ-->>FA: False
        FA-->>FE: 401 "Invalid email or password"
        FE-->>U: Visar felmeddelande (samma msg → ingen e-post-läcka)
    end
    WZ-->>FA: True

    FA->>JWT: encode({sub:"1", role:"user", exp:now+60min}, SECRET_KEY, HS256)
    Note over JWT: Header:  {"alg":"HS256","typ":"JWT"}<br/>Payload: {"sub":"1","role":"user","exp":1234567890}<br/>Signature: HMAC-SHA256(base64(header)+"."+base64(payload), key)
    JWT-->>FA: eyJhbGc... (JWT-token sträng)

    FA-->>FE: 200 {access_token: "eyJ...", token_type: "bearer"}
    FE->>FE: localStorage.setItem("jwt_token", token)
    FE-->>U: Loggar in → visar tasks + rekommendationer
```

---

## Figur 6 — GET /tasks — Rollbaserad åtkomst (Sekvensdiagram)

```mermaid
sequenceDiagram
    actor U as Användare / Admin
    participant FE as Frontend (JS)
    participant FA as FastAPI /tasks
    participant DEP as deps.get_current_user()
    participant JWT as pyjwt
    participant DB as SQLAlchemy / SQLite

    U->>FE: Öppnar tasklistan / klickar Refresh
    FE->>FA: GET /tasks\nAuthorization: Bearer eyJ...

    FA->>DEP: Depends(get_current_user)
    DEP->>JWT: decode(token, SECRET_KEY, HS256)

    alt Token saknas
        FA-->>FE: 401 "Not authenticated"
    end

    alt Token utgången (exp < now)
        JWT-->>DEP: ExpiredSignatureError
        DEP-->>FA: 401 "Token has expired"
        FA-->>FE: 401 Unauthorized
        FE-->>U: Visar felmeddelande
    end

    alt Token manipulerad (ogiltig signatur)
        JWT-->>DEP: InvalidTokenError
        DEP-->>FA: 401 "Invalid token"
    end

    JWT-->>DEP: {sub:"1", role:"user", exp:...}
    DEP->>DB: SELECT * FROM users WHERE id = 1
    DB-->>DEP: User {id=1, role=user}
    DEP-->>FA: current_user (User-objekt)

    alt current_user.role == admin
        FA->>DB: SELECT * FROM tasks
        Note over DB: Admin ser ALLA tasks i systemet
    else current_user.role == user
        FA->>DB: SELECT * FROM tasks WHERE owner_id = 1
        Note over DB: Vanlig user ser bara sina egna
    end

    DB-->>FA: [Task, Task, ...]
    FA-->>FE: 200 [{id,title,priority,status,owner_id,...}, ...]
    FE-->>U: Renderar tasklista med färgkodad prioritet
```

---

## Figur 7 — PUT /tasks/{id} — Uppdateringsflöde (Sekvensdiagram)

```mermaid
sequenceDiagram
    actor U as Användare
    participant FE as Frontend (JS)
    participant FA as FastAPI PUT /tasks/{id}
    participant DEP as get_current_user()
    participant VAL as Pydantic TaskUpdate
    participant DB as SQLAlchemy / SQLite

    U->>FE: Ändrar status på en task
    FE->>FA: PUT /tasks/3\nAuthorization: Bearer eyJ...\n{"status":"done"}

    FA->>DEP: Validera token → current_user
    DEP-->>FA: User {id=1, role=user}

    FA->>VAL: TaskUpdate(status="done")
    Note over VAL: exclude_unset=True →<br/>bara "status" skickas vidare<br/>title/priority/etc. rörs ej
    VAL-->>FA: {status: TaskStatus.done}

    FA->>DB: SELECT * FROM tasks WHERE id = 3
    alt Task finns ej
        DB-->>FA: None
        FA-->>FE: 404 "Task 3 not found"
    end
    DB-->>FA: Task {id=3, title="...", status=pending, owner_id=1}

    Note over FA: Ingen ägarkontroll på PUT (per spec)<br/>Alla autentiserade användare kan uppdatera

    FA->>DB: task.status = "done"\nSESSION.commit()
    DB-->>FA: Task {id=3, status=done}
    FA-->>FE: 200 {id:3, title:"...", status:"done", ...}
    FE->>FE: loadTasks() → uppdaterar listan
    FE-->>U: Task markerad som klar ✅
```

---

## Figur 8 — GET /recommend — AI-anrop med fallback (Sekvensdiagram)

```mermaid
sequenceDiagram
    actor U as Användare
    participant FE as Frontend (JS)
    participant FA as FastAPI /recommend
    participant DEP as get_current_user()
    participant DB as SQLAlchemy / SQLite
    participant EXT as Extern AI-tjänst\n(simulerad)
    participant MOCK as Lokal mock-logik

    U->>FE: Klickar Refresh på rekommendationer
    FE->>FA: GET /recommend\nAuthorization: Bearer eyJ...

    FA->>DEP: Validera token
    DEP-->>FA: current_user {id=1}

    FA->>DB: SELECT * FROM tasks WHERE owner_id = 1
    DB-->>FA: [Task1, Task2, Task3...]

    FA->>EXT: POST https://api.mock-ai-service.example.com/v1/recommend\nAuthorization: Bearer mock-ai-api-key-xyz-2024\n{"tasks":["Fix bug","Write tests",...]}\ntimeout=2s

    alt Externt anrop misslyckas (alltid i detta system)
        EXT-->>FA: ConnectionError / Timeout
        Note over FA: Fångas tyst med except Exception<br/>data_source = "mock-ai"
    else Externt anrop lyckas (framtida)
        EXT-->>FA: {"recommendations": [...]}
        Note over FA: data_source = "external-ai"
    end

    FA->>MOCK: _generate_recommendations(tasks)
    Note over MOCK: Regel 1: overdue (due_date < today) → 🔴 high<br/>Regel 2: high-priority + pending    → 🔴 high<br/>Regel 3: ≥3 in_progress             → 🟡 medium<br/>Regel 4: alla done                  → 🟢 low (firande)<br/>Regel 5: inga tasks                 → 🟢 low (onboarding)<br/>Regel 6: inget specifikt problem    → 🟢 low (generellt)
    MOCK-->>FA: [{type, priority, message}, ...]

    FA-->>FE: 200 {\n  user: "x@y.com",\n  source: "mock-ai",\n  api_key_used: "mock-ai-...",\n  task_count: 3,\n  recommendations: [...]\n}
    FE-->>U: Renderar rekommendationer med ikoner och färger
```

---

## Figur 9 — JWT-tokens livscykel (Tillståndsdiagram)

```mermaid
stateDiagram-v2
    [*] --> EjUtfärdad : Användare ej inloggad

    EjUtfärdad --> Utfärdad : POST /login\n✅ rätt email + lösenord\njwt.encode(HS256, SECRET_KEY)\nexp = now + 60 min

    Utfärdad --> Aktiv : Sparas i localStorage\nAnvänds i Authorization header

    Aktiv --> Aktiv : Skyddad endpoint anropad\njwt.decode() → OK\nAnvändare identifierad

    Aktiv --> Utgången : exp timestamp passerad\n(efter 60 minuter)

    Utgången --> Nekad : jwt.decode() →\nExpiredSignatureError\nHTTP 401 "Token has expired"

    Aktiv --> Ogiltig : Token manipulerad\n(payload eller signatur ändrad)

    Ogiltig --> Nekad : jwt.decode() →\nInvalidTokenError\nHTTP 401 "Invalid token"

    Nekad --> EjUtfärdad : Användaren behöver\nlogga in igen

    Aktiv --> Raderad : logout()\nlocalStorage.removeItem("jwt_token")

    Raderad --> EjUtfärdad : Token finns ej längre\ni klienten

    note right of Aktiv
        Payload innehåller:
        sub  = user_id (str)
        role = "user" | "admin"
        exp  = Unix timestamp
    end note
```

---

## Figur 10 — Tasks livscykel (Tillståndsdiagram)

```mermaid
stateDiagram-v2
    [*] --> Pending : POST /tasks\nowner_id = current_user.id\nstatus DEFAULT = pending

    Pending --> InProgress : PUT /tasks/{id}\n{"status":"in_progress"}\n(ingen ägarkontroll)

    Pending --> Done : PUT /tasks/{id}\n{"status":"done"}

    InProgress --> Done : PUT /tasks/{id}\n{"status":"done"}

    InProgress --> Pending : PUT /tasks/{id}\n{"status":"pending"}\n(återöppna)

    Done --> InProgress : PUT /tasks/{id}\n{"status":"in_progress"}\n(återaktivera)

    Done --> Pending : PUT /tasks/{id}\n{"status":"pending"}

    Pending --> [*] : DELETE /tasks/{id}\nUser: måste äga tasken\nAdmin: kan radera alla

    InProgress --> [*] : DELETE /tasks/{id}

    Done --> [*] : DELETE /tasks/{id}

    note right of Pending
        Skapad med:
        title (obligatorisk)
        description (valfri)
        due_date (valfri)
        priority: low|medium|high
    end note

    note right of Done
        AI-rekommendation:
        Om ALLA tasks är done
        → 🎉 celebration-meddelande
    end note
```

---

## Figur 11 — Säkerhetsmodell per lager

| Lager | Mekanism | Bibliotek / Standard | Detaljer |
|-------|----------|----------------------|----------|
| **Transportlager** | HTTP (dev) / HTTPS (prod) | — | CORS: `allow_origins=["*"]` i dev |
| **Lösenordslagring** | PBKDF2-HMAC-SHA256 | `werkzeug 2.3` | Salt auto-genereras · Aldrig plain text i DB |
| **Autentisering** | JWT Bearer Token | `pyjwt 2.6` · HS256 | Payload: `sub`, `role`, `exp` · TTL 60 min |
| **Tokenöverföring** | Authorization-header | OAuth2 Bearer | `OAuth2PasswordBearer(tokenUrl="/login")` |
| **Tokensignering** | HMAC-SHA256 | `SECRET_KEY` (hardcoded) | Prod: bör vara env-variabel ≥ 256 bitar |
| **Auktorisering** | Rollkontroll (RBAC) | FastAPI `Depends()` | `user`: egna tasks · `admin`: allt |
| **Ägarskapsskydd** | owner_id-kontroll | SQLAlchemy filter | Tillämpas på DELETE, EJ på PUT (per spec) |
| **Input-validering** | Pydantic-modeller | `pydantic` (via FastAPI) | Typkontroll · min/max-längder · EmailStr |
| **SQL-injektion** | Parametriserade queries | SQLAlchemy ORM + `text()` | `:param`-syntax i alla raw SQL-queries |
| **Felmeddelanden** | Generiska auth-fel | FastAPI `HTTPException` | "Invalid email or password" (läcker ej om e-post finns) |

---

## Figur 12 — Storyboard: 5 huvudscenarier

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    STORYBOARD — TASK MANAGEMENT SYSTEM                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  SCENARIO 1: Ny användare registrerar sig och loggar in                     ║
║  ─────────────────────────────────────────────────────                      ║
║                                                                              ║
║  [Browser]          [POST /register]        [SQLite]                        ║
║     │                     │                    │                            ║
║     │  Öppnar /frontend   │                    │                            ║
║     │◄────────────────────│  index.html        │                            ║
║     │                     │                    │                            ║
║     │  email + password   │                    │                            ║
║     │────────────────────►│  Validerar Pydantic│                            ║
║     │                     │  hash_password()   │                            ║
║     │                     │───────────────────►│  INSERT user               ║
║     │  201 {id,email,role}│◄───────────────────│                            ║
║     │◄────────────────────│                    │                            ║
║     │  POST /login        │                    │                            ║
║     │────────────────────►│  verify_password() │                            ║
║     │                     │  jwt.encode()      │                            ║
║     │  200 {access_token} │                    │                            ║
║     │◄────────────────────│                    │                            ║
║     │  localStorage ✓     │                    │                            ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  SCENARIO 2: Användaren skapar och hanterar tasks                           ║
║  ─────────────────────────────────────────────────                          ║
║                                                                              ║
║  [Browser]          [POST /tasks]           [SQLite]                        ║
║     │                     │                    │                            ║
║     │  Fyller i formulär  │                    │                            ║
║     │  title="Fix bug"    │                    │                            ║
║     │  priority=high      │                    │                            ║
║     │────────────────────►│  Bearer JWT        │                            ║
║     │                     │  decode_token()    │                            ║
║     │                     │  owner_id=1 (auto) │                            ║
║     │                     │───────────────────►│  INSERT task               ║
║     │  201 {id,title,...} │◄───────────────────│                            ║
║     │◄────────────────────│                    │                            ║
║     │                     │                    │                            ║
║     │  PUT /tasks/1       │                    │                            ║
║     │  {"status":"done"}  │                    │                            ║
║     │────────────────────►│  exclude_unset=True│                            ║
║     │                     │───────────────────►│  UPDATE tasks SET          ║
║     │  200 {status:"done"}│◄───────────────────│  status="done"             ║
║     │◄────────────────────│                    │                            ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  SCENARIO 3: Admin ser alla användares tasks                                ║
║  ────────────────────────────────────────────                               ║
║                                                                              ║
║  [Admin Browser]    [GET /tasks]            [SQLite]                        ║
║     │                     │                    │                            ║
║     │  Bearer JWT (admin) │                    │                            ║
║     │────────────────────►│  decode → role=admin                           ║
║     │                     │───────────────────►│  SELECT * FROM tasks       ║
║     │                     │                    │  (ALLA tasks, ej filtrerat)║
║     │                     │◄───────────────────│  [task1, task2, task3...]  ║
║     │  200 [alla tasks]   │                    │                            ║
║     │◄────────────────────│                    │                            ║
║                                                                              ║
║  [User Browser]     [GET /tasks]            [SQLite]                        ║
║     │                     │                    │                            ║
║     │  Bearer JWT (user)  │                    │                            ║
║     │────────────────────►│  decode → role=user│                            ║
║     │                     │───────────────────►│  SELECT * FROM tasks       ║
║     │                     │                    │  WHERE owner_id = 1        ║
║     │  200 [egna tasks]   │◄───────────────────│  (bara egna)               ║
║     │◄────────────────────│                    │                            ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  SCENARIO 4: AI-rekommendationer med extern API-fallback                    ║
║  ───────────────────────────────────────────────────────                    ║
║                                                                              ║
║  [Browser]    [GET /recommend]   [Extern AI]   [Mock-logik]                 ║
║     │               │                │              │                       ║
║     │  Bearer JWT   │                │              │                       ║
║     │──────────────►│  hämtar tasks  │              │                       ║
║     │               │                │              │                       ║
║     │               │──────────────►│  POST + API-nyckel                   ║
║     │               │                │  timeout=2s  │                       ║
║     │               │◄──────────────│  ❌ ConnectionError                  ║
║     │               │  (fångas tyst) │              │                       ║
║     │               │──────────────────────────────►│                       ║
║     │               │                │  Analyserar: │                       ║
║     │               │                │  overdue?    │                       ║
║     │               │                │  high+pending│                       ║
║     │               │                │  ≥3 in_prog? │                       ║
║     │               │◄──────────────────────────────│                       ║
║     │  200 {source:"mock-ai",        │              │                       ║
║     │   recommendations:[...]}       │              │                       ║
║     │◄──────────────│                │              │                       ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  SCENARIO 5: Utgången token → 401 → omloggning                             ║
║  ──────────────────────────────────────────────                             ║
║                                                                              ║
║  [Browser]          [FastAPI]             [pyjwt]                           ║
║     │                     │                    │                            ║
║     │  GET /tasks         │                    │                            ║
║     │  Bearer <gammal JWT>│                    │                            ║
║     │────────────────────►│  decode_access_token()                         ║
║     │                     │───────────────────►│  exp < now?                ║
║     │                     │◄───────────────────│  ✅ Ja → ExpiredSignatureError
║     │                     │  raise HTTP 401    │                            ║
║     │  401 "Token has     │                    │                            ║
║     │   expired"          │                    │                            ║
║     │◄────────────────────│                    │                            ║
║     │  Visar felmeddelande│                    │                            ║
║     │  Användaren loggar in igen               │                            ║
║     │  → nytt JWT utfärdas (TTL reset)         │                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Teknisk referens — snabbguide

| Konstant / Nyckel | Värde | Plats |
|---|---|---|
| `SECRET_KEY` | `"supersecret-taskmanager-key-2024"` | `app/core/config.py` |
| `ALGORITHM` | `HS256` (HMAC-SHA256) | `app/core/config.py` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | `app/core/config.py` |
| `EXTERNAL_AI_API_KEY` | `"mock-ai-api-key-xyz-2024"` | `app/api/recommend.py` |
| `SQLALCHEMY_DATABASE_URL` | `"sqlite:///./tasks.db"` | `app/db/database.py` |
| DB-fil | `tasks.db` (skapas automatiskt) | projektrot |
| Frontend | `http://127.0.0.1:8000/frontend` | `app/static/index.html` |
| API-docs | `http://127.0.0.1:8000/docs` | FastAPI Swagger UI |
