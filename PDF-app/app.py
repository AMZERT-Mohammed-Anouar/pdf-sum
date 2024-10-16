from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf_file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "File must be a PDF"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, "yourfile.pdf")
    file.save(file_path)
    print(f"File uploaded and saved as: {file_path}")
    return jsonify({"message": "File uploaded successfully!"})

def get_latest_pdf():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.pdf')]
    if not files:
        raise FileNotFoundError("No PDF files found in the uploads directory.")
    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(UPLOAD_FOLDER, f)))
    return os.path.join(UPLOAD_FOLDER, latest_file)

def convert_pdf_to_text(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The specified PDF file '{pdf_path}' does not exist.")
    
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
    except Exception as e:
        print(f"Error reading the PDF file: {e}")
        raise
    return text

def searchInPDF(pdf_path, key):
    occurrences = 0
    pages_with_lines = {}  # Dictionary to map pages to their line numbers where the query was found

    doc = fitz.open(pdf_path)
    for pno in range(len(doc)):
        page = doc[pno]
        content = page.get_text("text")
        lines = content.splitlines()  # Split page content by lines
        
        for line_number, line in enumerate(lines):
            if key.lower() in line.lower():
                occurrences += line.lower().count(key.lower())
                
                # Add line numbers to the appropriate page entry in pages_with_lines
                if pno + 1 not in pages_with_lines:
                    pages_with_lines[pno + 1] = []
                pages_with_lines[pno + 1].append(line_number + 1)  # Store line number as 1-indexed

    return occurrences, pages_with_lines

@app.route("/search", methods=["POST"])
def search():
    try:
        pdf_path = get_latest_pdf()
        print(f"Using PDF file for search: {pdf_path}")
        
        data = request.json
        query = data.get("query")
        print(f"Received query: {query}")

        pdf_text = convert_pdf_to_text(pdf_path)
        print("PDF text successfully extracted.")

        occurrences, pages_with_lines = searchInPDF(pdf_path, query)
        
        # Format pages and lines for the response output
        formatted_pages_with_lines = ", ".join([f"{page} (lines {', '.join(map(str, lines))})" 
                                               for page, lines in pages_with_lines.items()])

        response_data = {
            "pdf_text": pdf_text,
            "occurrences": occurrences,
            "pages_with_lines": formatted_pages_with_lines,  # Output pages with lines in the specified format
            "search_result": "Query found in PDF text." if occurrences > 0 else "Query not found in PDF text."
        }

        return jsonify(response_data)

    except FileNotFoundError as fnf_error:
        print(f"Error: {fnf_error}")
        return jsonify({"error": str(fnf_error)}), 400
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000)

