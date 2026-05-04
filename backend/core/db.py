"""
Shared database configuration and utilities.

Provides a thread lock for coordinating access to database.db
across multiple modules (profiles and sessions).
"""

import threading

# Shared lock for all database.db operations
_lock = threading.Lock()
