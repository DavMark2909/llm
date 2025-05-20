import yaml
import sqlite3
import os
import re

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict
from typing import Any
from langchain_core.language_models.base import BaseLanguageModel
from langgraph.graph import StateGraph, START, END
from sqlalchemy import create_engine, inspect

class ModelResponseState(TypedDict):
    user_question: str
    time_column: str
    time_aggregation: str
    fact_table: str
    tables_content: list[str]
    whole_question: str
    main_question: str
    query: str
    result: str
    counter: int
    error: str
    decision: str
    final_result: Any
    llm: BaseLanguageModel

class ModelResponseAgent:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not found in environment variables.")

        self.llm = init_chat_model("gpt-4o-mini", model_provider="openai")
        self.graph = create_graph()

    def ask_question(self, question):
        state = ModelResponseState(user_question=question, counter=0, llm=self.llm)
        result = self.graph.invoke(state)
        return result

def create_graph():
    graph = StateGraph(ModelResponseState)
    graph.add_node("content_preparation", table_content_preparation)
    graph.add_node("prompt_preparation", prepare_prompt)
    graph.add_node("generate_run_query", generate_query)
    graph.add_node("correct_prompt", correct_query)
    graph.add_node("end_of_execution", stop_execution)
    graph.add_node("decision_maker", decision)
    graph.add_node("text_generator", gen_text)
    graph.add_node("chart_generator", gen_chart)

    graph.add_edge(START, "content_preparation")
    graph.add_edge("content_preparation", "prompt_preparation")
    graph.add_edge("prompt_preparation", "generate_run_query")
    graph.add_conditional_edges("generate_run_query",
        error_router,
        {
            "continue": "decision_maker",
            "fix_the_query": "correct_prompt",
            "acknowledge_error": "end_of_execution"
        }
    )
    graph.add_conditional_edges("decision_maker",
        decision_router,
        {
            "chart": "chart_generator",
            "text": "text_generator",
            "again": "decision_maker"
        }
    )
    graph.add_edge("chart_generator", END)
    graph.add_edge("text_generator", END)
    graph.add_edge("correct_prompt", "generate_run_query")
    graph.add_edge("end_of_execution", END)

    app = graph.compile()
    return app

def checkTimeAggregation(column):
    time_unit = ""
    if ("month" in column):
        time_unit = "month"
        return (True, time_unit)
    elif ("hour" in column):
        time_unit = "hour"
        return (True, time_unit)
    elif ("day" in column or "weekda" in column):
        time_unit = "day"
        return (True, time_unit)
    else:
        return (False, time_unit)

def select_query_extraction(query):
    pattern = r'(SELECT.*?;)'
    matches = re.findall(pattern, query, re.DOTALL)
    if not matches:
        raise ValueError("No INSERT queries found in the provided text.")
    queries = []
    for sql in matches:
        queries.append(sql)
    return queries[0]

def table_content_preparation(state: ModelResponseState):
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    DB_PATH = os.path.join(BASE_DIR, "data.db")

    engine = create_engine(f"sqlite:///{DB_PATH}")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    tables_res = []
    time_aggregation = ""
    for table_name in tables:
        columns = inspector.get_columns(table_name)
        cols = []
        isFact = "fact" in table_name
        for column in columns:
            cols.append(f"{column['name']} ({column['type']})")
            if isFact:
                (isTime, time_unit) = checkTimeAggregation(column['name'])
                if isTime:
                    state["time_column"] = column
                    time_aggregation = time_unit
        cols_str = ",".join(cols)
        cur_res = "Table " + table_name
        if isFact:
            state["time_aggregation"] = time_aggregation
            state['fact_table'] = table_name
        tables_res.append(cur_res + ": " + cols_str)
    schemas = "\n".join(tables_res)
    state["tables_content"] = schemas
    return state

def prepare_prompt(state: ModelResponseState):
    config_path = os.path.join(os.path.dirname(__file__), "configs", "response.yaml")
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    if (state["time_aggregation"] == ""):
        main_prompt = data['etl']['question'].format(user_question=state['user_question'], table_schemas=state['tables_content'])
        whole_prompt = data['template'].format(template=main_prompt)
        state["main_question"] = main_prompt
        state["whole_question"] = whole_prompt
    else:
        main_prompt = data['time'][state['time_aggregation']].format(user_question=state['user_question'], fact_table=state["fact_table"], time_column=state['time_column'], table_schemas=state['tables_content'])
        whole_prompt = data['template'].format(template=main_prompt)
        state["main_question"] = main_prompt
        state["whole_question"] = whole_prompt
    return state

def generate_query(state: ModelResponseState):
    prompt = state['whole_question']
    llm = state['llm']
    query = llm.invoke(prompt).content
    query = select_query_extraction(query)
    state["query"] = query
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    DB_PATH = os.path.join(BASE_DIR, "data.db")
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    try:
        res = cursor.execute(query)
        state['result'] = res.fetchall()
        state['error'] = ""
    except sqlite3.Error as e:
        state['error'] = str(e)
        state['counter'] = state['counter'] + 1
    return state

def decision(state: ModelResponseState):
    config_path = os.path.join(os.path.dirname(__file__), "configs", "response.yaml")
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    prompt = data['prompts']['decision'].format(user_question=state['user_question'], answer=state['result'])
    llm = state['llm']
    decision = llm.invoke(prompt).content
    state['decision'] = decision
    return state

def decision_router(state: ModelResponseState):
    if state['decision'] == 'chart':
        return "chart"
    elif state['decision'] == 'text':
        return "text"
    else:
        return "again"
    
def gen_text(state: ModelResponseState):
    config_path = os.path.join(os.path.dirname(__file__), "configs", "response.yaml")
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    prompt = data['prompts']['text'].format(user_question=state['user_question'], answer=state['result'])
    llm = state['llm']
    response = llm.invoke(prompt)
    state['final_result'] = response.content
    return state

def gen_chart(state: ModelResponseState):
    config_path = os.path.join(os.path.dirname(__file__), "configs", "response.yaml")
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    prompt = data['prompts']['chart'].format(user_question=state['user_question'], answer=state['result'])
    llm = state['llm']
    response = llm.invoke(prompt).content
    state['final_result'] = response
    return state

def error_router(state: ModelResponseState):
    if state['error'] == "":
        return "continue"
    else:
        if state['counter'] < 5:
            return "fix_the_query"
        else:
            return "acknowledge_error"
        
def correct_query(state: ModelResponseState):
    config_path = os.path.join(os.path.dirname(__file__), "configs", "response.yaml")
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    state['whole_question'] = data['etl']['correction'].format(user_question=state['main_question'], generated_query=state['query'], error_description=state["error"])
    return state

def stop_execution(state: ModelResponseState):
    state['result'] = "Could not answer your question"
    return state