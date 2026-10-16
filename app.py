import streamlit as st
from src.database import (
    inicializar_db,
    agregar_materia,
    obtener_materias
)

st.set_page_config(
    page_title="StudyPilot AI",
    page_icon="📚",
    layout="wide"
)

inicializar_db()

st.title("📚 StudyPilot AI")
st.write("Tu asistente inteligente para estudiar diferentes materias.")

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

else:
    st.info("Agrega tu primera materia para comenzar.")