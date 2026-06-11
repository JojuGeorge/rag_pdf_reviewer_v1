from dotenv import load_dotenv
load_dotenv()

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma


from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
from typing import List
from collections import defaultdict
from sentence_transformers import CrossEncoder
from collections import defaultdict

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
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


async def get_similar_contract_reranked(revised_docs,results):
    contract_chunks = defaultdict(list)
    contract_metadata = {}

    for doc, score in results:
        contract_path = doc.metadata.get("contract_path")
        if not contract_path:
            continue

        contract_metadata[contract_path] = doc.metadata
        contract_chunks[contract_path].append(doc.page_content)
        
    if not contract_chunks:
        return None
    
    query_text = "\n".join(doc.page_content for doc in revised_docs[:10])
    
    candidate_contracts=[]
    
    for contract_path, chunks in contract_chunks.items():
        contract_text = "\n".join(chunks[:10])
        
        candidate_contracts.append({
            "path": contract_path, 
            "text": contract_text, 
            "metadata": contract_metadata[contract_path]
        })
        
    pairs = [
        (query_text, candidate["text"]) for candidate in candidate_contracts
    ]
    
    scores = reranker.predict(pairs)
    
    for candidate, score in zip(candidate_contracts, scores):
        candidate["rerank_score"] = float(score)
        
    candidate_contracts.sort(key=lambda x: x["rerank_score"], reverse=True)
    best_candidate = candidate_contracts[0]
    
    return {
        "contract_path": best_candidate["path"],
        "contract_name": best_candidate["metadata"]["contract_name"],
        "rerank_score": best_candidate["rerank_score"]
    }

  

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
        
        results = vector_store.similarity_search_with_score(query_texts, k=50)
        
        if not results:
            return {
                "analysis": "",
                "logs": ["No matching contracts found in Chroma."]
            }
        
        best_doc = await get_similar_contract_reranked(revised_docs=revised_docs, results=results)
        if not best_doc:
            raise HTTPException(
                status_code=404,
                detail="No matched contract metadata found. Re-upload original contracts to Chroma."
            )

        original_doc_path = best_doc["contract_path"]
        matched_contract = original_doc_path
        original_doc_loader = PyPDFLoader(original_doc_path)
        original_docs = original_doc_loader.load()
        
        logs.append(f"Matched contract: {best_doc['contract_name']}")
        
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
                            
                        
