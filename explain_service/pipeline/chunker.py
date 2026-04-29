def chunk_text(text, chunk_size=1000):
    sentences = text.split(". ")
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) < chunk_size:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk =  sentence + ". "
        
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

    