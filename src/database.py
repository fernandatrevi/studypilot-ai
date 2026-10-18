
import sqlite3
import json
from pathlib import Path


DB_PATH = Path("data/studypilot.db")


def conectar():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def inicializar_db():
    with conectar() as conexion:

        # Tabla de materias
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS materias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL
            )
        """)

        # Tabla de resultados de exámenes
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS resultados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                materia TEXT NOT NULL,
                pregunta TEXT NOT NULL,
                respuesta_usuario TEXT,
                respuesta_correcta TEXT NOT NULL,
                acierto INTEGER NOT NULL,
                explicacion TEXT,
                fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                opciones TEXT
            )
        """)

        # Actualizar bases de datos anteriores
        columnas = [
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(resultados)"
            ).fetchall()
        ]

        if "opciones" not in columnas:
            conexion.execute(
                "ALTER TABLE resultados ADD COLUMN opciones TEXT"
            )


def agregar_materia(nombre):
    with conectar() as conexion:
        conexion.execute(
            "INSERT OR IGNORE INTO materias (nombre) VALUES (?)",
            (nombre,)
        )


def obtener_materias():
    with conectar() as conexion:
        filas = conexion.execute(
            "SELECT nombre FROM materias ORDER BY nombre"
        ).fetchall()

    return [fila[0] for fila in filas]


def guardar_resultados(materia, resultados):
    with conectar() as conexion:
        for resultado in resultados:

            opciones = resultado.get("opciones", [])

            conexion.execute("""
                INSERT INTO resultados (
                    materia,
                    pregunta,
                    respuesta_usuario,
                    respuesta_correcta,
                    acierto,
                    explicacion,
                    opciones
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                materia,
                resultado["pregunta"],
                resultado["respuesta_usuario"],
                resultado["respuesta_correcta"],
                int(resultado["acierto"]),
                resultado["explicacion"],
                json.dumps(
                    opciones,
                    ensure_ascii=False
                )
            ))


def obtener_errores(materia):
    with conectar() as conexion:
        filas = conexion.execute("""
            SELECT
                pregunta,
                respuesta_usuario,
                respuesta_correcta,
                explicacion,
                fecha
            FROM resultados
            WHERE materia = ? AND acierto = 0
            ORDER BY fecha DESC, id DESC
        """, (materia,)).fetchall()

    return filas


def obtener_estadisticas(materia):
    with conectar() as conexion:
        fila = conexion.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(acierto), 0)
            FROM resultados
            WHERE materia = ?
        """, (materia,)).fetchone()

    total, aciertos = fila

    return {
        "total": total,
        "aciertos": aciertos,
        "porcentaje": (
            round(aciertos / total * 100, 1)
            if total else 0
        )
    }


def obtener_errores_interactivos(materia):
    with conectar() as conexion:
        filas = conexion.execute("""
            SELECT
                id,
                pregunta,
                respuesta_usuario,
                respuesta_correcta,
                explicacion,
                fecha,
                opciones
            FROM resultados
            WHERE materia = ? AND acierto = 0
            ORDER BY fecha DESC, id DESC
        """, (materia,)).fetchall()

    errores = []

    for fila in filas:
        opciones = []

        if fila[6]:
            try:
                opciones = json.loads(fila[6])
            except (json.JSONDecodeError, TypeError):
                opciones = []

        errores.append({
            "id": fila[0],
            "pregunta": fila[1],
            "respuesta_usuario": fila[2],
            "respuesta_correcta": fila[3],
            "explicacion": fila[4],
            "fecha": fila[5],
            "opciones": opciones
        })

    return errores
