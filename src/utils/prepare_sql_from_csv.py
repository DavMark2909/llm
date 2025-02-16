import os
import yaml
from sqlalchemy import create_engine, inspect
import pandas as pd

class PrepareSQLFromTabular:
    def __init__(self) -> None:
    
        self.file_dir_list = os.listdir("../../data")
        self.files_directory = "/Users/mark/Documents/Research/LLM_MODEL/data"

        with open('../config/config.yml', 'r') as file:
            config = yaml.safe_load(file)

        mysql_config = config.get('mysql')

        username = mysql_config.get('username')
        password = mysql_config.get('password')
        host = mysql_config.get('host')
        port = mysql_config.get('port')
        database = mysql_config.get('database')

        connection_string = f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}"
        self.engine = create_engine(connection_string)
        
        print("Number of csv files:", len(self.file_dir_list))

    def _prepare_db(self):
        
        for file in self.file_dir_list:
            full_file_path = os.path.join(self.files_directory, file)
            print(full_file_path)
            file_name, file_extension = os.path.splitext(file)
            if file_extension == ".csv":
                df = pd.read_csv(full_file_path)
            elif file_extension == ".xlsx":
                df = pd.read_excel(full_file_path)
            else:
                raise ValueError("The selected file type is not supported")
            df.to_sql(file_name, self.engine, index=False)
        print("All csv files are saved into the sql database.")

    def _validate_db(self):
        # validates the tables stored in the SQL database.
        insp = inspect(self.engine)
        table_names = insp.get_table_names()
        print("Available table names in created SQL DB:", table_names)

    def run_pipeline(self):
        # method is responsible for the convertion of csv files to sql tables and futher validation of the table
        self._prepare_db()
        self._validate_db()

    