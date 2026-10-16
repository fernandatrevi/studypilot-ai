
from pathlib import Path
import re
import pymupdf


# Carpeta donde se guardan los documentos
DOCUMENTS_DIR = Path("data/documents")


# Crear carpeta para cada materia
def carpeta_materia(materia):
    nombre = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        materia
    )

    nombre = nombre.strip("_") or "materia"

    carpeta = DOCUMENTS_DIR / nombre
    carpeta.mkdir(parents=True, exist_ok=True)

    return carpeta


# Guardar documentos PDF
def guardar_pdf(materia, archivo):
    carpeta = carpeta_materia(materia)

    nombre = Path(archivo.name).name

    if not nombre.lower().endswith(".pdf"):
        raise ValueError("Solo se permiten archivos PDF.")

    ruta = carpeta / nombre

    with open(ruta, "wb") as f:
        f.write(archivo.getbuffer())

    return ruta


# Obtener documentos guardados
def listar_pdfs(materia):
    carpeta = carpeta_materia(materia)

    return sorted(
        archivo.name
        for archivo in carpeta.glob("*.pdf")
    )


# Leer contenido de los documentos
def leer_pdf(materia, nombre_archivo):
    carpeta = carpeta_materia(materia)
    ruta = carpeta / Path(nombre_archivo).name

    texto = []

    with pymupdf.open(ruta) as documento:
        for numero, pagina in enumerate(documento, start=1):
            contenido = pagina.get_text("text")

            if contenido.strip():
                texto.append(
                    f"--- Página {numero} ---\n{contenido}"
                )

    return "\n\n".join(texto)

def obtener_imagen_pagina(materia, nombre_archivo, numero_pagina):
    carpeta = carpeta_materia(materia)
    ruta = carpeta / Path(nombre_archivo).name

    with pymupdf.open(ruta) as documento:
        pagina = documento[numero_pagina]
        imagen = pagina.get_pixmap(
            matrix=pymupdf.Matrix(1.5, 1.5),
            alpha=False
        )

        return imagen.tobytes("png")


def contar_paginas(materia, nombre_archivo):
    carpeta = carpeta_materia(materia)
    ruta = carpeta / Path(nombre_archivo).name

    with pymupdf.open(ruta) as documento:
        return len(documento)