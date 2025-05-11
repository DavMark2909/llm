import yaml
import sqlite3
import os

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
    prompt: str
    llm: BaseLanguageModel 

class TableConverterAgent:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not found in environment variables.")

        self.llm = init_chat_model("gpt-4o-mini", model_provider="openai")
        self.graph = create_graph(self.llm)
                

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

        state = TableConvertionState(tables_to_create=tables_result, schemas_of_tables=schemas_result, llm=self.llm)

        result_state = self.graph.invoke(state)
        

    
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
                "repeat": "query_running"
            }  
    )

    app = graph.compile()
    return app
    

def prepare_prompt(state: TableConvertionState):
    with open("configs/table_convertion_configs.yaml", "r") as f:
        data = yaml.safe_load(f)
    prompt = data['prompts']['table_creation'].format(table_content=state["tables_to_create"], table_schema=state["schemas_of_tables"])
    state["prompt"] = prompt
    return state
    
def run_prompt(state: TableConvertionState):
    prompt = state["prompt"]
    llm = state['llm']
    response = llm.invoke(prompt).content
    print(response)
    # the end of this code is hardcoded
    response = "create table flights (flight_id int primary key, plane_number int, departure_place int, destination_place int, departure_time DATETIME, arrival_time DATETIME, FOREIGN KEY (plane_number) REFERENCES planes(plane_number), FOREIGN KEY (departure_place) REFERENCES place(place_id), FOREIGN KEY (destination_place) REFERENCES place(place_id))"
    state['model_response'] = response
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
        state['result_of_run'] = "error"
    finally:
        connection.close()
    return state

def cond_logic(state: TableConvertionState):
    result = state['result_of_run']
    if result == "error":
        return "repeat"
    else:
        return "finish"