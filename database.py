import os
import sqlite3
from urllib.parse import urlparse

def get_db_connection():
    """Get database connection - PostgreSQL or SQLite"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and database_url.startswith('postgresql'):
        # PostgreSQL connection
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Parse URL
        result = urlparse(database_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        return conn, 'postgresql'
    else:
        # SQLite fallback
        conn = sqlite3.connect('blog_app.db')
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'
