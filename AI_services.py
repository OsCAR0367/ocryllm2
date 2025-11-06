import os
import base64
import json
from datetime import datetime
import google.generativeai as genai
from mistralai import Mistral
from pydantic import BaseModel
from typing import List, Optional

class GraphicInfo(BaseModel):
    page: int
    description: str

class DocumentAnalysis(BaseModel):
    title: str
    summary: str
    graphics: Optional[List[GraphicInfo]] = []

class AIServices:
    def __init__(self, mistral_api_key, gemini_api_key):
        # Configurar los clientes de Mistral y Gemini
        self.mistral_client = Mistral(api_key=mistral_api_key)
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        
        self.chat_model_name = "mistral-small-latest" 

    
    def extract_with_mistrail_ocr(self, image_paths, filename):
        "Funcion: Extract text, THEN structure it using Mistral Chat"

        all_text = []

        # --- PASO 1: EXTRAER TEXTO (OCR) ---
        # Este bucle solo extrae el texto crudo de cada página
        for idx, image_path in enumerate(image_paths, 1):
            try:
                with open(image_path, "rb") as img_file:
                    image_data = base64.b64encode(img_file.read()).decode("utf-8")
                
                response = self.mistral_client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{image_data}"
                    },
                    include_image_base64=False
                )
                
                # (Arreglo de la sesión anterior)
                extract_text = response.full_text 
                all_text.append(f"\n\n## Pagina {idx}\n\n{extract_text}") 

            except Exception as e:
                print(f"Error processing image {image_path}: {e}")
                all_text.append(f"\n\n## Pagina {idx}\n\nError al procesar la imagen.")

        
        # --- PASO 2: ESTRUCTURAR TEXTO (CHAT) ---
        
        # Combinamos todo el texto extraído en un solo string
        combined_text = "\n".join(all_text)

        # Creamos el prompt para el modelo de chat
        system_prompt = f"""
        Eres un asistente de análisis de documentos. Analiza el texto proporcionado 
        extraído de un documento. El texto incluye marcadores '## Pagina X'.
        
        Tu tarea es:
        1.  Extraer el título principal del documento.
        2.  Generar un resumen breve del contenido total.
        3.  Identificar cualquier gráfico, tabla o diagrama. 
            Usa los marcadores '## Pagina X' para saber en qué página están.

        Tu salida DEBE ser un objeto JSON que siga este esquema:
        {DocumentAnalysis.model_json_schema()}
        """
        
        try:
            # Llamamos a chat.parse() como en la documentación
            chat_response = self.mistral_client.chat.parse(
                model=self.chat_model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": combined_text}
                ],
                response_format=DocumentAnalysis
            )
            
            # chat_response.model es ahora un objeto Pydantic (DocumentAnalysis)
            structured_data = chat_response.model
            
            # Convertimos la lista de gráficos pydantic a lista de diccionarios
            graphics_list = [g.model_dump() for g in structured_data.graphics] if structured_data.graphics else []

            # Devolvemos el diccionario en el formato que app.py espera
            return {
                "text": combined_text, # Devolvemos el texto crudo completo
                "graphics": graphics_list, # Devolvemos los gráficos estructurados
                "metadata": {
                    "filename": filename,
                    "pages": len(image_paths),
                    "extraction_method": "mistral_ocr_then_chat_parse", # Método actualizado
                    "processed_date": datetime.now().isoformat(),
                    "title": structured_data.title, # Título del LLM
                    "summary": structured_data.summary # Resumen del LLM
                }
            }

        except Exception as e:
            print(f"Error structuring text with Mistral Chat: {e}")
            # Si el Chat falla, devolvemos el texto crudo (comportamiento anterior)
            return {
                "text": combined_text,
                "graphics": [],
                "metadata": {
                    "filename": filename,
                    "pages": len(image_paths),
                    "extraction_method": "mistral_ocr_only (Chat failed)",
                    "processed_date": datetime.now().isoformat(),
                    "title": "Sin título (Error en Chat)"
                }
            }


















