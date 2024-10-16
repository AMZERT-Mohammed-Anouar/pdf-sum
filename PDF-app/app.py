from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import os
import re
from transformers import pipeline

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the summarization model
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

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

def searchInPDF_english(pdf_path, key):
    occurrences = 0
    pages_with_lines = {}

    doc = fitz.open(pdf_path)
    for pno in range(len(doc)):
        page = doc[pno]
        content = page.get_text("text")
        lines = content.splitlines()
        
        for line_number, line in enumerate(lines):
            if key.lower() in line.lower():
                occurrences += line.lower().count(key.lower())
                
                if pno + 1 not in pages_with_lines:
                    pages_with_lines[pno + 1] = []
                pages_with_lines[pno + 1].append(line_number + 1)

    return occurrences, pages_with_lines

# Updated French search function - Improved to detect occurrences more accurately
def searchInPDF_french(pdf_path, key):
    occurrences = 0
    pages_with_lines = {}
    phrase_pattern = re.compile(re.escape(key), re.IGNORECASE)

    # Open the PDF file using PyMuPDF
    doc = fitz.open(pdf_path)

    for pno in range(len(doc)):
        page = doc[pno]
        content = page.get_text("text")
        
        # Split content by lines
        lines = content.splitlines()
        
        # Check for occurrences line by line and store matches
        for line_num, line in enumerate(lines, start=1):
            # Find all matches in the current line
            matches = list(phrase_pattern.finditer(line))
            match_count = len(matches)
            occurrences += match_count

            if match_count > 0:
                # Store line number in dictionary
                if pno + 1 not in pages_with_lines:
                    pages_with_lines[pno + 1] = []
                pages_with_lines[pno + 1].append(line_num)

        # Full page check - to handle multi-line matches
        page_content = ' '.join(lines)
        matches_full_page = list(phrase_pattern.finditer(page_content))
        if len(matches_full_page) > len(matches):  # Capture cases missed in the line-by-line search
            for match in matches_full_page:
                match_start = match.start()
                char_count = 0
                for line_num, line in enumerate(lines, start=1):
                    char_count += len(line) + 1  # Include line breaks
                    if char_count >= match_start:
                        if pno + 1 not in pages_with_lines:
                            pages_with_lines[pno + 1] = []
                        if line_num not in pages_with_lines[pno + 1]:
                            pages_with_lines[pno + 1].append(line_num)
                        break

    return occurrences, pages_with_lines

@app.route("/search", methods=["POST"])
def search():
    try:
        pdf_path = get_latest_pdf()
        print(f"Using PDF file for search: {pdf_path}")
        
        data = request.json
        query = data.get("query")
        language = data.get("language", "english").lower()
        print(f"Received query: {query} in language: {language}")

        pdf_text = convert_pdf_to_text(pdf_path)
        print("PDF text successfully extracted.")

        # Choose the appropriate search function based on language
        if language == "french":
            occurrences, pages_with_lines = searchInPDF_french(pdf_path, query)
        else:
            occurrences, pages_with_lines = searchInPDF_english(pdf_path, query)
        
        formatted_pages_with_lines = ", ".join([f"{page} (lines {', '.join(map(str, lines))})" 
                                               for page, lines in pages_with_lines.items()])

        response_data = {
            "summary": summarize_text(pdf_text),  # Add summary to the response
            "occurrences": occurrences,
            "pages_with_lines": formatted_pages_with_lines,
            "search_result": "Query found in PDF text." if occurrences > 0 else "Query not found in PDF text."
        }

        return jsonify(response_data)

    except FileNotFoundError as fnf_error:
        print(f"Error: {fnf_error}")
        return jsonify({"error": str(fnf_error)}), 400
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# Function to summarize the extracted PDF text
def summarize_text(text):
    # Handle cases where text might be too long for summarization
    max_length = 1024  # Maximum tokens for the model
    if len(text) > max_length:
        text = text[:max_length]  # Truncate to fit model input

    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
    return summary[0]['summary_text']  # Return the summary text

if __name__ == "__main__":
    app.run(port=5000)

