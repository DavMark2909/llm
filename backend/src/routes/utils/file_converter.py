import sqlite3
import pandas as pd
import os

from sqlalchemy import create_engine, MetaData, Table, inspect
from routes.utils.llms.create_table_generator import TableConverterAgent
from .similarities import queue_maker


def convert_files(directory):
    table_map = {} 
    table_path_map = {}
    table_foreign_kyes = {}
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if file_path.endswith('.csv'):
            convert_file_csv(filename.replace(".csv", ""), file_path, table_map, table_foreign_kyes, table_path_map)
    schemas = {}
    tables = get_table_names_init()
    queue = queue_maker(table_foreign_kyes, tables)
    while queue:
        a = queue.pop(0)
        print("Table to proceed: ", a)
        res = get_table_creation_query({a: table_map[a]}, get_table_schemas(schemas))
        if res != "success":
            return res
        convert_generated_table(a, table_path_map[a])
    return "success"

    

def convert_file_csv(filename, file_path, table_map, table_foreign_kyes, table_path_map):
    df = pd.read_csv(file_path)
    columns = df.columns
    id_columns = [col.strip() for col in columns if col.endswith('_id')]
    existedBefore = False

    if len(id_columns) == 1:
        connection = sqlite3.connect("data.db")
        if table_exists(connection, filename):
            existedBefore = True
        df.to_sql(filename, connection, if_exists='append', index=False) 
        if existedBefore:
            delete_fact_table()
            run_etl_job()
        os.remove(file_path)
    else:
        table_path_map[filename] = file_path
        table_map[filename] = df.iloc[0].to_dict()
        table_foreign_kyes[filename] = id_columns

def convert_generated_table(table_name, file_path):
    df = pd.read_csv(file_path)
    datetime_columns = [col for col in df.columns if 'time' in col.lower() or 'day' in col.lower()]
    for col in datetime_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    connection = sqlite3.connect("data.db")
    df.to_sql(table_name, connection, if_exists='append', index=False) 
    os.remove(file_path)


def get_table_schemas(schemas):
    if len(schemas) != 0:
        schemas.clear()
    engine = create_engine('sqlite:///data.db')
    metadata = MetaData()
    metadata.reflect(bind=engine)

    for table_name, table in metadata.tables.items():
        str_builder = []
        for column in table.columns:
            str_builder.append(f"{column.name} ({column.type})")
        schemas[table_name] = "\n".join(str_builder)
    
    return schemas


def get_table_names_init():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    db_path = os.path.join(base_dir, 'data.db')
    engine = create_engine(f'sqlite:///{db_path}')
    inspector = inspect(engine)
    return inspector.get_table_names()


def get_table_creation_query(tables_for_creation, created_tables):
    agent = TableConverterAgent()
    return agent.start_execution(tables_for_creation, created_tables)
    

def table_exists(connection, table_name):
    cursor = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,)
    )
    return cursor.fetchone() is not None

def delete_fact_table():
    return

def run_etl_job():
    return 