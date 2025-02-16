from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase

class ConnectionLoader:
    def __init__(self, confs) -> None:
        configs = confs
        connection_string = f"mysql+mysqlconnector://{configs.username}:{configs.password}@{configs.host}:{configs.port}/{configs.database}"
        engine = create_engine(connection_string)
        self.db = SQLDatabase(engine)
        print(self.db.run("SELECT * FROM employee"))