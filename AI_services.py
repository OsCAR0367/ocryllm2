import os
import base64
import json
from datetime import datetime
import google.generativeai as genai
from mistralai import Mistral
# NOTA: Ya no se necesitan 'pydantic' ni 'typing'

class AIServices:
    def __init__(self, mistral_api_key, gemini_api_key):
        # Configurar los clientes de Mistral y Gemini
        self.mistral_client = Mistral(api_key=mistral_api_key)
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        # Ya no necesitamos 'self.chat_model_name'
    
    def extract_with_mistrail_ocr(self, image_paths, filename):
        """
        Función: Extrae texto de imágenes usando Mistral OCR
        y lo devuelve en un JSON simple.
        """

        all_text = []

        # --- PASO 1: Extraer texto (OCR) de todas las páginas ---
        for idx, image_path in enumerate(image_paths, 1):
            try:
                with open(image_path, "rb") as img_file:
                    image_data = base64.b64encode(img_file.read()).decode("utf-8")
                
                response = self.mistral_client.ocr.process(  #
                    model="mistral-ocr-latest",
                    document={
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{image_data}"
                    },
                    include_image_base64=False
                )
                
                # --- ESTA ES LA CORRECCIÓN DEFINITIVA ---
                # El atributo .markdown nos da el texto formateado
                extract_text = response.pages[0].markdown 
                
                # Añadimos un encabezado de página
                # El 'extract_text' ya vendrá formateado
                all_text.append(f"\n\n## Pagina {idx}\n\n{extract_text}") 

            except Exception as e:
                print(f"Error processing image {image_path}: {e}")
                all_text.append(f"\n\n## Pagina {idx}\n\nError al procesar la imagen.")

        
        # --- PASO 2: Combinar y devolver el JSON solicitado ---
        
        # Unimos todo el texto de todas las páginas
        combined_text = "\n".join(all_text)

        # Devolvemos el JSON exacto que pediste
        return {
            "text": combined_text
        }