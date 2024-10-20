from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import os
from transformers import PegasusForConditionalGeneration, PegasusTokenizer, pipeline
from sentence_transformers import SentenceTransformer, util
from flask_cors import CORS
from langdetect import detect  
import re

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load Pegasus model for summarization
model_name = "google/pegasus-large"
model = PegasusForConditionalGeneration.from_pretrained(model_name)
tokenizer = PegasusTokenizer.from_pretrained(model_name, use_fast=True)
summarizer = pipeline("text2text-generation", model=model, tokenizer=tokenizer)

# Load Sentence Transformer for embeddings
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

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
        for i in range(len(doc)):
            page = doc[i]
            page_text = page.get_text()
            if page_text:
                text += page_text
            else:
                print(f"Warning: Page {i + 1} contains no text.")
    except Exception as e:
        print(f"Error reading the PDF file: {e}")
        raise
    return text

def quick_filter_chunks(text_chunks, query):
    filtered_chunks = []
    for idx, chunk in enumerate(text_chunks):
        if re.search(re.escape(query), chunk, re.IGNORECASE):
            filtered_chunks.append((idx, chunk))
    return filtered_chunks

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query', '')

    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        pdf_path = get_latest_pdf()
        text = convert_pdf_to_text(pdf_path)
        sentences = text.split('. ')  # Split text into sentences

        # Detect the language of the extracted text
        language = detect(text)  
        print(f"Detected Language: {language}")

        # Encode sentences and the query
        sentence_embeddings = embedding_model.encode(sentences, convert_to_tensor=True)
        query_embedding = embedding_model.encode(query, convert_to_tensor=True)

        # Compute cosine similarities
        similarities = util.pytorch_cos_sim(query_embedding, sentence_embeddings)[0]
        matched_indices = similarities.argsort(descending=True)[:5]  

        matched_text_info = []
        line_numbers = []
        total_pages = len(fitz.open(pdf_path))

        for index in matched_indices:
            matched_text_info.append({
                "chunk_index": index.item(),
                "similarity_score": similarities[index].item(),
                "text": sentences[index].strip()
            })

            # Find the page and line number for each matched sentence
            page_num = -1
            line_num = -1
            for page_index in range(total_pages):
                page = fitz.open(pdf_path)[page_index]
                page_text = page.get_text()
                
                # Normalize line breaks and strip whitespace
                page_lines = [line.strip() for line in page_text.splitlines() if line.strip()]
                
                # Find matching sentence in the page text
                if matched_text_info[-1]["text"] in page_text:
                    page_num = page_index + 1  # Page numbers start from 1
                    
                    # Try to find the line number
                    for line_index, line in enumerate(page_lines):
                        if matched_text_info[-1]["text"] == line:
                            line_num = line_index + 1  # Line numbers start from 1
                            break
                    break

            line_numbers.append({
                "chunk_index": matched_text_info[-1]["chunk_index"],
                "page": page_num,
                "line": line_num
            })

        # Combine matched text info with line numbers
        for match in matched_text_info:
            match["line_info"] = next((line for line in line_numbers if line["chunk_index"] == match["chunk_index"]), None)

        return jsonify({
            "matched_text_info": matched_text_info,
            "total_matches": len(matched_text_info), 
            "total_pages": total_pages  
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/summarize', methods=['POST'])
def summarize():
    try:
        pdf_path = get_latest_pdf()
        pdf_text = convert_pdf_to_text(pdf_path)
        summary = summarize_text(pdf_text)
        return jsonify({"summary": summary})
    except FileNotFoundError as fnf_error:
        return jsonify({"error": str(fnf_error)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def summarize_text(text):
    max_token_length = 512  # Token length for splitting large text
    chunks = [text[i:i + max_token_length] for i in range(0, len(text), max_token_length)]
    
    summaries = []
    for chunk in chunks:
        try:
            summary = summarizer(chunk, max_length=150, min_length=30, do_sample=True)
            generated_text = summary[0]['generated_text']
            sentences = generated_text.split('.')

            # Remove duplicate or redundant sentences
            unique_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and sentence not in unique_sentences:
                    unique_sentences.append(sentence)

            summaries.append(". ".join(unique_sentences))
        except Exception as e:
            print(f"Error during summarization: {e}")
            raise e

    return " ".join(summaries)

if __name__ == "__main__":
    print("Starting the Flask application...")
    app.run(port=5000)
