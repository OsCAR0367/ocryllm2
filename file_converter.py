import os
import fitz  
import comtypes.client
import comtypes 

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
        """Convierte PDF a imágenes PNG."""

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
        """Convierte DOCX a imágenes PNG vía PDF intermedio."""
        pdf_path = ""
        
        comtypes.CoInitialize()
        
        try:
            base_name = os.path.splitext(os.path.basename(docx_path))[0]
            pdf_path = os.path.join(self.output_folder, f"{base_name}.pdf")

            docx_path_abs = os.path.abspath(docx_path)
            pdf_path_abs = os.path.abspath(pdf_path)

            word = comtypes.client.CreateObject("Word.Application")
            word.Visible = False
            doc = None
            try:
                doc = word.Documents.Open(docx_path_abs)
                doc.SaveAs(pdf_path_abs, FileFormat=17)
            except Exception as e:
                raise Exception(f"Error durante la conversión de Word: {e}")
            finally:
                if doc:
                    doc.Close(0)
                if word:
                    word.Quit()
            
            print(f"Conversión DOCX completada.")
            
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"comtypes no generó el PDF para DOCX: {pdf_path}")
            
            images = self._convert_pdf(pdf_path)
            
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            return images
        except Exception as e:
            raise Exception(f"Fallo en _convert_docx (path: {pdf_path}): {e}")
        finally:
        
            comtypes.CoUninitialize()

    
    def _convert_pptx(self, pptx_path):
 
        pdf_path = ""
        

        comtypes.CoInitialize()
        
        try:
            base_name = os.path.splitext(os.path.basename(pptx_path))[0]
            pdf_path = os.path.join(self.output_folder, f"{base_name}.pdf")
            
            pptx_path_abs = os.path.abspath(pptx_path)
            pdf_path_abs = os.path.abspath(pdf_path)

            powerpoint = comtypes.client.CreateObject("PowerPoint.Application")
            presentation = None
            try:
                presentation = powerpoint.Presentations.Open(pptx_path_abs, WithWindow=False)
                presentation.SaveAs(pdf_path_abs, 32) # 32 = pptSaveAsPDF
            except Exception as e:
                raise Exception(f"Error durante la conversión de PowerPoint: {e}")
            finally:
                if presentation:
                    presentation.Close()
                if powerpoint:
                    powerpoint.Quit()

            print(f"Conversión PPTX completada.")

            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"comtypes no generó el PDF para PPTX: {pdf_path}")
            
            images = self._convert_pdf(pdf_path)
            
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                
            return images
            
        except Exception as e:
            raise Exception(f"Fallo en _convert_pptx (path: {pdf_path}): {e}")
        finally:
            comtypes.CoUninitialize()