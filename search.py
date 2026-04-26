import pandas as pd
import os
from database import insert_record

def index_file(filepath: str) -> int:
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.csv':
            df = pd.read_csv(filepath, encoding='utf-8', on_bad_lines='skip')
        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(filepath, engine='openpyxl')
        elif ext == '.json':
            df = pd.read_json(filepath)
        elif ext == '.txt':
            # предположим tab-separated
            df = pd.read_csv(filepath, sep='\t', encoding='utf-8')
        else:
            return 0
    except Exception as e:
        print(f"Ошибка чтения {filepath}: {e}")
        return 0

    # предполагаем, что столбцы могут называться phone, email и т.д. Приводим к нижнему регистру
    df.columns = [c.lower() for c in df.columns]
    count = 0
    for _, row in df.iterrows():
        rec = {}
        for field in ['phone', 'email', 'full_name', 'nickname', 'address', 'passport', 'birth_date']:
            if field in row:
                val = row[field]
                if pd.notna(val):
                    rec[field] = str(val).strip()
        if rec:
            insert_record(rec)
            count += 1
    return count
