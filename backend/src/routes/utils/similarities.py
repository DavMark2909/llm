import inflect

p = inflect.engine()

def find_matching_table(fk_column: str, existing_tables: list[str]) -> str | None:
    base_name = fk_column[:-3]  

    for table in existing_tables:
        singular = p.singular_noun(table)
        singular = singular if singular else table  

        if singular.lower() == base_name.lower():
            # print(table, " ", fk_column)
            return table  

    return None

def find_own_id(table, fk_columns):
    singular = p.singular_noun(table)
    singular = singular if singular else table

    for column in fk_columns:
        c = column[:-3]
        if singular.lower() == c.lower():
            # print("Found the column for itself - ", table, " , the column is", column)
            return column
    return None

def queue_maker(values, tables):
    queue = []
    while values:
        for table in list(values.keys()):
            resolvable = True
            fk_columns = values[table][:]
            itself = find_own_id(table, fk_columns)
            if itself is not None:
                fk_columns.remove(itself)
            for column in fk_columns:
                match = find_matching_table(column, tables)
                if match == None:
                    resolvable = False
                    continue
            if resolvable:
                queue.append(table)
                values.pop(table)
                tables.append(table)
    return queue