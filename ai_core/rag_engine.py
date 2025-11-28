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
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file.")

genai.configure(api_key=GEMINI_API_KEY)

# Initialize ChromaDB (Persistent storage so data survives restarts)
# This will create a folder named 'chroma_db' in your project root
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Use Sentence Transformers for embeddings (matches requirements.txt)
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Get or create the collection for medical reports
collection = chroma_client.get_or_create_collection(
    name="medical_reports",
    embedding_function=sentence_transformer_ef
)

# --- Helper: Add Report to Vector DB ---
async def index_report(report_id: str, text_content: str, metadata: dict):
    """
    Splits a report into chunks and saves them to ChromaDB.
    Call this function immediately after saving a report to MongoDB.
    """
    if not text_content:
        return

    # Simple chunking strategy (can be improved with LangChain later)
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

# --- Main RAG Function ---
async def get_rag_response(query: str, user_email: str) -> str:
    """
    1. Searches ChromaDB for relevant chunks belonging to the user.
    2. Sends the chunks + query to Gemini for an answer.
    """
    try:
        # 1. Retrieve relevant documents from Chroma
        # We filter by 'owner_email' to ensure patients only see THEIR OWN data.
        results = collection.query(
            query_texts=[query],
            n_results=3,
            where={"owner_email": user_email} 
        )

        retrieved_context = ""
        if results['documents']:
            # Flatten list of lists
            retrieved_context = "\n\n".join(results['documents'][0])
        
        # 2. Construct Prompt for Gemini
        if not retrieved_context:
            system_instruction = "You are a helpful medical assistant. The user has no medical records uploaded yet. Answer broadly but advise them to consult a doctor."
            context_block = "No specific medical records found."
        else:
            system_instruction = (
                "You are ArogyaAI, a helpful medical assistant. "
                "Use the following pieces of retrieved medical context to answer the user's question. "
                "If the answer is not in the context, say you don't know based on the records. "
                "Keep answers concise and empathetic."
            )
            context_block = f"--- Retrieved Medical Records ---\n{retrieved_context}\n---------------------------------"

        full_prompt = f"{system_instruction}\n\n{context_block}\n\nUser Question: {query}"

        # 3. Generate Response
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(full_prompt)
        
        return response.text

    except Exception as e:
        print(f"RAG Error: {e}")
        return "I'm sorry, I encountered an error analyzing your records. Please try again later."

# --- Summary Function ---
async def get_summary_response(user_email: str) -> str:
    """
    Retrieves the most recent reports and asks Gemini to summarize the patient's health status.
    """
    try:
        # Fetch the latest 5 chunks from this user's collection
        # Note: Chroma query() requires a query_text, so we use a generic term.
        results = collection.query(
            query_texts=["medical summary diagnosis treatment"],
            n_results=10,
            where={"owner_email": user_email}
        )

        retrieved_context = ""
        if results['documents']:
            retrieved_context = "\n".join(results['documents'][0])
        
        if not retrieved_context:
            return "You haven't uploaded any medical reports yet, so I cannot generate a health summary."

        prompt = (
            f"Based on the following medical record excerpts, provide a concise 3-bullet point summary "
            f"of the patient's recent health status:\n\n{retrieved_context}"
        )
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"Summary Error: {e}")
        return "Unable to generate summary at this time."