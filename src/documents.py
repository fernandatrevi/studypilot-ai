
from pathlib import Path
import re
import pymupdf

CARPETA_DOCUMENTOS = Path("data/documents")


def carpeta_materia(materia):
    nombre = re.sub(r"[^\w\s-]", "", materia, flags=re.UNICODE)
    nombre = re.sub(r"\s+", "_", nombre.strip())

    if not nombre:
        raise ValueError("El nombre de la materia no es válido.")

    carpeta = CARPETA_DOCUMENTOS / nombre
    carpeta.mkdir(parents=True, exist_ok=True)

    return carpeta


def ruta_documento(materia, nombre_archivo):
    nombre = Path(nombre_archivo).name

    if not nombre.lower().endswith(".pdf"):
        raise ValueError("El archivo debe ser un PDF.")

    return carpeta_materia(materia) / nombre


def guardar_pdf(materia, archivo):
    ruta = ruta_documento(materia, archivo.name)
    ruta.write_bytes(archivo.getvalue())
    return ruta


def listar_pdfs(materia):
    carpeta = carpeta_materia(materia)

    return sorted(
        archivo.name
        for archivo in carpeta.glob("*.pdf")
        if archivo.is_file()
    )


def leer_pdf(materia, nombre_archivo):
    ruta = ruta_documento(materia, nombre_archivo)
    textos = []

    with pymupdf.open(ruta) as documento:
        for numero, pagina in enumerate(documento, start=1):
            contenido = pagina.get_text("text")

            if contenido.strip():
                textos.append(
                    f"--- Página {numero} ---\n{contenido}"
                )

    return "\n\n".join(textos)


def contar_paginas(materia, nombre_archivo):
    ruta = ruta_documento(materia, nombre_archivo)

    with pymupdf.open(ruta) as documento:
        return len(documento)


def obtener_imagen_pagina(materia, nombre_archivo, numero_pagina):
    ruta = ruta_documento(materia, nombre_archivo)

    with pymupdf.open(ruta) as documento:
        pagina = documento[numero_pagina]

        imagen = pagina.get_pixmap(
            matrix=pymupdf.Matrix(1.5, 1.5),
            alpha=False
        )

        return imagen.tobytes("png")


def obtener_contexto(materia, limite=14000):
    documentos = listar_pdfs(materia)
    partes = []

    for nombre in documentos:
        texto = leer_pdf(materia, nombre)

        if texto.strip():
            partes.append(
                f"DOCUMENTO: {nombre}\n{texto}"
            )

    contexto = "\n\n".join(partes)

    return contexto[:limite]

def obtener_contexto(materia, limite=14000):
    documentos = listar_pdfs(materia)
    partes = []

    for nombre in documentos:
        texto = leer_pdf(materia, nombre)

        if texto.strip():
            partes.append(
                f"DOCUMENTO: {nombre}\n{texto}"
            )

    contexto = "\n\n".join(partes)

    return contexto[:limite]
