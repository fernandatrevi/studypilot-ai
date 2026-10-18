import json
import socket
from urllib import request, error

OLLAMA_URL = 'http://localhost:11434/api/chat'
MODELO = 'qwen3:1.7b'


def consultar_ollama(mensaje, sistema=None, formato=None, timeout=75,
                    num_predict=1800, num_ctx=4096):
    if sistema is None:
        sistema = ('Eres un profesor universitario paciente y claro. '
                   'Responde en español, explica paso a paso y utiliza ejemplos.')
    datos = {
        'model': MODELO,
        'messages': [{'role': 'system', 'content': sistema},
                     {'role': 'user', 'content': mensaje}],
        'stream': False,
        'think': False,
        'options': {'temperature': 0.3, 'num_ctx': num_ctx,
                    'num_predict': num_predict},
    }
    if formato is not None:
        datos['format'] = formato
    solicitud = request.Request(OLLAMA_URL,
        data=json.dumps(datos).encode('utf-8'),
        headers={'Content-Type': 'application/json'})
    try:
        with request.urlopen(solicitud, timeout=timeout) as respuesta:
            resultado = json.loads(respuesta.read().decode('utf-8'))
    except (socket.timeout, TimeoutError) as exc:
        raise RuntimeError(f'Ollama tardó más de {timeout} segundos. Intenta con menos preguntas.') from exc
    except error.HTTPError as exc:
        raise RuntimeError(f'Ollama devolvió un error HTTP {exc.code}.') from exc
    except error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            raise RuntimeError(f'Ollama tardó más de {timeout} segundos.') from exc
        raise RuntimeError('No se pudo conectar con Ollama. Verifica que esté funcionando.') from exc
    try:
        return resultado['message']['content']
    except (KeyError, TypeError) as exc:
        raise RuntimeError('Ollama devolvió una respuesta incompleta.') from exc


def preguntar_ia(pregunta, contexto, materia):
    if not contexto.strip():
        return 'Primero sube un PDF con texto para comenzar.'
    mensaje = f'''MATERIA: {materia}
MATERIAL DE ESTUDIO:
{contexto[:14000]}
PREGUNTA:
{pregunta}

Explica en español con Markdown: qué es, cómo funciona, ejemplo sencillo,
pasos para aplicarlo, para qué sirve, relación con mis diapositivas y resumen.
No inventes información del PDF. Distingue conocimiento general de contenido
respaldado por el PDF. Adapta la extensión a la pregunta.'''
    return consultar_ollama(mensaje,
        sistema='Eres un tutor universitario claro y paciente. Responde en Markdown.',
        timeout=120)
