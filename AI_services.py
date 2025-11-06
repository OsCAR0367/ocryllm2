import os
import base64
import json
from datetime import datetime
import google.generativeai as genai
from mistralai import Mistral
import concurrent.futures
from PIL import Image


class AIServices:
    def __init__(self, mistral_api_key, gemini_api_key):
        # Configurar los clientes de Mistral y Gemini
        self.mistral_client = Mistral(api_key=mistral_api_key)
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite")

    
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
                
                # texto en markdown
                extract_text = response.pages[0].markdown 
                
                all_text.append(f"\n\n## Pagina {idx}\n\n{extract_text}") 

            except Exception as e:
                print(f"Error processing image {image_path}: {e}")
                all_text.append(f"\n\n## Pagina {idx}\n\nError al procesar la imagen.")

        


        combined_text = "\n".join(all_text)

    
        return {
            "text": combined_text
        }
    
    def _analyze_single_image_gemini(self, image_path, page_num):
        """
        Función interna para analizar una sola imagen con Gemini Vision.
        Se ejecutará en un hilo separado.
        """
        try:
            img = Image.open(image_path)
            
            prompt_parts = [
                f"Esta es la página {page_num} de un documento.",
                "Analiza esta única página y describe su contenido clave en formato Markdown.",
                "Si hay gráficos, tablas o diagramas, descríbelos en detalle.",
                "Extrae los puntos principales o el texto más relevante, resumiendo el propósito de la página.",
                img
            ]
            
            response = self.gemini_model.generate_content(prompt_parts)
            
            if hasattr(response, 'text'):
                analysis_text = response.text
            else:
                analysis_text = "No se pudo obtener texto de la respuesta de Gemini."

            
            return f"\n\n## Pagina {page_num} (Análisis Gemini)\n\n{analysis_text}"
        
        except Exception as e:
            print(f"Error processing image with Gemini {image_path}: {e}")
            return f"\n\n## Pagina {page_num} (Análisis Gemini)\n\nError al procesar la imagen con Gemini."

    def analyze_with_gemini_vision(self, image_paths, filename):
        """
        Función: Analiza el contenido de las imágenes usando Gemini Vision
        de forma paralela (concurrente).
        """
        
        all_analysis = []
        
      
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            
            page_numbers = range(1, len(image_paths) + 1)
            
          
            results = executor.map(self._analyze_single_image_gemini, image_paths, page_numbers)
            
            all_analysis = list(results)
        
        combined_analysis = "\n".join(all_analysis)
        
        return {
            "text": combined_analysis
        }