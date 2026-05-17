# ---------------------------------------------------------------------------
# Application configuration
# ---------------------------------------------------------------------------
# SECRET_KEY is hardcoded here as required by the issue spec.
# In a real production environment this value should come from an
# environment variable or a secrets manager — never committed to git.

SECRET_KEY: str = "supersecret-taskmanager-key-2024"

# Hashing algorithm used when signing JWT tokens
ALGORITHM: str = "HS256"

# How long (in minutes) an issued token remains valid
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
