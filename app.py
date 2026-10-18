import streamlit as st
from src.database import (
    obtener_errores_interactivos,
    inicializar_db,
    agregar_materia,
    obtener_materias,
    guardar_resultados,
    obtener_errores,
    obtener_estadisticas
)

from src.documents import (
    guardar_pdf,
    listar_pdfs,
    leer_pdf,
    obtener_imagen_pagina,
    contar_paginas,
    obtener_contexto
)

from src.tutor import preguntar_ia
from src.quiz import generar_examen, evaluar_examen


# CONFIGURACIÓN
st.set_page_config(
    page_title="StudyPilot AI",
    page_icon="📚",
    layout="wide"
)

inicializar_db()

st.title("📚 StudyPilot AI")
st.write(
    "Tu asistente inteligente para estudiar diferentes materias."
)


# MATERIAS
st.subheader("Mis materias")

nueva_materia = st.text_input("Nombre de la materia")

if st.button("Agregar materia"):
    nombre = nueva_materia.strip()

    if nombre:
        agregar_materia(nombre)
        st.success("Materia guardada correctamente.")
        st.rerun()
    else:
        st.warning("Escribe el nombre de una materia.")


materias = obtener_materias()

if not materias:
    st.info("Agrega tu primera materia para comenzar.")
    st.stop()


materia = st.selectbox(
    "Selecciona una materia",
    materias
)

st.subheader(f"Estudiar: {materia}")


# MODOS DE ESTUDIO
opcion = st.radio(
    "¿Qué quieres hacer?",
    [
        "Explicar un tema",
        "Practicar preguntas",
        "Simular un examen",
        "Repasar errores"
    ]
)

st.divider()


# DOCUMENTOS
st.subheader("📄 Documentos de estudio")

archivo_pdf = st.file_uploader(
    "Sube tus diapositivas o apuntes",
    type=["pdf"],
    key=f"pdf_{materia}"
)

if archivo_pdf is not None:
    if st.button("Guardar PDF"):
        try:
            ruta = guardar_pdf(materia, archivo_pdf)
            st.success(f"Documento guardado: {ruta.name}")
            st.rerun()
        except Exception as error:
            st.error(f"No se pudo guardar: {error}")


documentos = listar_pdfs(materia)

st.subheader("Mis documentos")

if documentos:
    st.write(
        f"Tienes {len(documentos)} documento(s) guardado(s)."
    )

    for documento in documentos:
        with st.expander(f"📄 {documento}"):

            try:
                total_paginas = contar_paginas(
                    materia,
                    documento
                )

                if total_paginas > 0:
                    pagina = st.number_input(
                        "Número de página",
                        min_value=1,
                        max_value=total_paginas,
                        value=1,
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
                    f"No se pudo mostrar el PDF: {error}"
                )

            if st.button(
                "Leer texto",
                key=f"leer_{materia}_{documento}"
            ):
                try:
                    texto = leer_pdf(materia, documento)

                    if texto.strip():
                        st.session_state[
                            f"texto_{materia}_{documento}"
                        ] = texto
                    else:
                        st.warning(
                            "No se encontró texto extraíble."
                        )

                except Exception as error:
                    st.error(str(error))

            texto_guardado = st.session_state.get(
                f"texto_{materia}_{documento}"
            )

            if texto_guardado:
                st.text_area(
                    "Texto del documento",
                    value=texto_guardado,
                    height=300,
                    key=f"mostrar_{materia}_{documento}"
                )

else:
    st.info(
        "Todavía no tienes documentos guardados."
    )


# CONTEXTO
contexto = obtener_contexto(materia)

st.divider()


# EXPLICAR UN TEMA
if opcion == "Explicar un tema":

    st.header("🧠 Tutor inteligente")

    pregunta = st.text_area(
        "¿Qué tema quieres aprender?",
        placeholder="Ejemplo: Explícame qué es LIME"
    )

    if st.button("Preguntar a la IA"):

        if not pregunta.strip():
            st.warning("Escribe una pregunta.")

        elif not contexto.strip():
            st.warning(
                "Primero sube un PDF con texto."
            )

        else:
            with st.spinner("Preparando explicación..."):
                try:
                    respuesta = preguntar_ia(
                        pregunta,
                        contexto,
                        materia
                    )

                    st.session_state["respuesta_tutor"] = respuesta

                except Exception as error:
                    st.error(
                        f"No se pudo consultar la IA: {error}"
                    )

    if "respuesta_tutor" in st.session_state:
        st.markdown(
            st.session_state["respuesta_tutor"]
        )


