"""
db/database.py

Manejo de la conexión a SQLite e inicialización del esquema.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Ruta de la base de datos (junto al ejecutable/proyecto)
DB_PATH = Path(__file__).resolve().parent.parent / "tintoreria.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """
    Crea una conexión nueva a la base de datos.
    row_factory = Row permite acceder a las columnas por nombre (row["campo"]).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_cursor(commit: bool = False):
    """
    Context manager para obtener un cursor y cerrar/confirmar automáticamente.

    Uso:
        with get_cursor(commit=True) as cur:
            cur.execute("INSERT INTO clientes (...) VALUES (...)", (...))
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(force: bool = False) -> None:
    """
    Inicializa la base de datos ejecutando schema.sql.
    Si force=True, elimina el archivo existente y lo vuelve a crear
    (usar solo en desarrollo).
    """
    if force and DB_PATH.exists():
        DB_PATH.unlink()

    is_new = not DB_PATH.exists()

    conn = get_connection()
    try:
        if is_new:
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()
    finally:
        conn.close()