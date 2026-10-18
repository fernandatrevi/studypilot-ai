
import json
from src.tutor import consultar_ollama


def generar_examen(contexto, cantidad=5):
    if not contexto.strip():
        raise ValueError(
            "No hay texto disponible para generar el examen."
        )

    mensaje = f"""
Genera un examen universitario utilizando únicamente el siguiente material.

MATERIAL:
{contexto[:11000]}

Crea exactamente {cantidad} preguntas de opción múltiple.

Devuelve exclusivamente este JSON:
{{
    "preguntas": [
        {{
            "pregunta": "¿Pregunta?",
            "opciones": [
                "Opción A",
                "Opción B",
                "Opción C",
                "Opción D"
            ],
            "correcta": 0,
            "explicacion": "Justificación de la respuesta"
        }}
    ]
}}

REGLAS:
- Cuatro opciones por pregunta.
- Solo una respuesta correcta.
- El campo correcta debe ser un entero entre 0 y 3.
- No inventes información.
- Basa las preguntas en el material.
- Incluye preguntas conceptuales y de aplicación.
"""

    respuesta = consultar_ollama(
        mensaje,
        sistema=(
            "Eres un profesor universitario que genera exámenes. "
            "Devuelve únicamente JSON válido."
        ),
        formato="json"
    )

    resultado = json.loads(respuesta)
    preguntas = resultado.get("preguntas", [])

    validas = []

    for pregunta in preguntas:
        if (
            isinstance(pregunta, dict)
            and isinstance(pregunta.get("pregunta"), str)
            and isinstance(pregunta.get("opciones"), list)
            and len(pregunta["opciones"]) == 4
            and all(
                isinstance(opcion, str)
                for opcion in pregunta["opciones"]
            )
            and type(pregunta.get("correcta")) is int
            and 0 <= pregunta["correcta"] <= 3
            and isinstance(pregunta.get("explicacion"), str)
        ):
            validas.append(pregunta)

    if not validas:
        raise ValueError(
            "La IA no generó preguntas con el formato esperado."
        )

    return validas


def evaluar_examen(preguntas, respuestas):
    resultados = []
    aciertos = 0

    for indice, pregunta in enumerate(preguntas):
        seleccionada = respuestas.get(indice)
        correcta = pregunta["correcta"]
        opciones = pregunta["opciones"]

        es_correcta = seleccionada == correcta

        if es_correcta:
            aciertos += 1

        resultados.append({
            "pregunta": pregunta["pregunta"],
            "opciones": opciones,
            "respuesta_usuario": (
                opciones[seleccionada]
                if (
                    type(seleccionada) is int
                    and 0 <= seleccionada < len(opciones)
                )
                else "Sin responder"
            ),
            "respuesta_correcta": opciones[correcta],
            "acierto": es_correcta,
            "explicacion": pregunta["explicacion"]
        })

    total = len(preguntas)

    return {
        "aciertos": aciertos,
        "total": total,
        "calificacion": (
            round(aciertos / total * 100, 1)
            if total else 0
        ),
        "resultados": resultados
    }
