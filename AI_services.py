import os
import base64
import json
from datetime import datetime
import google.generativeai as genai
from mistralai import Mistral
import concurrent.futures
from PIL import Image

from pydantic import BaseModel, Field
from typing import List, Dict, Any

class DocumentMetadata(BaseModel):
    filename: str
    title: str = "Sin título"
    summary: str = "No hay resumen disponible."
    pages: int
    total_graphics: int = 0
    extraction_method: str
    processed_date: str = Field(default_factory=lambda: datetime.now().isoformat())
    pages_with_errors: List[str] = []

class ExtractionResult(BaseModel):
    text: str
    graphics: List[Dict[str, Any]] = []
    metadata: DocumentMetadata

#grafico de barra, lineal, texto. asincrono(fastapi),langgraph para las etapasnodos), langchain conexion a modelos.
class AIServices:
    
    def __init__(self, mistral_api_key, gemini_api_key):
        self.mistral_client = Mistral(api_key=mistral_api_key)
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite")

    

    def _process_single_image_mistral(self, image_path, page_num):
        """Etapa Única de Mistral: OCR Rápido para texto y recolección de IDs de gráficos"""
        try:
            with open(image_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")
            
            response_ocr = self.mistral_client.ocr.process(
                model="mistral-ocr-latest",
                document={"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_data}"},
            )

            page = response_ocr.pages[0]
            text = page.markdown

            graphics = []
            if hasattr(page, 'images') and page.images:
                for img in page.images:
                    graphics.append({
                        "page": page_num,
                        "id": img.id
                    })

            return {
                "page": page_num,
                "text": f"\n\n## Página {page_num}\n\n{text}",
                "graphics_data": graphics, 
                "success": True
            }
        except Exception as e:
            print(f"Error procesando imagen (OCR) {image_path}: {e}")
            return {
                "page": page_num,
                "text": f"\n\n## Página {page_num}\n\nError al procesar la imagen.",
                "graphics_data": [],
                "success": False,
                "error": str(e)
            }

    def extract_with_mistrail_ocr(self, image_paths, filename):
        """Orquestador de Mistral: Solo OCR en paralelo. Devuelve Pydantic."""
        print(f"Procesando {len(image_paths)} páginas con Mistral OCR...")
        all_text = []
        all_graphics_data = [] 
        pages_with_errors = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor: 
            page_numbers = range(1, len(image_paths) + 1)
            results = executor.map(self._process_single_image_mistral, image_paths, page_numbers)
        
        for result in list(results):
            all_text.append(result["text"])
            all_graphics_data.extend(result["graphics_data"])
            if not result["success"]:
                pages_with_errors.append(f"P{result['page']}")

        print(f"Extracción OCR completa. {len(all_graphics_data)} gráficos/imágenes encontrados.")
        
            
        final_combined_text = "".join(all_text)

        metadata_instance = DocumentMetadata(
            filename=filename,
            title=f"{filename}",
            summary="Texto extraído con Mistral OCR.",
            pages=len(image_paths),
            total_graphics=len(all_graphics_data),
            extraction_method="Mistral OCR",
            pages_with_errors=pages_with_errors
        )
        
        result_instance = ExtractionResult(
            text=final_combined_text,
            graphics=all_graphics_data,
            metadata=metadata_instance
        )
        
        print("✓ Extracción Mistral OCR completa.")
        try:
            return result_instance.model_dump()
        except AttributeError:
            return result_instance.dict()

    
    
    def _analyze_single_image_gemini(self, image_path, page_num):
        """Analiza imagen Y devuelve lista JSON de gráficos"""
        try:
            img = Image.open(image_path)
            prompt_parts = [
f"""--- INSTRUCCIONES ---
1. Analiza la página {page_num} y describe su contenido clave en formato Markdown. Describe texto, propósito, etc.
2. Busca gráficos, tablas o diagramas.
3. Responde en el siguiente formato EXACTO, sin texto adicional antes o después:

<analysis_markdown>
[análisis completo en Markdown]
</analysis_markdown>

<graphics_json>
[
  {{"type": "tipo de gráfico", "description": "descripción breve del gráfico 1"}},
  {{"type": "tabla", "description": "descripción breve de la tabla 1"}}
]
</graphics_json>

Si no hay gráficos, devuelve una lista vacía [].

--- IMAGEN DE LA PÁGINA ---
""", img
            ]
            response = self.gemini_model.generate_content(prompt_parts)
            return (response.text, True, page_num)
        
        except Exception as e:
            print(f"Error processing image with Gemini {image_path}: {e}")
            return (f"Error al procesar la imagen con Gemini: {e}", False, page_num)

    
    def analyze_with_gemini_vision(self, image_paths, filename):
        """Orquestador de Gemini: Procesa en paralelo, parsea JSON y devuelve Pydantic"""
        
        all_analysis_strings = []
        all_graphics_list = [] 
        pages_with_errors = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            page_numbers = range(1, len(image_paths) + 1)
            results = executor.map(self._analyze_single_image_gemini, image_paths, page_numbers)
            
            for (raw_text, success, page_num) in list(results):
                if not success:
                    pages_with_errors.append(f"P{page_num}")
                    all_analysis_strings.append(f"\n\n## Página {page_num}\n\n{raw_text}")
                    continue

                try:
                    md_part = raw_text.split('<analysis_markdown>')[1].split('</analysis_markdown>')[0].strip()
                    all_analysis_strings.append(f"\n\n## Página {page_num} (Análisis Gemini)\n\n{md_part}")

                    json_part = raw_text.split('<graphics_json>')[1].split('</graphics_json>')[0].strip()
                    graphics_on_page = json.loads(json_part)
                    
                    for graphic in graphics_on_page:
                        graphic['page'] = page_num
                        all_graphics_list.append(graphic)

                except Exception as e:
                    print(f"Error parseando respuesta de Gemini para P{page_num}: {e}. Texto recibido: {raw_text}")
                    all_analysis_strings.append(f"\n\n## Página {page_num}\n\nError al parsear respuesta: {raw_text}")
                    pages_with_errors.append(f"P{page_num}-Parse")

        combined_analysis = "\n".join(all_analysis_strings)

        # --- Generación de Metadatos (Título y Resumen) ---
        doc_title = f"Análisis (Gemini) de {filename}"
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
        
        
        metadata_instance = DocumentMetadata(
            filename=filename,
            title=doc_title,
            summary=doc_summary,
            pages=len(image_paths),
            total_graphics=len(all_graphics_list), 
            extraction_method="Gemini Vision",
            pages_with_errors=pages_with_errors
        )
        
        result_instance = ExtractionResult(
            text=combined_analysis,
            graphics=all_graphics_list,
            metadata=metadata_instance
        )
        
        print("✓ Extracción con Gemini completa.")
        try:
            return result_instance.model_dump()
        except AttributeError:
            return result_instance.dict()