# backend/llm_ollama.py
import ollama

MODEL_NAME = "llama3.2"  # this is the model you pulled

def chat_with_ollama(messages):
    """
    messages: list of dicts like:
      {"role": "system"|"user"|"assistant", "content": "text"}
    returns: assistant reply text (str)
    """
    response = ollama.chat(
        model=MODEL_NAME,
        messages=messages,
    )
    return response["message"]["content"]
