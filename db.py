# =============================================================================
# db.py — Database Connection & Query Helpers
# =============================================================================
# Provides a centralized interface to MySQL using mysql-connector-python.
# All queries use parameterized inputs to prevent SQL injection.
# =============================================================================

import mysql.connector
from mysql.connector import Error
from config import Config


def get_connection():
    """
    Creates and returns a new MySQL database connection using Config credentials.
    Raises an exception if the connection fails.
    """
    try:
        conn = mysql.connector.connect(
            host     = Config.DB_HOST,
            user     = Config.DB_USER,
            password = Config.DB_PASSWORD,
            database = Config.DB_NAME,
            port     = Config.DB_PORT,
            autocommit = True
        )
        return conn
    except Error as e:
        print(f"[DB ERROR] Failed to connect to MySQL: {e}")
        raise


def execute_query(query, params=None):
    """
    Executes a non-SELECT query (INSERT, UPDATE, DELETE).
    Uses parameterized queries to prevent SQL injection.

    Args:
        query  (str):   The SQL query string with %s placeholders.
        params (tuple): Optional tuple of parameters to bind.

    Returns:
        int: lastrowid of the inserted/affected row, or None.
    """
    conn   = None
    cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"[DB ERROR] execute_query failed: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def fetch_all(query, params=None):
    """
    Executes a SELECT query and returns all matching rows as a list of dicts.

    Args:
        query  (str):   The SQL SELECT query with %s placeholders.
        params (tuple): Optional tuple of parameters to bind.

    Returns:
        list[dict]: List of rows, each as a column→value dict.
    """
    conn   = None
    cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchall()
    except Error as e:
        print(f"[DB ERROR] fetch_all failed: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def fetch_one(query, params=None):
    """
    Executes a SELECT query and returns the first matching row as a dict.

    Args:
        query  (str):   The SQL SELECT query with %s placeholders.
        params (tuple): Optional tuple of parameters to bind.

    Returns:
        dict | None: The first row as a column→value dict, or None if not found.
    """
    conn   = None
    cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchone()
    except Error as e:
        print(f"[DB ERROR] fetch_one failed: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()# =============================================================================
# db.py — Database Connection & Query Helpers
# =============================================================================
# Provides a centralized interface to MySQL using mysql-connector-python.
# All queries use parameterized inputs to prevent SQL injection.
# =============================================================================

import mysql.connector
from mysql.connector import Error
from config import Config


def get_connection():
    """
    Creates and returns a new MySQL database connection using Config credentials.
    Raises an exception if the connection fails.
    """
    try:
        conn = mysql.connector.connect(
            host     = Config.DB_HOST,
            user     = Config.DB_USER,
            password = Config.DB_PASSWORD,
            database = Config.DB_NAME,
            port     = Config.DB_PORT,
            autocommit = True
        )
        return conn
    except Error as e:
        print(f"[DB ERROR] Failed to connect to MySQL: {e}")
        raise


def execute_query(query, params=None):
    """
    Executes a non-SELECT query (INSERT, UPDATE, DELETE).
    Uses parameterized queries to prevent SQL injection.

    Args:
        query  (str):   The SQL query string with %s placeholders.
        params (tuple): Optional tuple of parameters to bind.

    Returns:
        int: lastrowid of the inserted/affected row, or None.
    """
    conn   = None
    cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"[DB ERROR] execute_query failed: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def fetch_all(query, params=None):
    """
    Executes a SELECT query and returns all matching rows as a list of dicts.

    Args:
        query  (str):   The SQL SELECT query with %s placeholders.
        params (tuple): Optional tuple of parameters to bind.

    Returns:
        list[dict]: List of rows, each as a column→value dict.
    """
    conn   = None
    cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchall()
    except Error as e:
        print(f"[DB ERROR] fetch_all failed: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def fetch_one(query, params=None):
    """
    Executes a SELECT query and returns the first matching row as a dict.

    Args:
        query  (str):   The SQL SELECT query with %s placeholders.
        params (tuple): Optional tuple of parameters to bind.

    Returns:
        dict | None: The first row as a column→value dict, or None if not found.
    """
    conn   = None
    cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchone()
    except Error as e:
        print(f"[DB ERROR] fetch_one failed: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()