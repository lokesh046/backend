import uuid
from .validator import validate_text
from .chunker import chunk_text
from .embedder import embed_text
from .file_parser import extract_text_from_file
from .vectordb import index
from .metadata import generate_metadata
from .versioning import get_next_version


def ingest_file(file_path, filename):
    raw_text = extract_text_from_file(file_path)

    validated = validate_text(raw_text)

    chunks = chunk_text(validated)

    embeddings = embed_text(chunks)

    version = get_next_version(filename, index)

    metadata = generate_metadata(filename, version=version)

    # Pinecone expects a list of tuples: (id, embedding, metadata)
    # We must add the text chunk to the metadata so we can retrieve it later
    vectors = []
    for i, chunk in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        chunk_metadata = metadata.copy()
        chunk_metadata["text"] = chunk
        vectors.append((chunk_id, embeddings[i], chunk_metadata))

    # Pinecone upsert
    index.upsert(vectors=vectors)

    return {
        "chunks_added" : len(chunks),
        "version": version
    }