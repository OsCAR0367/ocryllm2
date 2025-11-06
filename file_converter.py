import os
import io
from PIL import Image
from pdf2image import convert_from_path
from pptx import Presentation
from docx import Document
import fitz  


class FileConverter:
    """Converts various file types to text."""

    def __init__(self, upload_folder='uploads', output_folder='outputs'):
        self.upload_folder = upload_folder
        self.output_folder = output_folder
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)
    
    def convert_to_images(self, file_path, file_type):
        """Converts a file to images 1 per page."""

        if file_type == 'pdf':
            return self._convert_pdf(file_path)
        if file_type == 'docx':
            return self._convert_docx(file_path)
        if file_type == 'pptx':
            return self._convert_pptx(file_path)
        else:
            raise ValueError("Tipo de archivo no soportado")
    
    def _convert_pdf(self, pdf_path):

        images = []
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]

        with fitz.open(pdf_path) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=300) 

                output_path = os.path.join(
                    self.output_folder,
                    f"{base_name}_page_{page_num + 1}.png"
                )
                pix.save(output_path)
                images.append(output_path)
        
        return images
    
    def _convert_docx(self, docx_path):

        try:
            from docx2pdf import convert

            base_name = os.path.splitext(os.path.basename(docx_path))[0]
            pdf_path = os.path.join(self.output_folder, f"{base_name}.pdf")
            #Convertir de docx a pdf
            convert(docx_path, pdf_path)
            #convertir de pdf a imagenes
            images = self._convert_pdf(pdf_path)
            #Eliminar el pdf temporal
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            return images
        except ImportError:
            raise ImportError("docx2pdf no está instalado.")
    
    def _convert_pptx(self, pptx_path):
        
        try:
            from pptxtopdf import convert
            import os
            
            base_name = os.path.splitext(os.path.basename(pptx_path))[0]
            input_dir = os.path.dirname(pptx_path)
            output_dir = self.output_folder
            
            convert(input_dir, output_dir)
            
            pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
            
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"No se generó el PDF: {pdf_path}")
            
            images = self._convert_pdf(pdf_path)
            
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                
            return images
            
        except ImportError:
            raise ImportError("pptxtopdf no está instalado.")