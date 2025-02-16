from utils.model_load import ModelLoader
from utils.load_config import LoadConfig
from utils.conn_load import ConnectionLoader
from utils.prepare_sql_from_csv import PrepareSQLFromTabular


def starter():
    configs = LoadConfig()
    db_connection = ConnectionLoader(confs=configs)
    model = ModelLoader(confs=configs, db = db_connection)



if __name__ == "__main__":
    starter()