import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-default-secret-key')
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1')
    DATABASE_URL = os.getenv('DATABASE_URL')

    @classmethod
    def validate(cls):
        """Validate required environment variables."""
        if not cls.SECRET_KEY:
            raise ValueError("No SECRET_KEY set for the application.")
        if not cls.DATABASE_URL:
            raise ValueError("No DATABASE_URL set for the application.")

# Validate the configuration
Config.validate()