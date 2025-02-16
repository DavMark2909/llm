from langchain_ollama import OllamaLLM
from langchain.chains import create_sql_query_chain

class ModelLoader:
    def __init__(self, confs, db) -> None:
        llm = OllamaLLM(model="llama3.2:latest")
        self.sql_chain = create_sql_query_chain(llm, db)