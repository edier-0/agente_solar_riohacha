import os
from google import genai
from google.genai import types

async def obtener_respuesta_gemini(prompt: str, system_instruction: str = None, model_name: str = "gemini-2.5-flash-lite"):
    """
    Se comunica asíncronamente con Gemini usando el nuevo SDK `google-genai`.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no está configurada")

    # Inicializar el cliente
    client = genai.Client(api_key=api_key)

    # Configurar instrucciones del sistema si se proporcionan
    config = None
    if system_instruction:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3, # Baja temperatura para respuestas más precisas
            response_mime_type="application/json" # Como los agentes piden JSON, lo dejamos base o podemos inyectarlo luego, mejor no ponerlo aquí global.
        )
        # Quitamos response_mime_type global para que sirva para chat también.
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3,
        )

    try:
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config
        )
        return response.text
    except Exception as e:
        print(f"Error al conectar con Gemini: {e}")
        return "Lo siento, hubo un error al procesar tu solicitud con el modelo de IA."