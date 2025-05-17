
from sqlalchemy import create_engine, MetaData

def get_table_schemas():
    schemas = {}
    engine = create_engine('sqlite:///data.db')
    metadata = MetaData()
    metadata.reflect(bind=engine)

    for table_name, table in metadata.tables.items():
        # Use the table name as a string, and column names as list of strings
        schemas[str(table_name)] = [column.name for column in table.columns]
    
    return schemas

