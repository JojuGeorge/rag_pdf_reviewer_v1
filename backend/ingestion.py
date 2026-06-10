from dotenv import load_dotenv
load_dotenv()

import os, uuid

from langchain_community.document_loaders import PyPDFLoader

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

CONTRACT_FOLDER = BASE_DIR.parent / "data" / "contracts"

embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-small",
    chunk_size=200, 
    retry_min_seconds=10
)

text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=250, chunk_overlap=0
)


vector_store = Chroma(
    collection_name="rag_chroma",
    embedding_function=embedding_model,
    persist_directory="./chroma"
)

def ingestion():
    for file in os.listdir(CONTRACT_FOLDER):
        if not file.endswith(".pdf"):
            continue
        
        file_path = os.path.join(CONTRACT_FOLDER, file)
        
        print(f"Processing: {file_path}")
        
        loader = PyPDFLoader(str(file_path))
        docs = loader.load()
        
        chunks = text_splitter.split_documents(docs)
        
        # adding metadatas
        for chunk in chunks:
            chunk.metadata.update({
                "contract_name": file,
                "contract_path": str(file_path),
            })
                
        vector_store.add_documents(
            documents=chunks,
            ids=[str(uuid.uuid4()) for _ in chunks]
        )
        
    print("\n DONE")
      
def get_retriever():
    retriever = Chroma(
        collection_name="rag_chroma",
        persist_directory="./chroma",
        embedding_function=embedding_model
    )        
    return retriever.as_retriever(search_kwargs={"k":5})
        
if __name__ == "__main__":
    ingestion()