from .vectordb import index, pc
from typing import Tuple, List

def retrieve(query: str, top_k: int = 3) -> Tuple[str, List[str], float]:

    # Embed the query using Pinecone Inference API
    # input_type must be "query" when querying
    response = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=[query],
        parameters={
            "input_type": "query",
            "truncate": "END"
        }
    )
    query_embedding = response[0].values

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )

    if not results.matches:
        return "", [], 0.0

    documents = []
    sources = set()
    scores = []

    for match in results.matches:
        if "text" in match.metadata:
            documents.append(match.metadata["text"])
        if "source" in match.metadata:
            sources.add(match.metadata["source"])
        scores.append(match.score)

    context = "\n\n".join(documents)
    source_list = list(sources)

    # Pinecone cosine similarity score is typically 0 to 1
    if len(scores) == 0:
        avg_score = 0.0
    else:
        avg_score = sum(scores) / len(scores)

    # Scale the raw score to a more user-friendly 80-99% range
    base_confidence = 80.0
    confidence = round(base_confidence + (max(0, avg_score) * 19.99), 2)

    return context, source_list, confidence

