# ai_core/rag_engine.py

import os
import google.generativeai as genai
import chromadb
from chromadb.utils import embedding_functions
from database import reports_collection 
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# FIX: Using 'gemini-2.5-pro' for superior reasoning over Flash.
MODEL_NAME = "gemini-2.5-pro" 

if not GEMINI_API_KEY:
    # This check ensures the configuration step does not crash the server on startup
    pass 

genai.configure(api_key=GEMINI_API_KEY)

# Initialize ChromaDB 
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Use Sentence Transformers for embeddings 
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Get or create the collection for medical reports
collection = chroma_client.get_or_create_collection(
    name="medical_reports",
    embedding_function=sentence_transformer_ef
)

# --- Helper: Add Report to Vector DB (Necessary for RAG) ---
async def index_report(report_id: str, text_content: str, metadata: dict):
    """
    Splits a report into chunks and saves them to ChromaDB for RAG retrieval.
    """
    if not text_content:
        return

    # Simple chunking strategy
    chunk_size = 500
    chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size)]
    
    ids = [f"{report_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [metadata for _ in range(len(chunks))]

    collection.upsert(
        documents=chunks,
        ids=ids,
        metadatas=metadatas
    )
    print(f"Indexed report {report_id} into {len(chunks)} chunks.")

# --- Main RAG Function (Analysis and Medicine Suggestion) ---
async def get_rag_response(query: str, user_email: str) -> str:
    """
    Retrieves patient data and asks the specialized LLM to provide analysis and medicine suggestions.
    """
    try:
        # 1. Retrieve relevant documents from Chroma
        results = collection.query(
            query_texts=[query],
            n_results=3,
            where={"owner_email": user_email} 
        )

        retrieved_context = ""
        if results['documents'] and results['documents'][0]:
            retrieved_context = "\n\n".join(results['documents'][0])
        
        # 2. Construct Prompt for Medical Analysis
        if not retrieved_context:
            system_instruction = (
                "You are ArogyaAI, a helpful, GENERAL medical assistant. "
                "The user has no relevant medical records. Answer the user's query "
                "based on general public knowledge. Always add a strong medical disclaimer."
            )
            context_block = "No specific medical records found."
        else:
            system_instruction = (
                "You are ArogyaAI, a specialized medical AI assistant. "
                "ANALYZE the retrieved patient reports and history to answer the user's question. "
                "FOCUS on extracting key findings, diagnoses, and medical actions. "
                "If the query relates to symptoms or treatment, suggest only *GENERAL* (non-prescription, non-specific dosage) "
                "recommendations and common OTC medicines related to the reported conditions. "
                "Keep answers concise, actionable, and informative. Always conclude with a mandatory medical disclaimer."
            )
            context_block = f"--- RETRIEVED PATIENT MEDICAL CONTEXT ---\n{retrieved_context}\n---------------------------------"

        full_prompt = f"{system_instruction}\n\n{context_block}\n\nUser Question: {query}"

        # 3. Generate Response (Using the corrected model name)
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(full_prompt)
        
        return response.text

    except Exception as e:
        print(f"RAG Error: {e}")
        return "I'm sorry, I encountered an error analyzing your records. Please ensure your GEMINI_API_KEY is correct and try again."

# --- Summary Function ---
async def get_summary_response(user_email: str) -> str:
    try:
        results = collection.query(
            query_texts=["general health history diagnosis treatment lab results"],
            n_results=10, 
            where={"owner_email": user_email}
        )

        retrieved_context = ""
        if results['documents'] and results['documents'][0]:
            retrieved_context = "\n\n".join(results['documents'][0])
        
        if not retrieved_context:
            return "You haven't uploaded any medical reports yet. Please upload a few reports before requesting a summary."

        prompt = (
            "You are ArogyaAI, the patient's personal medical record summarization assistant. "
            "Analyze the following medical record excerpts and provide a concise, professional summary "
            "of the patient's current health status. Structure your response into 3 sections:\n\n"
            "1. **Key Diagnoses/Findings:** List the most important health concerns or lab results.\n"
            "2. **Recent Actions:** Note any recent prescriptions, treatments, or recommendations.\n"
            "3. **General Status:** Provide a single concluding sentence on the overall health state.\n\n"
            "--- MEDICAL RECORDS CONTEXT ---\n"
            f"{retrieved_context}"
            "\n---------------------------------"
        )
        
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"Summary Error: {e}")
        return "I am unable to generate the comprehensive summary at this time due to a processing error."