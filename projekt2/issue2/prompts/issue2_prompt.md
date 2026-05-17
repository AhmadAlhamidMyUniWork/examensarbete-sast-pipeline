# Issue #2 Prompt — Databasmodeller (User + Task)

## Prompt sent to AI teammate

**Issue #2: Databasmodeller (User + Task)**

Beskrivning: Implementera databasmodeller för User och Task med SQLAlchemy och SQLite.

Uppgifter:
- Konfigurera SQLAlchemy engine och session
- Skapa Base-modell
- Skapa `User`-modell med fälten: id, email, password, role
- Skapa `Task`-modell med fälten: id, title, description, due_date, priority, status, owner_id
- Skapa relation mellan User och Task
- Lägg till logik för att skapa databasen automatiskt
- Lägg till minst en raw SQL-query

Acceptanskriterier:
- Databasen skapas automatiskt vid start
- Tabeller för User och Task finns
- Relationer fungerar korrekt
- CRUD-operationer fungerar grundläggande
