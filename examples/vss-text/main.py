import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))
from models.txtmodel import TextModel
from config import CONFIG as cfg
from vectordb import VectorDB

if __name__ == '__main__':
    print("Connecting to the vector database ...")
    db = VectorDB(cfg.get("db_host"), cfg.get("db_port"), cfg.get("db_password"), TextModel())

    print("Deleting all vectors ...")
    db.con.flushall()

    print("Creating the index ...")
    db.create_index(index_name="texts", item_type="article")

    print("Adding some vectors ...")
    db.add("article", "hello", {"descr": "A simple hello world example", "labels": ["example"]},
           "Hello world is a common example to show something very simple.")
    db.add("article", "fox", {"descr": "A very simple example", "labels": ["example"]},
           "The quick brown fox jumps over the lazy dog.")

    print("Checking for users with the same interest ...")
    search_text = "The quick brown dog jumps over the lazy mouse."
    for r in db.vector_search("*", search_text, 1, index_name="texts"):
        print("score = {}".format(r["score"]))
        print(db.get(r["type"], r["id"]))



