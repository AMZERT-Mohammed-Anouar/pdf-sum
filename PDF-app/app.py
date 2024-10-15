from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import os
import re

app = Flask(__name__)

def convert_pdf_to_text(pdf_path):
    # Check if the PDF file exists
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The specified PDF file '{pdf_path}' does not exist.")
    
    text = ""
    try:
        # Use PyMuPDF to extract text
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
    except Exception as e:
        print(f"Error reading the PDF file: {e}")
        raise
    return text

def searchInPDF(pdf_path, key):
    occurrences = 0
    found_pages = set()
    matches = []

    # Open the PDF file using PyMuPDF
    doc = fitz.open(pdf_path)

    # Search through each page
    for pno in range(len(doc)):
        page = doc[pno]
        content = page.get_text("text")  # Get the text of the page
        
        # Check if the key (query) is in the text
        if key.lower() in content.lower():  # Case insensitive search
            occurrences += content.lower().count(key.lower())  # Count occurrences of the key
            found_pages.add(pno + 1)  # Page numbers are 1-indexed
            matches.append(f"Found '{key}' on page {pno + 1}")  # Log where the match was found

    return occurrences, list(found_pages), matches

@app.route("/search", methods=["POST"])
def search():
    # Get the request data
    data = request.json
    query = data.get("query")
    
    print(f"Received query: {query}")  # Debug: print the query received

    try:
        # Convert PDF to text
        pdf_text = convert_pdf_to_text("yourfile.pdf")  # Ensure this path is correct
        print("PDF text successfully extracted.")  # Debug: print success message

        # Search for the query in the PDF
        occurrences, found_pages, matches = searchInPDF("yourfile.pdf", query)
        
        # Prepare the response data
        response_data = {
            "pdf_text": pdf_text,  # Include the full extracted text
            "occurrences": occurrences,
            "pages_found": found_pages,
            "search_result": "Query found in PDF text." if occurrences > 0 else "Query not found in PDF text.",
            "matches": matches  # Detailed match information
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error occurred: {e}")  # Print the error to the Flask console
        return jsonify({"error": str(e)}), 500  # Return error as JSON

if __name__ == "__main__":
    app.run(port=5000)
