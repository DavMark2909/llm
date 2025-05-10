import sqlite3
import pandas as pd

def convert_file_csv(file_name, file_path, extension):
    if extension == "csv":
        df = pd.read_csv(file_path)
        connection = sqlite3.connect("data.db")
        if table_exists(connection, file_name):
        # TODO: create a table that stores the etl query for the fact table. That query should be executed after new data is added to already existing table
            delete_fact_table()
        df.to_sql(file_name, connection, if_exists='append') 

def table_exists(connection, table_name):
    cursor = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,)
    )
    return cursor.fetchone() is not None

def delete_fact_table():
    return