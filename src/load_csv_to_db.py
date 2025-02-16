from utils.prepare_sql_from_csv import PrepareSQLFromTabular
from utils.load_config import LoadConfig

configs = LoadConfig()

if __name__ == "main":
    prepareSQLInstance = PrepareSQLFromTabular()
    prepareSQLInstance.run_pipeline()