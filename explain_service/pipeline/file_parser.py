import os
import json
import pandas as pd
from pypdf import PdfReader
from docx import Document

def extract_text_from_file(file_path):

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt" or ext == ".md":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    elif ext == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join([page.extract_text() or "" for page in reader.pages])

    elif ext == ".docx":
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    elif ext == ".csv":
        df = pd.read_csv(file_path)
        return df.to_string()

    elif ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, indent=2)

    else:
        raise ValueError("Unsupported file type.")