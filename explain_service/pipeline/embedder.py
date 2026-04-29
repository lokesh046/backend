from .vectordb import pc

def embed_text(text_chunks):
    # Use Pinecone's Inference API for embeddings
    # Make sure your index is created with DIMENSIONS: 1024 to match this model
    response = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=text_chunks,
        parameters={
            "input_type": "passage",
            "truncate": "END"
        }
    )
    
    # Extract the vector values from the response
    return [record.values for record in response]
