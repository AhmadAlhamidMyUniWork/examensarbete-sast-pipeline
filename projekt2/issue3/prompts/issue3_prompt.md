# Issue #3 Prompt — Autentisering (register/login/JWT)

## Prompt sent to AI teammate

**Issue #3: Autentisering (register/login/JWT)**

Beskrivning: Implementera användarregistrering och inloggning med JWT samt rollhantering.

Uppgifter:
- Implementera enkel lösenordshashning
- Skapa endpoint POST /register
- Skapa endpoint POST /login
- Generera JWT-token vid login
- Lägg till hårdkodad SECRET_KEY
- Implementera funktion för att läsa användare från token
- Inkludera roll (user/admin) i token

Acceptanskriterier:
- Användare kan registrera konto
- Användare kan logga in och få JWT-token
- Token innehåller user_id och roll
- Skyddade endpoints kan läsa aktuell användare
