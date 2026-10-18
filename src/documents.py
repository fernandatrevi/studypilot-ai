
"""Gestión de PDF y selección de contexto para StudyPilot AI."""

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
            contenido = pagina.get_text("text").strip()

            if contenido:
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
            alpha=False,
        )

        return imagen.tobytes("png")


def obtener_contexto(materia, limite=14000):
    """
    Obtiene contenido de los PDF de una materia.

    Mejoras:
    - Conserva definiciones y explicaciones breves.
    - Evita depender únicamente de las primeras páginas.
    - Distribuye el contenido entre los documentos disponibles.
    - Mantiene el nombre del documento y el número de página.
    - No inventa texto que no se pudo extraer.

    Limitación:
    - No realiza OCR sobre imágenes.
    """

    if type(limite) is not int or limite <= 0:
        raise ValueError(
            "El límite debe ser un entero positivo."
        )

    documentos = []

    for nombre in listar_pdfs(materia):
        ruta = ruta_documento(materia, nombre)
        paginas = []

        with pymupdf.open(ruta) as documento:
            for numero, pagina in enumerate(documento, start=1):
                texto = pagina.get_text("text").strip()

                if not texto:
                    continue

                palabras = re.findall(
                    r"\b\w+\b",
                    texto,
                    flags=re.UNICODE,
                )

                # Conservar definiciones y explicaciones cortas.
                if len(palabras) < 8:
                    continue

                bloque = (
                    f"DOCUMENTO: {nombre}\n"
                    f"--- Página {numero} ---\n"
                    f"{texto}"
                )

                paginas.append(bloque)

        if paginas:
            documentos.append(paginas)

    if not documentos:
        return ""

    # Intercalar páginas de los documentos para darles
    # oportunidad de aparecer en el contexto.
    candidatas = []
    indice = 0

    while any(indice < len(doc) for doc in documentos):
        for paginas in documentos:
            if indice < len(paginas):
                candidatas.append(paginas[indice])

        indice += 1

    # Priorizar fragmentos legibles: evitar repartir el límite en trozos
    # diminutos cuando hay cientos de diapositivas.
    seleccionadas = []
    espacio_restante = limite
    for bloque in candidatas:
        separador = "\n\n" if seleccionadas else ""
        disponible = espacio_restante - len(separador)
        if disponible < 150:
            break
        prefijo = bloque.split("\n", 2)
        if len(prefijo) != 3:
            continue
        encabezado = prefijo[0] + "\n" + prefijo[1] + "\n"
        espacio_texto = min(1400, disponible - len(encabezado))
        if espacio_texto < 100:
            continue
        fragmento = encabezado + prefijo[2][:espacio_texto]
        seleccionadas.append(fragmento)
        espacio_restante -= len(separador) + len(fragmento)

    return "\n\n".join(seleccionadas)
