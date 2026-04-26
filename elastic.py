from elasticsearch import AsyncElasticsearch, helpers
from config import ELASTIC_HOST, ELASTIC_INDEX
import pandas as pd
import os

es = AsyncElasticsearch([ELASTIC_HOST])

async def create_index():
    if await es.indices.exists(index=ELASTIC_INDEX):
        return
    mapping = {
        "mappings": {
            "properties": {
                "phone": {"type": "keyword"},
                "email": {"type": "keyword"},
                "full_name": {"type": "text"},
                "nickname": {"type": "keyword"},
                "address": {"type": "text"},
                "passport": {"type": "keyword"},
                "birth_date": {"type": "date"}
            }
        }
    }
    await es.indices.create(index=ELASTIC_INDEX, body=mapping)

async def search_es(query: str):
    body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["phone", "email", "full_name", "nickname", "address", "passport"],
                "fuzziness": "AUTO"
            }
        },
        "size": 10
    }
    res = await es.search(index=ELASTIC_INDEX, body=body)
    return [hit["_source"] for hit in res["hits"]["hits"]]

async def index_file(filepath: str):
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines="skip")
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(filepath, engine="openpyxl")
        elif ext == ".json":
            df = pd.read_json(filepath)
        elif ext == ".txt":
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            import csv
            reader = csv.DictReader(lines, delimiter="\t")
            df = pd.DataFrame(reader)
        else:
            return 0
        actions = [
            {"_index": ELASTIC_INDEX, "_source": row.to_dict()}
            for _, row in df.iterrows()
        ]
        if actions:
            await helpers.async_bulk(es, actions)
        return len(actions)
    except Exception as e:
        print(f"Ошибка индексации {filepath}: {e}")
        return 0
