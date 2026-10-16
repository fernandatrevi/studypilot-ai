
import json
from urllib import request, error

OLLAMA_URL = "http://localhost:11434/api/chat"
MODELO = "qwen3:1.7b"


def consultar_ollama(mensaje, sistema=None, formato=None):
    if sistema is None:
        sistema = (
            "Eres un profesor universitario paciente y claro. "
            "Responde en español, explica paso a paso y "
            "utiliza ejemplos para facilitar el aprendizaje."
        )

    datos = {
        "model": MODELO,
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": mensaje}
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.3,
            "num_ctx": 4096,
            "num_predict": 1800
        }
    }

    if formato is not None:
        datos["format"] = formato

    solicitud = request.Request(
        OLLAMA_URL,
        data=json.dumps(datos).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with request.urlopen(solicitud, timeout=240) as respuesta:
            resultado = json.loads(
                respuesta.read().decode("utf-8")
            )

    except error.URLError as exc:
        raise RuntimeError(
            "No se pudo conectar con Ollama. "
            "Verifica que esté funcionando."
        ) from exc

    return resultado["message"]["content"]



def preguntar_ia(pregunta, contexto, materia):
    if not contexto.strip():
        return "Primero sube un PDF con texto para comenzar."

    mensaje = f"""
MATERIA: {materia}

MATERIAL DE ESTUDIO:
{contexto[:14000]}

PREGUNTA:
{pregunta}

Eres un profesor universitario especializado en enseñar
de forma clara, completa y paso a paso.

Tu objetivo es que el estudiante realmente comprenda
el tema, no solamente memorice una definición.

ESTRUCTURA DE LA RESPUESTA:

## ¿Qué es?
Explica el concepto con palabras sencillas.

## ¿Cómo funciona?
Explica el procedimiento paso a paso y por qué
se realiza cada paso.

## Ejemplo sencillo
Utiliza un ejemplo fácil de entender.

## Pasos para aplicarlo
Si el tema incluye procedimientos, fórmulas o
programación, explica cómo utilizarlos.

Si incluye código Python, presenta el código
en bloques y explica qué hace cada instrucción.

## ¿Para qué sirve?
Explica su utilidad y cuándo conviene aplicarlo.

## Ejemplo relacionado con mis diapositivas
Utiliza un ejemplo respaldado por el material
y menciona el documento y la página cuando
esa información esté disponible.

## Resumen
Presenta las ideas principales para estudiar.

REGLAS:
- Responde en español.
- Utiliza títulos y subtítulos en Markdown.
- Explica con suficiente profundidad.
- No omitas pasos importantes.
- No inventes información del material.
- Distingue los ejemplos ilustrativos de los del PDF.
- Si algo no aparece en las diapositivas, indícalo.
- Si el estudiante pide una respuesta breve,
  adapta la extensión.
"""

    return consultar_ollama(
        mensaje,
        sistema=(
            "Eres un excelente tutor universitario. "
            "Enseñas con paciencia, ejemplos y procedimientos "
            "detallados. Respondes en Markdown, no en JSON."
        )
    )
