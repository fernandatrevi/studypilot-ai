import sqlite3
from pathlib import Path

DB_PATH = Path("data/studypilot.db")


def conectar():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def inicializar_db():
    with conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS materias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            )
        """)


def agregar_materia(nombre):
    with conectar() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO materias (nombre) VALUES (?)",
            (nombre,)
        )


def obtener_materias():
    with conectar() as conn:
        filas = conn.execute(
            "SELECT nombre FROM materias ORDER BY nombre"
        ).fetchall()

    return [fila[0] for fila in filas]