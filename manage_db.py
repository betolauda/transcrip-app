#!/usr/bin/env python3
"""
Database management CLI script.

Usage:
    python manage_db.py status
    python manage_db.py migrate
    python manage_db.py migrate --dry-run
    python manage_db.py rollback 3
    python manage_db.py create add_new_feature --description "Add feature X"
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == '__main__':
    from src.database.management import db
    db()