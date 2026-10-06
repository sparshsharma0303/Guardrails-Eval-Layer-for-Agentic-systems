import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg
import hashlib
load_dotenv()

schema_path = Path(__file__).parent / "schema.sql"

conn_string = os.environ["DATABASE_URL"]
conn = psycopg.connect(conn_string)

with open(schema_path) as f:
    sql = f.read()

with conn.cursor() as cur:
    cur.execute(sql)

def compute_cache_key(provider, model, prompt):
    combined = f"{model}|{provider}|{prompt}"
    hash_object = hashlib.sha256(combined.encode())
    key = hash_object.hexdigest()
    return key

def get_cached_response(conn, cache_key: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT response FROM cache WHERE cache_key = %s",
            (cache_key,)
        )
        row = cur.fetchone()
        if not row: 
            return None
        else:
            return row[0]

def save_to_cache(conn,model:str,provider:str,prompt:str, response:str):
    cache_key = compute_cache_key(model=model,provider=provider,prompt=prompt)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO cache( cache_key, model, provider, prompt, response) VALUES (%s,%s,%s,%s,%s)",
            (
                cache_key,
                model,
                provider,
                prompt,
                response
            )
        )
    conn.commit()


if __name__ == "__main__":
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'cache';")
        result = cur.fetchone()

    key1 = compute_cache_key(provider="a",model="bc",prompt="de")
    key2 = compute_cache_key(provider="a",model="bc",prompt="de") 
    key3 = compute_cache_key(provider="a",model="bc",prompt="d")  # different prompt
    print(key1)
    print(key2)
    print(key3)
    print(key1 == key2)
    print(key2 == key3)

