#!/usr/bin/env python
"""Test MySQL connection with new credentials"""

from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text

load_dotenv()
db_url = os.getenv('DATABASE_URL')
print(f'Testing with DATABASE_URL: {db_url}')

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✓ MySQL connection successful!')
        print(f'Query result: {result.fetchone()}')
        print('✓ Database is ready!')
except Exception as e:
    print(f'✗ Connection failed: {str(e)}')
    exit(1)
