import os
import sqlite3
from collections import OrderedDict
from typing import Dict, List, Any


def build_database(tables_dict: Dict[str, List[str]]):
    connection = sqlite3.connect("bexar_data.db")
    cursor = connection.cursor()
    for key, value in tables_dict.items():
        cursor.execute(f"CREATE TABLE {key}({', '.join(value)});")


def insert_record(data_dict: OrderedDict[str, Any]):
    connection = sqlite3.connect("bexar_data.db")
    cursor = connection.cursor()
    improvement_list = data_dict.pop("improvements")
    value_history_list = data_dict.pop("value_history")
    cursor.execute(
        f"INSERT INTO property VALUES({'?, ' * (len(data_dict.keys()) - 1) + '?'})", list(data_dict.values())
    )
    for improvement in improvement_list:
        improvement_details_list = improvement.pop("details")
        for improvement_detail in improvement_details_list:
            cursor.execute(
                f"INSERT INTO improvement_details VALUES({'?, ' * (len(improvement_detail.keys()) - 1) + '?'})",
                list(improvement_detail.values()),
            )
        cursor.execute(
            f"INSERT INTO improvement VALUES({'?, ' * (len(improvement.keys()) - 1) + '?'})", list(improvement.values())
        )
    for history in value_history_list:
        cursor.execute(
            f"INSERT INTO value_history VALUES({'?, ' * (len(history.keys()) - 1) + '?'})", list(history.values())
        )
    connection.commit()


def clear_database():
    os.remove("bexar_data.db")