# PRACTICAR O SIMULAR EXAMEN
elif opcion in [
    "Practicar preguntas",
    "Simular un examen"
]:

    es_examen = opcion == "Simular un examen"

    if es_examen:
        st.header("📝 Simulador de examen")
    else:
        st.header("✏️ Practicar preguntas")

    cantidad = st.slider(
        "Número de preguntas",
        min_value=3,
        max_value=15,
        value=5
    )

    clave_examen = f"examen_{materia}_{opcion}"
    clave_resultado = f"resultado_{materia}_{opcion}"

    if st.button("Generar preguntas"):

        if not contexto.strip():
            st.warning(
                "Primero sube material de estudio."
            )

        else:
            with st.spinner("Generando preguntas..."):
                try:
                    preguntas = generar_examen(
                        contexto,
                        cantidad
                    )

                    st.session_state[clave_examen] = preguntas
                    st.session_state.pop(
                        clave_resultado,
                        None
                    )

                    st.success(
                        f"Se generaron {len(preguntas)} preguntas."
                    )

                except Exception as error:
                    st.error(
                        f"No se pudo generar el examen: {error}"
                    )

    preguntas = st.session_state.get(
        clave_examen,
        []
    )

    if preguntas:

        st.write(
            f"Responde las siguientes {len(preguntas)} preguntas."
        )

        with st.form(
            key=f"formulario_{materia}_{opcion}"
        ):

            respuestas = {}

            for indice, pregunta in enumerate(preguntas):

                st.markdown(
                    f"**Pregunta {indice + 1}. "
                    f"{pregunta['pregunta']}**"
                )

                opciones = pregunta["opciones"]

                seleccion = st.radio(
                    "Selecciona una respuesta",
                    options=list(range(4)),
                    format_func=lambda x, opciones=opciones: opciones[x],
                    index=None,
                    key=f"respuesta_{materia}_{opcion}_{indice}"
                )

                respuestas[indice] = seleccion

            enviar = st.form_submit_button(
                "Calificar respuestas"
            )

        
        if enviar:
            try:
                resultado = evaluar_examen(
                    preguntas,
                    respuestas
                )

                st.session_state[clave_resultado] = resultado

                try:
                    guardar_resultados(
                        materia,
                        resultado["resultados"]
                    )
                except Exception as error:
                    st.warning(
                        f"Se calculó tu calificación, "
                        f"pero no se pudo guardar el historial: {error}"
                    )

            except Exception as error:
                st.error(
                    f"No se pudo calificar el examen: {error}"
                )

        if resultado:

            st.divider()

            st.subheader("Resultados")

            st.metric(
                "Calificación",
                f"{resultado['calificacion']}%"
            )

            st.write(
                f"Aciertos: {resultado['aciertos']} "
                f"de {resultado['total']}"
            )

            for indice, detalle in enumerate(
                resultado["resultados"],
                start=1
            ):

                with st.expander(
                    f"Pregunta {indice}: "
                    f"{'✅ Correcta' if detalle['acierto'] else '❌ Incorrecta'}"
                ):

                    st.write(
                        f"**Pregunta:** {detalle['pregunta']}"
                    )

                    st.write(
                        f"**Tu respuesta:** "
                        f"{detalle['respuesta_usuario']}"
                    )

                    st.write(
                        f"**Respuesta correcta:** "
                        f"{detalle['respuesta_correcta']}"
                    )

                    st.write(
                        f"**Explicación:** "
                        f"{detalle['explicacion']}"
                    )


# REPASAR ERRORES

# REPASAR ERRORES
elif opcion == "Repasar errores":

    st.header("🔁 Repasar errores")

    estadisticas = obtener_estadisticas(materia)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Preguntas respondidas",
        estadisticas["total"]
    )

    col2.metric(
        "Respuestas correctas",
        estadisticas["aciertos"]
    )

    col3.metric(
        "Porcentaje de aciertos",
        f"{estadisticas['porcentaje']}%"
    )

    errores = obtener_errores_interactivos(materia)

    if not errores:
        st.success("¡Todavía no tienes errores registrados!")

    else:
        st.subheader("Practica las preguntas que fallaste")

        for error in errores:

            with st.expander(error["pregunta"]):

                opciones = error["opciones"]

                if len(opciones) != 4:
                    st.info(
                        "Esta pregunta pertenece a un examen anterior "
                        "y no tiene las cuatro opciones guardadas."
                    )

                    st.write(
                        f"Respuesta correcta: "
                        f"{error['respuesta_correcta']}"
                    )

                    st.write(error["explicacion"])
                    continue

                with st.form(
                    key=f"repaso_form_{error['id']}"
                ):

                    seleccion = st.radio(
                        "Selecciona tu respuesta:",
                        options=opciones,
                        index=None,
                        key=f"repaso_{error['id']}"
                    )

                    comprobar = st.form_submit_button(
                        "Comprobar respuesta"
                    )

                clave = f"resultado_repaso_{error['id']}"

                if comprobar:

                    if seleccion is None:
                        st.warning("Selecciona una respuesta.")

                    else:
                        correcta = (
                            seleccion == error["respuesta_correcta"]
                        )

                        st.session_state[clave] = {
                            "correcta": correcta,
                            "seleccion": seleccion
                        }

                resultado_repaso = st.session_state.get(clave)

                if resultado_repaso:

                    if resultado_repaso["correcta"]:
                        st.success(
                            "¡Correcto! Aprendiste de tu error."
                        )

                    else:
                        st.error(
                            "Respuesta incorrecta. Sigue practicando."
                        )

                    st.write(
                        "**Tu respuesta:**",
                        resultado_repaso["seleccion"]
                    )

                    st.write(
                        "**Respuesta correcta:**",
                        error["respuesta_correcta"]
                    )

                    st.write(
                        "**Explicación:**",
                        error["explicacion"]
                    )
