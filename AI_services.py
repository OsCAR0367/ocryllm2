import os
import base64
import json
from datetime import datetime
import google.generativeai as genai
from mistralai import Mistral

class AIServices:
    def __init__(self, mistral_api_key, gemini_api_key):
        # Configurar los clientes de Mistral y Gemini
        self.mistral_client = Mistral(api_key=mistral_api_key)
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel("gemini-2.5-flash")
    
    def extract_with_mistrail_ocr(self, image_paths, filename):
        "Funcion:Extract text in JSON from image using Mistral OCR model"

        all_text = []
        graphics_found = []

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
                extract_text = response.text
                all_text.append(f"\n\n## Pagina {idx}\n\n{extract_text}") 

                if any(k in extract_text.lower() for k in ["chart", "graph", "diagram", "tabla","gráfico"]):
                    graphics_found.append({
                        "page": idx,
                        "description": "grafico detectado en la pagina",
                        "type": "detected_in_text"
                    })
            except Exception as e:
                print(f"Error processing image {image_path}: {e}")
                all_text.append(f"\n\n## Pagina {idx}\n\nError al procesar la imagen.")

        return {
            "text": "\n".join(all_text),
            "graphics": graphics_found,
            "metadata": {
                "filename": filename,
                "pages": len(image_paths),
                "extraction_method": "mistral_ocr",
                "processed_date": datetime.now().isoformat(),
                "title": self._extract_title(all_text[0] if all_text else "")
            }
        }
    
    def _extract_title(self, text):
        """Extrae un título simple del contenido"""
        return text.split("\n")[0][:100] if text else "Sin título"

























