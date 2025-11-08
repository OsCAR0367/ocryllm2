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
        self.mistral_client = Mistral(api_key=mistral_api_key)
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite")

    
    def _process_single_image_mistral(self, image_path, page_num):
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
            extract_text = response.pages[0].markdown 
            return f"\n\n## Pagina {page_num}\n\n{extract_text}"

        except Exception as e:
            print(f"Error processing image with Mistral {image_path}: {e}")
            return f"\n\n## Pagina {page_num}\n\nError al procesar la imagen."

    
    def extract_with_mistrail_ocr(self, image_paths, filename):
        
        all_text = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            page_numbers = range(1, len(image_paths) + 1)
            results = executor.map(self._process_single_image_mistral, image_paths, page_numbers)
            all_text = list(results)
        
        combined_text = "\n".join(all_text)

        result_data = {
            "text": combined_text,
            "graphics": [], 
            "metadata": {
                "filename": filename,
                "title": f"Texto extraído de {filename}",
                "pages": len(image_paths),
                "extraction_method": "Mistral OCR",
                "processed_date": datetime.now().isoformat()
            }
        }
        return result_data

        
    def _analyze_single_image_gemini(self, image_path, page_num):
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
        
        all_analysis = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            page_numbers = range(1, len(image_paths) + 1)
            results = executor.map(self._analyze_single_image_gemini, image_paths, page_numbers)
            all_analysis = list(results)
        
        combined_analysis = "\n".join(all_analysis)

        doc_title = f"Análisis de {filename}"
        doc_summary = "No se pudo generar el resumen."

        try:
            metadata_prompt = f"""
            Basado en el siguiente análisis de un documento, genera un título conciso y un resumen corto (2-3 frases).

            TEXTO DEL DOCUMENTO:
            {combined_analysis}

            ---
            RESPUESTA SOLICITADA:
            Título: [Escribe el título aquí]
            Resumen: [Escribe el resumen aquí]
            """
            
            metadata_response = self.gemini_model.generate_content(metadata_prompt)
            
            for line in metadata_response.text.split('\n'):
                if line.startswith("Título:"):
                    doc_title = line.replace("Título:", "").strip()
                if line.startswith("Resumen:"):
                    doc_summary = line.replace("Resumen:", "").strip()
        except Exception as e:
            print(f"Error al generar metadatos con Gemini: {e}")
        
        result_data = {
            "text": combined_analysis,
            "graphics": [], 
            "metadata": {
                "filename": filename,
                "title": doc_title,
                "summary": doc_summary,
                "pages": len(image_paths),
                "extraction_method": "Gemini Vision",
                "processed_date": datetime.now().isoformat()
            }
        }
        return result_data