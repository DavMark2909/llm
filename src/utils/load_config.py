import yaml

class LoadConfig:
    def __init__(self) -> None:
        with open('../../config/config.yml', 'r') as file:
            config = yaml.safe_load(file)

        self.load_directories(app_config=config)

    def load_directories(self, app_config):
        self.csv_directory = app_config.get('directories').stored_csv_xlsx_directory

    def mysql_config(self, app_config):
        mysql_config = app_config.get('mysql')

        self.username = mysql_config.get('username')
        self.password = mysql_config.get('password')
        self.host = mysql_config.get('host')
        self.port = mysql_config.get('port')
        self.database = mysql_config.get('database')

    



