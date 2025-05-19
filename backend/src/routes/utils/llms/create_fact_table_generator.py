import yaml
import sqlite3
import os
import re

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from sqlalchemy import create_engine, inspect

from typing_extensions import TypedDict, List
from langchain_core.language_models.base import BaseLanguageModel
from langgraph.graph import StateGraph, START, END

class FactTableState(TypedDict):
    prompt: str
    model_output: str
    agg_columns: List[str]
    user_prompt: str
    checker: str
    fact_table: str
    result_of_run: str
    counter: int
    etl_counter: int
    etl: str
    etl_errors: str
    etl_result: str
    table_queries: str
    llm: BaseLanguageModel


class TableConverterAgent:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not found in environment variables.")
        self.llm = init_chat_model("gpt-4o-mini", model_provider="openai")
        self.graph = create_graph()

    def start_fact_table(self, agg_columns, operations, time_column, time):
        config_path = os.path.join(os.path.dirname(__file__), "configs", "fact_table.yaml")
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
        prompts = data["model"]["prompts"]
        role_prompt = prompts["role"]
        tables_schemas_prompt = prompts["tables"].format(tables=self.generate_table_schema_from_db())
        operations_string = ", ".join(f"{op} of {col}" for col, op in operations.items())
        operations_prompt = prompts["operations"].format(operations=operations_string)
        time_aggregation_string = ""

        print("Operatin prompt: ", operations_prompt)

        if time != "":
            generated_time_field = self.generate_time_aggregation(time_column, time)
            time_aggregation_string = prompts["time_aggregation"].format(date_field=time_column,time=time, generated_time_name=generated_time_field)
            agg_columns = [generated_time_field if col == time_column else col for col in agg_columns]
        if len(agg_columns) > 1:
            output_prompt = prompts["remarks_multiple_aggregation"].format(key={', '.join(agg_columns)})
        else:
            output_prompt = prompts["remarks_one_aggregation"].format(primary_key=agg_columns[0])

        final_prompt = ' '.join([role_prompt, tables_schemas_prompt, operations_prompt, time_aggregation_string, output_prompt])
        user_prompt = data['model']['prompts']['user_prompting'].format(agg_columns=agg_columns, operations=operations_string, time_column=time_column, time=time)
        etl = data['model']['prompts']['etl']
        state = FactTableState(prompt=final_prompt, llm=self.llm, checker=data["model"]["prompts"]["checking_prompt"], user_prompt=user_prompt, counter=0, etl_counter=0, etl=etl)

        result_state = self.graph.invoke(state)
        return result_state['result_of_run']

    def generate_time_aggregation(self, field_name, time_unit):
        if time_unit == "HOUR":
            field_name += "_hourly"
        elif time_unit == "WEEKDAY":
            field_name += "_daily"
        elif time_unit == "WEEK":
            field_name += "_weekly"
        elif time_unit == "MONTH":
            field_name += "_monthly"
        else:
            field_name += "_quarterly"
        return field_name

    def generate_table_schema_from_db(self):
        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        DB_PATH = os.path.join(BASE_DIR, "data.db")

        engine = create_engine(f"sqlite:///{DB_PATH}")
        inspector = inspect(engine)
        outputs = []

        table_names = inspector.get_table_names()

        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            formatted_fields = "\n  - ".join(
                f"{col['name']} {col['type']}" for col in columns
            )
            formatted_table = f"Table: {table_name}\n  - {formatted_fields}"
            outputs.append(formatted_table)

        return "\n\n".join(outputs)

