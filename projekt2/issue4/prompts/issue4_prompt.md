# Issue #4 Prompt — Task endpoints (CRUD)

## Prompt sent to AI teammate

**Issue #4: Task endpoints (CRUD)**

Beskrivning: Implementera endpoints för att skapa, läsa och uppdatera tasks.

Uppgifter:
- Skapa endpoint GET /tasks
- Skapa endpoint POST /tasks
- Skapa endpoint PUT /tasks/{id}
- (Valfritt) Skapa DELETE /tasks/{id}
- Koppla tasks till inloggad användare
- Lägg till enkel validering
- Implementera enkel rollhantering (admin/user)
- Undvik strikt ägarkontroll (medvetet enkel implementation)

Acceptanskriterier:
- Användare kan skapa och se sina tasks
- Tasks sparas i databasen
- Uppdatering av task fungerar
- Admin kan se fler tasks än vanliga användare
