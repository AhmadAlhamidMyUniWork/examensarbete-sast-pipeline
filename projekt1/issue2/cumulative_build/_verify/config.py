import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DATABASE = os.environ.get('DATABASE', 'customers.db')
    JWT_EXPIRATION_HOURS = 24