def create_graph():
    graph = StateGraph(FactTableState)
    graph.add_node("generate_user_prompt", generate_user_prompt)
    graph.add_node("run_prompt", run_prompt)
    graph.add_node("model_output_checker", output_checker)
    graph.add_node("fact_table_runner", create_fact_table)
    graph.add_node("table_schema_creator", tables_schema_creater)
    graph.add_node("etl_creator", create_etl)

    graph.add_edge(START, "generate_user_prompt")
    graph.add_edge("generate_user_prompt", "run_prompt")
    graph.add_edge("run_prompt", "model_output_checker")
    graph.add_edge("model_output_checker", "fact_table_runner")
    graph.add_conditional_edges("fact_table_runner", 
        cond_logic,
            {
                "finish": END,
                "repeat": "model_output_checker",
                "empty": "model_output_checker",
                "continue": "table_schema_creator"
            }  
    )
    graph.add_edge("table_schema_creator", "etl_creator")
    graph.add_conditional_edges("etl_creator", 
        cond_logic_etl,
            {
                "finish": END,
                "repeat": "etl_creator",
            }  
    )

    app = graph.compile()
    return app

def sql_query_extraction(query):
    pattern = r'(INSERT.*?;)'
    matches = re.findall(pattern, query, re.DOTALL)
    if not matches:
        raise ValueError("No INSERT queries found in the provided text.")
    queries = []
    for sql in matches:
        queries.append(sql)
    return queries

def generate_user_prompt(state: FactTableState):
    prompt = state['user_prompt']
    llm = state['llm']

    result = llm.invoke(prompt).content
    state['user_prompt'] = result
    return state

def run_prompt(state: FactTableState):
    prompt = state["prompt"]
    llm = state['llm']

    response = llm.invoke(prompt)
    result = response.content
    state['model_output'] = result
    return state

def output_checker(state: FactTableState):
    model_output = state["model_output"]
    llm = state['llm']
    checker = state['checker']
    user_prompt = state["user_prompt"]

    prompt = checker.format(user_prompt=user_prompt, fact_table=model_output)
    res = llm.invoke(prompt)
    state["model_output"] = res.content
    print(state["model_output"])
    return state

def create_fact_table(state: FactTableState):
    model_output = state["model_output"]
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    DB_PATH = os.path.join(BASE_DIR, "data.db")
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    match = re.search(r"```sql\n(.*?)\n```", model_output, re.DOTALL)
    if match:
        query = match.group(1).strip()
    else:
        query = ""  
    try:
        cursor.execute(query)
        connection.commit()
        state['fact_table'] = query
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

def tables_schema_creater(state: FactTableState):
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    DB_PATH = os.path.join(BASE_DIR, "data.db")

    engine = create_engine(f"sqlite:///{DB_PATH}")
    inspector = inspect(engine)
    outputs = []

    table_names = inspector.get_table_names()

    for table_name in table_names:
        if "fact" in table_name.lower():
            continue
        columns = inspector.get_columns(table_name)
        formatted_fields = "\n  - ".join(
            f"{col['name']} {col['type']}" for col in columns
        )
        formatted_table = f"Table: {table_name}\n  - {formatted_fields}"
        outputs.append(formatted_table)

    res = "\n\n".join(outputs)
    print("In the schema creator method: ", res)
    state['table_queries'] = res
    return state

def create_etl(state: FactTableState):
    llm = state['llm']
    etl_prompt = state['etl'].format(sql_context="sqlite", tables_schema=state["table_queries"], generated_fact_table=state['fact_table'])
    response = llm.invoke(etl_prompt)
    etl_query = sql_query_extraction(response.content)
    print(etl_query[0])
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    DB_PATH = os.path.join(BASE_DIR, "data.db")
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    try:
        cursor.execute(etl_query[0])
        connection.commit()
        state['etl_errors'] = ""
        state['etl_result'] = "success"
        return state
    except:
        state["etl_errors"] = "Error while trying to execute the ETL job."
        state['etl_counter'] += 1
        state['etl_result'] = "failure"
    return state

def cond_logic_etl(state: FactTableState):
    if state['etl_counter'] > 3:
        return "finish"
    if state['etl_errors'] == "":
        return "finish"
    else:
        return "repeat"

def cond_logic(state: FactTableState):
    result = state['result_of_run']
    counter = state['counter']
    if counter > 3:
        return "finish"
    if result == "error":
        return "repeat"
    elif result == "empty":
        return "empty"
    else:
        return "continue"
