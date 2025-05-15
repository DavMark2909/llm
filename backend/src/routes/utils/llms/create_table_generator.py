import yaml
import sqlite3
import os
import re

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict
from langchain_core.language_models.base import BaseLanguageModel
from langgraph.graph import StateGraph, START, END



class TableConvertionState(TypedDict):
    tables_to_create: str
    schemas_of_tables: str
    model_response: str
    result_of_run: str
    counter: int
    prompt: str
    llm: BaseLanguageModel 

class TableConverterAgent:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not found in environment variables.")

        self.llm = init_chat_model("gpt-4o-mini", model_provider="openai")
        self.graph = create_graph()
                

    def start_execution(self, tables_to_do, created_schemas):
        tables_result = []
        schemas_result = []

        for table, row in tables_to_do.items():
            tables_result.append(f"Table: {table}\nColumns with sample data:")
            for col, val in row.items():
                tables_result.append(f"- {col}: {repr(val)}")
            tables_result.append("")  

        for table_name, columns in created_schemas.items():
            schemas_result.append(f"Schema for table '{table_name}':")
            for line in columns.split("\n"):
                name, type_ = line.split(" (")
                type_ = type_.rstrip(")")
                schemas_result.append(f"- {name}: {type_}")
        schemas_result.append("")

        tables_result = "\n".join(tables_result)
        schemas_result = "\n".join(schemas_result)

        state = TableConvertionState(tables_to_create=tables_result, schemas_of_tables=schemas_result, llm=self.llm, counter=0)

        result_state = self.graph.invoke(state)
        return result_state['result_of_run']
        

    
def create_graph():
    graph = StateGraph(TableConvertionState)
    graph.add_node("prompt_preparation", prepare_prompt)
    graph.add_node("prompt_running", run_prompt)
    graph.add_node("query_running", run_response)

    graph.add_edge(START, "prompt_preparation")
    graph.add_edge("prompt_preparation", "prompt_running")
    graph.add_edge("prompt_running", "query_running")
    graph.add_conditional_edges("query_running", 
        cond_logic,
            {
                "finish": END,
                "repeat": "query_running",
                "empty": "prompt_running"
            }  
    )

    app = graph.compile()
    return app
    

def prepare_prompt(state: TableConvertionState):
    config_path = os.path.join(os.path.dirname(__file__), "configs", "table_convertion_configs.yaml")
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    prompt = data['prompts']['table_creation'].format(table_content=state["tables_to_create"], table_schema=state["schemas_of_tables"])
    state["prompt"] = prompt
    print("Prompt is ", prompt)
    return state
    
def run_prompt(state: TableConvertionState):
    prompt = state["prompt"]
    llm = state['llm']
    response = llm.invoke(prompt).content
    print("The model response ", response)
    match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL)
    if match:
        state['model_response'] = match.group(1).strip()
    else:
        state['model_response'] = ""  
    return state

def run_response(state: TableConvertionState):
    query = state['model_response']
    connection = sqlite3.connect('data.db')
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        state['result_of_run'] = "success"
    except sqlite3.Error:
        if query == "":
            state['result_of_run'] = "empty"
        else:
            state['result_of_run'] = "error"
        state['counter'] = state['counter'] + 1
    finally:
        connection.close()
    return state

def cond_logic(state: TableConvertionState):
    result = state['result_of_run']
    counter = state['counter']
    if counter > 3:
        return "finish"
    if result == "error":
        return "repeat"
    elif result == "empty":
        return "empty"
    else:
        return "finish"