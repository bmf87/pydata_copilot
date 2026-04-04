import streamlit as st
from llama_cpp import Llama
from typing import List
from langchain_core.embeddings import Embeddings
import pydc.util.constants as constants
from llama_cpp import Llama
import pydc.util.constants as constants

@st.cache_resource(show_spinner="Loading Qwen 7B model...")
def load_inference_model() -> Llama:
    """
    Load a GGUF model from a Hugging Face repo using llama_cpp.Llama.from_pretrained.
    Cached so Streamlit reruns don't reload it every time.
    """
    llm = Llama.from_pretrained(
        repo_id=constants.INFERENCE_REPO_ID_7B,                   
        filename=constants.INFERENCE_MODEL_7B,        # Q4_K_M model file
        n_ctx=4096,                                   # context window
        n_threads=4,                                  
        n_gpu_layers=26,                              # partial offload - diagnosing v0.2.62 GPU token bug
        chat_format="chatml",                         # Qwen2.5-Coder uses ChatML; required in v0.2.x
        verbose=False,
    )
    return llm

@st.cache_resource(show_spinner="Loading Nomic Embed model...")
def load_embedding_model() -> Llama:
    """
    Load a GGUF text embedding model from a Hugging Face repo using llama_cpp.Llama.from_pretrained.
    Cached so Streamlit reruns don't reload it every time.
    """
    embed_model = Llama.from_pretrained(
        repo_id=constants.EMBEDDING_REPO_ID,
        filename=constants.EMBEDDING_MODEL,
        embedding=True,                                  # Crucial for embedding models in llama_cpp
        n_ctx=8192,                                      # nomic-embed-text supports 8192 context window
        n_threads=4,
        n_gpu_layers=-1,
        verbose=False,
    )
    return embed_model

class LlamaCPPEmbeddings(Embeddings):
    """
    Wrapper around a loaded llama_cpp Llama embeddings model to conform to 
    LangChain's Embeddings interface so it can be automatically used by InMemoryStore.
    """
    def __init__(self, model: Llama):
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            res = self.model.create_embedding(text)
            embeddings.append(res["data"][0]["embedding"])
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        res = self.model.create_embedding(text)
        return res["data"][0]["embedding"]

@st.cache_resource
def get_langchain_embeddings() -> LlamaCPPEmbeddings:
    """
    Returns the loaded LlamaCPPEmbeddings instance. 
    Cached to prevent reloading the model on every Streamlit rerun.
    """
    model = load_embedding_model()
    return LlamaCPPEmbeddings(model)
