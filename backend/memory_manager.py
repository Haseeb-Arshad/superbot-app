import os
import time
from typing import List, Dict
import chromadb
from chromadb.utils import embedding_functions
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# Ensure you have OPENAI_API_KEY in your environment variables
# For now, we will assume it is set. If not, this will error.

class MemoryManager:
    def __init__(self):
        print("[MemoryManager] Initializing...")
        
        # Initialize ChromaDB Client (Persistent)
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # OpenAI Embedding Function
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )

        # Collections
        # 1. Stream Context: Short-term memory of what the system hears
        self.stream_context = self.chroma_client.get_or_create_collection(
            name="stream_context",
            embedding_function=self.openai_ef
        )
        
        # 2. Long Term History: Persistent knowledge (e.g., browser history, important facts)
        self.long_term_history = self.chroma_client.get_or_create_collection(
            name="long_term_history",
            embedding_function=self.openai_ef
        )
        
        # Initialize LLM (GPT-4o)
        self.llm = ChatOpenAI(
            model_name="gpt-4o",
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0.7
        )
        
        print("[MemoryManager] Ready.")

    def add_memory(self, text: str, source: str, metadata: Dict = {}):
        """
        Adds a memory to the appropriate collection.
        If source is 'system', it goes to stream_context.
        If source is 'browser' or 'user_fact', it goes to long_term_history.
        """
        if not text or not text.strip():
            return

        timestamp = time.time()
        meta = metadata.copy()
        meta.update({"timestamp": timestamp, "source": source})
        
        ids = [f"{source}_{timestamp}"]
        documents = [text]
        
        if source == "system":
            self.stream_context.add(
                ids=ids,
                documents=documents,
                metadatas=[meta]
            )
            print(f"[Memory] Added to Stream Context: {text[:50]}...")
        else:
            self.long_term_history.add(
                ids=ids,
                documents=documents,
                metadatas=[meta]
            )
            print(f"[Memory] Added to Long Term History: {text[:50]}...")

    def query_brain(self, user_query: str) -> str:
        """
        Queries both collections and generates a response using GPT-4o.
        Only considers stream_context from the last 30 minutes (filter not fully implemented in chroma query directly easily, 
        so we'll retrieve and filter or just retrieve recent).
        """
        print(f"[Brain] Thinking about: {user_query}")
        
        # Retrieve System Context (What the user heard recently)
        stream_results = self.stream_context.query(
            query_texts=[user_query],
            n_results=5
            # where={"timestamp": {"$gt": time.time() - 1800}} # Optional: Filter time if metadata supported
        )
        
        # Retrieve Long Term Memory (Browser history, facts)
        history_results = self.long_term_history.query(
            query_texts=[user_query],
            n_results=3
        )
        
        # Format Context
        context_str = "--- SYSTEM AUDIO CONTEXT (What the user heard) ---\n"
        if stream_results['documents']:
            for doc in stream_results['documents'][0]:
                context_str += f"- {doc}\n"
        
        context_str += "\n--- LONG TERM HISTORY (Browser/Facts) ---\n"
        if history_results['documents']:
            for doc in history_results['documents'][0]:
                context_str += f"- {doc}\n"
                
        # Generate Response
        system_prompt = f"""
        You are Omni-Bot, a helpful AI assistant.
        You have access to what the user is currently hearing on their computer (System Audio) and what they have seen (Browser History).
        
        Use the provided Context to answer the user's question. 
        If the answer is not in the context, use your general knowledge but mention that you don't recall hearing it recently.
        
        CONTEXT:
        {context_str}
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ]
        
        response = self.llm(messages)
        return response.content

# Singleton Instance
memory_manager = None

def get_memory_manager():
    global memory_manager
    if memory_manager is None:
        memory_manager = MemoryManager()
    return memory_manager
