from dotenv import load_dotenv
load_dotenv()

import uuid

from langchain_community.document_loaders import PyPDFLoader

from langchain_openai import  OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from pathlib import Path
from fastapi import APIRouter, UploadFile, File
import shutil
from typing import List

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent

CONTRACT_FOLDER = BASE_DIR.parent / "data" / "contracts"
Path(CONTRACT_FOLDER).mkdir(parents=True, exist_ok=True)


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

@router.post("/upload-contracts")
async def ingestion(files: List[UploadFile] = File(...)):
    logs = []

    uploaded_files=[]
    for file in files:
        if not file.filename.endswith(".pdf"):
            continue            
        
        destination = (
            Path(CONTRACT_FOLDER) / file.filename
        )
        
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )
        uploaded_files.append(file.filename)
        
        
        logs.append(f"Processing: {file.filename}")
        
        loader = PyPDFLoader(str(destination))
        docs = loader.load()
        
        logs.append(f"Loaded {len(docs)} pages")
        
        chunks = text_splitter.split_documents(docs)
        logs.append(f"Created {len(chunks)} chunks")
        
        # adding metadatas
        for chunk in chunks:
            chunk.metadata.update({
                "contract_name": file.filename,
                "contract_path": str(destination),
            })
                
        vector_store.add_documents(
            documents=chunks,
            ids=[str(uuid.uuid4()) for _ in chunks]
        )
        logs.append("Stored in Chroma")
        
    return {
        "status": "success",
        "uploaded_files": uploaded_files,
        "logs": logs
    }
      
# def get_retriever():
#     retriever = Chroma(
#         collection_name="rag_chroma",
#         persist_directory="./chroma",
#         embedding_function=embedding_model
#     )        
#     return retriever.as_retriever(search_kwargs={"k":5})
        
