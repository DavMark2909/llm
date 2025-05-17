from .llms.create_fact_table_generator import TableConverterAgent

def launch_fact_table_agent(agg_column, operations, time_column, time):
    agent = TableConverterAgent()
    return agent.start_fact_table(agg_column, operations, time_column, time)