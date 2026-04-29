def get_next_version(filename, index):
    # Pinecone requires a vector for querying. We use a zero vector (dim 1024) to just filter by metadata.
    dummy_vector = [0.0] * 1024
    
    results = index.query(
        vector=dummy_vector,
        filter={"source": filename},
        top_k=100,
        include_metadata=True
    )

    if not results.matches:
        return 1

    versions = []
    for match in results.matches:
        if "version" in match.metadata:
            versions.append(match.metadata["version"])

    if not versions:
        return 1

    return int(max(versions)) + 1
