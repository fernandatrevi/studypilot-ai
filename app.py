
import streamlit as st

from src.database import (
    inicializar_db,
    agregar_materia,
    obtener_materias
)

from src.documents import (
    guardar_pdf,
    listar_pdfs,
    leer_pdf,
    obtener_imagen_pagina,
    contar_paginas
)


# Configuración
st.set_page_config(
    page_title="StudyPilot AI",
    page_icon="📚",
    layout="wide"
)

inicializar_db()

# Página principal
st.title("📚 StudyPilot AI")
st.write("Tu asistente inteligente para estudiar diferentes materias.")

# Materias
st.subheader("Mis materias")

nueva_materia = st.text_input("Nombre de la materia")

if st.button("Agregar materia"):
    nombre = nueva_materia.strip()

    if nombre:
        agregar_materia(nombre)
        st.success("Materia guardada correctamente.")
    else:
        st.warning("Escribe el nombre de una materia.")

materias = obtener_materias()

if materias:
    materia = st.selectbox(
        "Selecciona una materia",
        materias
    )

    st.subheader(f"Estudiar: {materia}")

    # Modos de estudio
    opcion = st.radio(
        "¿Qué quieres hacer?",
        [
            "Explicar un tema",
            "Practicar preguntas",
            "Simular un examen",
            "Repasar errores"
        ]
    )

    st.write(f"Modo seleccionado: {opcion}")

    # Documentos
    st.divider()
    st.subheader("📄 Documentos de estudio")

    st.write(
        "Sube las diapositivas, apuntes o materiales "
        "que quieras utilizar para estudiar esta materia."
    )

    archivo_pdf = st.file_uploader(
        "Selecciona un archivo PDF",
        type=["pdf"],
        key=f"pdf_{materia}"
    )

    if archivo_pdf is not None:
        st.write(f"Archivo seleccionado: {archivo_pdf.name}")

        if st.button("Guardar PDF"):
            ruta = guardar_pdf(materia, archivo_pdf)
            st.success(f"Documento guardado: {ruta.name}")

    # Mostrar documentos
    st.subheader("Mis documentos")

    documentos = listar_pdfs(materia)

    if documentos:
        st.write(f"Tienes {len(documentos)} documento(s) guardado(s).")

        for documento in documentos:
            st.write(f"📄 {documento}")

            # Visualizar páginas completas
            with st.expander(
                f"Ver diapositivas: {documento}"
            ):
                try:
                    total_paginas = contar_paginas(
                        materia,
                        documento
                    )

                    pagina = st.number_input(
                        "Número de página",
                        min_value=1,
                        max_value=total_paginas,
                        value=1,
                        step=1,
                        key=f"pagina_{materia}_{documento}"
                    )

                    imagen = obtener_imagen_pagina(
                        materia,
                        documento,
                        pagina - 1
                    )

                    st.image(
                        imagen,
                        caption=f"Página {pagina} de {total_paginas}",
                        use_container_width=True
                    )

                except Exception as error:
                    st.error(
                        f"No se pudo mostrar la página: {error}"
                    )

            # Extraer texto del PDF
            if st.button(
                "Leer PDF",
                key=f"leer_{materia}_{documento}"
            ):
                try:
                    texto = leer_pdf(materia, documento)

                    if texto.strip():
                        st.success("Texto extraído correctamente.")

                        st.text_area(
                            "Contenido del documento",
                            value=texto,
                            height=350,
                            key=f"texto_{materia}_{documento}"
                        )
                    else:
                        st.warning(
                            "No se encontró texto extraíble."
                        )

                except Exception as error:
                    st.error(
                        f"No se pudo leer el PDF: {error}"
                    )

    else:
        st.info(
            "Todavía no tienes documentos guardados "
            "para esta materia."
        )

else:
    st.info("Agrega tu primera materia para comenzar.")
