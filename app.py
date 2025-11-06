import os
import tempfile
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import AI_services  
from file_converter import FileConverter
from flask_cors import CORS


load_dotenv()

app = Flask(__name__)
CORS(app)

# Crear instancia del servicio de IA
ai_service = AI_services.AIServices(
    mistral_api_key=os.getenv("MISTRAL_API_KEY"),
    gemini_api_key=os.getenv("GEMINI_API_KEY")
)


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        # Obtener archivo y método
        file = request.files.get("file")
        method = request.form.get("method", "mistral")

        if not file:
            return jsonify({"success": False, "error": "No se subió ningún archivo"}), 400

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, file.filename)
            file.save(file_path)

            converter = FileConverter(output_folder=temp_dir)

            if file.filename.lower().endswith(".pdf"):
                image_paths = converter._convert_pdf(file_path)
            elif file.filename.lower().endswith(".pptx"):
                image_paths = converter._convert_pptx(file_path)
            else:
                return jsonify({"success": False, "error": "Formato no soportado (usa PDF o PPTX)"}), 400
            # Ejecutar OCR con Mistral
            result = ai_service.extract_with_mistrail_ocr(image_paths, file.filename)

            return jsonify({"success": True, "data": result})

    except Exception as e:
        print(f"❌ Error en /upload: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
