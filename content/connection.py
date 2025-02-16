from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama3.2:latest")

response = llm.invoke("Who was the first man on the moon")

print(response)
