import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DATABASE = os.environ.get('DATABASE', 'customers.db')
    JWT_EXPIRATION_HOURS = 24
    EXTERNAL_API_URL = os.environ.get(
        'EXTERNAL_API_URL',
        'https://jsonplaceholder.typicode.com/users'
    )
    EXTERNAL_API_TIMEOUT = 5  # sekunder
