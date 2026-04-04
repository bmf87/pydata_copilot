# inference.py
from typing import List, Dict, Generator
from llama_cpp import Llama
from pydc.llm.llm_loader import load_inference_model

def chat_once(messages: List[Dict[str, str]], **gen_kwargs) -> str:
    """
    Chat with the LLM once. 
    
    Args:
        messages (List[Dict[str, str]]): List of messages to send to the LLM.
        **gen_kwargs: Additional keyword arguments to pass to the LLM.
    
    Returns:
        str: The response from the LLM.
    """

    # Get cached LLM instance
    llm: Llama = load_inference_model()
    resp = llm.create_chat_completion(messages=messages, max_tokens=2048, **gen_kwargs)
    return resp["choices"][0]["message"]["content"]

def chat_stream(messages: List[Dict[str, str]], **gen_kwargs) -> Generator[str, None, None]:
    """
    Stream tokens from the LLM. Use if UI/UX requires real-time updates.
    
    Args:
        messages (List[Dict[str, str]]): List of messages to send to the LLM.
        **gen_kwargs: Additional keyword arguments to pass to the LLM.
    
    Returns:
        Generator[str, None, None]: Generator of tokens from the LLM.
    """
    
    # Get cached LLM instance
    llm: Llama = load_inference_model()
    stream = llm.create_chat_completion(messages=messages, stream=True, max_tokens=2048, **gen_kwargs)
    for chunk in stream:
        delta = chunk["choices"][0]["delta"]
        token = delta.get("content", "")
        if token:
            yield token
