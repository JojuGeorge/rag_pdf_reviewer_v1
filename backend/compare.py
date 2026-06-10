from dotenv import load_dotenv
load_dotenv()

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma


from pathlib import Path
from fastapi import APIRouter, UploadFile, File
import shutil
from typing import List

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# retriever = get_retriever()
router=APIRouter()

BASE_DIR = Path(__file__).resolve().parent

UPLOADS_FOLDER = BASE_DIR.parent / "data" / "uploads"
Path(UPLOADS_FOLDER).mkdir(parents=True, exist_ok=True)

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

# AI legal summary prompt
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a senior legal contract reviewer.

            Compare these contracts and generate:

            1. Executive summary
            2. Critical legal risks
            3. Financial risks
            4. Liability changes
            5. Termination changes
            6. Compliance risks
            7. Final recommendation
            """
        ),
        (
            "human",
            """
            ORIGINAL:
            {original_text}

            REVISED:
            {revised_text}
            """
        )
    ]
)

@router.post("/analyze")
async def compary(files: List[UploadFile] = File(...)):
    logs = []
    uploaded_files=[]
    matched_contract = None
    analysis = ""
    results_data=[]
    
    for file in files:
        if not file.filename.endswith(".pdf"):
            continue            
        
        destination = (
            Path(UPLOADS_FOLDER) / file.filename
        )
        
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )
        uploaded_files.append(file.filename)
        
        
        logs.append(f"\n\nProcessing: {file.filename}")
        
        loader = PyPDFLoader(str(destination))
        revised_docs = loader.load()
        
        logs.append(f"Loaded {len(revised_docs)} pages")
        
        query_texts = "\n".join([doc.page_content for doc in revised_docs[:3]])
        
        logs.append("Searching vector database...")
        
        results = vector_store.similarity_search_with_score(query_texts, k=5)
        
        if not results:
            return {
                "analysis": "",
                "logs": ["No matching contracts found in Chroma."]
            }
        
        best_doc, score = results[0]
        original_doc_path = best_doc.metadata["contract_path"]
        matched_contract = original_doc_path
        original_doc_loader = PyPDFLoader(original_doc_path)
        original_docs = original_doc_loader.load()
        
        logs.append(f"Matched contract: {best_doc.metadata['contract_name']}"
)
        
        original_text = "\n".join(
            [doc.page_content for doc in original_docs]
        )

        revised_text = "\n".join(
            [doc.page_content for doc in revised_docs]
        )
        
        logs.append("Running legal analysis...")
        
        chain = prompt | llm
        response = chain.invoke({
            "original_text": original_text,
            "revised_text": revised_text,
        })
        analysis = response.content
        
        logs.append("Analysis Done")
        
        results_data.append({
            "revised_contract_name":file.filename ,
            "matched_contract": matched_contract,
            "analysis": analysis
        })
        
    return {
        "results": results_data,
        "logs": logs
    }
                            
                        