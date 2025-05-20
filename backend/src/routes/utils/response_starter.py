import sqlite3
import ast

from .llms.response_generator import ModelResponseAgent

def parse_question(user_question): 
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
    table_count = cursor.fetchone()[0]

    if table_count == 0:
        return ("You haven't uploaded any files yet", "text")
    else:
        agent = ModelResponseAgent()
        state = agent.ask_question(user_question)
        result = state['final_result']
        type = state['decision']
        if type == "chart":
            result = parse_chart_output(result)
        return (result, type)
    
def parse_chart_output(output: str):
    lines = [line.strip().strip(';') for line in output.strip().splitlines()]
    lines = [line for line in lines if line and not line.startswith('```')]  # remove markdown block

    if len(lines) < 5:
        raise ValueError("Invalid output format: not enough lines")

    try:
        x_values = ast.literal_eval(lines[0])
        y_values = ast.literal_eval(lines[1])
        x_label = lines[2]
        y_label = lines[3]
        title = lines[4]
    except Exception as e:
        raise ValueError(f"Error parsing chart output: {e}")

    return x_values, y_values, x_label, y_label, title
