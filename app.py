import os
import tempfile
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS 
from dotenv import load_dotenv
import AI_services  
from file_converter import FileConverter


load_dotenv()

app = Flask(__name__)
CORS(app) 

# instancias  de IA
ai_service = AI_services.AIServices(
    mistral_api_key=os.getenv("MISTRAL_API_KEY"),
    gemini_api_key=os.getenv("GEMINI_API_KEY")
)


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        
        file = request.files.get("file")
        # El valor de "method" vendrá del frontend ( "mistral", "gemini", "ambos")
        method = request.form.get("method", "mistral") #

        if not file:
            return jsonify({"success": False, "error": "No se subió ningún archivo"}), 400

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, file.filename)
            file.save(file_path)

            converter = FileConverter(output_folder=temp_dir)

            if file.filename.lower().endswith(".pdf"):
                image_paths = converter._convert_pdf(file_path) #
            elif file.filename.lower().endswith(".pptx"):
                image_paths = converter._convert_pptx(file_path) #
            else:
                return jsonify({"success": False, "error": "Formato no soportado (usa PDF, word o PPTX)"}), 400
            
            
            result_data = {}

            if method == "gemini":
                print("Ejecutando solo Gemini Vision...")
                result_data = ai_service.analyze_with_gemini_vision(image_paths, file.filename)

            elif method == "ambos":
                print("Ejecutando Mistral OCR y Gemini Vision...")
                # (Opcional: puedes ejecutar esto en paralelo si lo deseas)
                result_mistral = ai_service.extract_with_mistrail_ocr(image_paths, file.filename)
                result_gemini = ai_service.analyze_with_gemini_vision(image_paths, file.filename)
                
                # Combinamos los resultados
                combined_text = (
                    f"<h1>Resultados de Mistral OCR (Texto Extraído)</h1>\n"
                    f"{result_mistral['text']}\n\n"
                    f"<br><hr><br>\n\n"
                    f"<h1>Resultados de Gemini Vision (Análisis)</h1>\n"
                    f"{result_gemini['text']}"
                )
                result_data = {"text": combined_text}

            else: # Por defecto, o si method == "mistral"
                # 3. Solo Mistral OCR
                print("Ejecutando solo Mistral OCR...")
                result_data = ai_service.extract_with_mistrail_ocr(image_paths, file.filename) #
            
            # --- FIN DE LA NUEVA LÓGICA ---

            return jsonify({"success": True, "data": result_data}) #

    except Exception as e:
        print(f"❌ Error en /upload: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)