from fastapi import FastAPI
from ingestion import router as ingestion_router
from compare import router as compare_router

app = FastAPI()

app.include_router(ingestion_router)
app.include_router(compare_router)