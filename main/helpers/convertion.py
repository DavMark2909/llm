import sqlite3
import os
import pandas as pd
from sqlalchemy import create_engine, inspect

class PrepareCsvToSQL:
    def __init__(self) -> None:
        self.db_name = "from_csv.db"  
        self.folder = "/Users/mark/Documents/Research/LLM_MODEL/data" 
        self.files = ["cancer.csv", "diabetes.csv"]
        self.conn = sqlite3.connect(self.db_name)
        self.engine = create_engine(f"sqlite:///{self.db_name}")

    def _prepare_db(self):
        for file in self.files:
            full_file_path = os.path.join(self.folder, file)
            print(full_file_path)
            file_name, file_extension = os.path.splitext(file)
            if file_extension == ".csv":
                df = pd.read_csv(full_file_path)
            elif file_extension == ".xlsx":
                df = pd.read_excel(full_file_path)
            else:
                raise ValueError("The selected file type is not supported")
            df.to_sql(file_name, self.engine, index=False, if_exists="replace")
        print("All csv files are saved into the sql database.")

    def _validate_db(self):
        insp = inspect(self.engine)
        table_names = insp.get_table_names()
        print("Available table names in created SQL DB:", table_names)

    def run_pipeline(self):
        self._prepare_db()
        self._validate_db()