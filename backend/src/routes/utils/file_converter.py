import sqlite3
import pandas as pd
import os

from sqlalchemy import create_engine, MetaData, Table


def convert_files(directory):
    table_map = {}
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if file_path.endswith('.csv'):
            convert_file_csv(filename.replace(".csv", ""), file_path, table_map)
    schemas = {}
    get_table_schemas(schemas)
    get_table_creation_query(table_map, schemas)
    

def convert_file_csv(filename, file_path, table_map):
    df = pd.read_csv(file_path)
    columns = df.columns
    id_columns = [col for col in columns if col.endswith('_id')]
    existedBefore = False

    if len(id_columns) == 1:
        connection = sqlite3.connect("data.db")
        if table_exists(connection, filename):
            existedBefore = True
        df.to_sql(filename, connection, if_exists='append') 
        if existedBefore:
            delete_fact_table()
            run_etl_job()
    else:
        table_map[filename] = df.iloc[0].to_dict()

def get_table_schemas(schemas):
    engine = create_engine('sqlite:///data.db')
    metadata = MetaData()
    metadata.reflect(bind=engine)

    for table_name, table in metadata.tables.items():
        str_builder = []
        for column in table.columns:
            str_builder.append(f"{column.name} ({column.type})")
        schemas[table_name] = str_builder.join("\n")


def get_table_creation_query(tables_for_creation, created_tables):
    
    return 



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