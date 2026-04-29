import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "financial-knowledge"

# Make sure to create this index in the Pinecone UI: Dimensions 1024, Metric Cosine
index = pc.Index(index_name)