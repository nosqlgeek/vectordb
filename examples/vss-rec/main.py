import os
from vector_db import VectorDB

if __name__ == '__main__':
    print("Connecting to the vector database ...")
    db = VectorDB(os.getenv("DB_HOST"), os.getenv("DB_PORT"), os.getenv("DB_PWD"))

    print("Deleting all vectors ...")
    db.con.flushall()

    print("Creating the index ...")
    db.create_index(dimension=3, index_name="interests", item_type="user")

    print("Adding some vectors ...")
    db.add("user", "samuel", {"descr": "Samuel is into books and comics", "labels": ["books", "comics"]}, [0.9, 0.7, 0.2])
    db.add("user", "david", {"descr": "David likes books and comics.", "labels" : ["books", "comics"]}, [0.7, 0.9, 0.1])
    db.add("user", "pieter", {"descr": "Pieter likes comics.", "labels":["comics"]}, [0.3, 0.9, 0.2])
    db.add("user", "morti", {"descr": "Morti is into comics and computers.", "labels":["comics", "computers"]}, [0.1, 0.9, 0.7])

    print("The following users like books:")
    for r in db.search("@labels:{books}", index_name="interests"):
        print(r)

    print("Checking for users with the same interest ...")
    search_vector = [0.9, 0.7, 0.2]
    print("search_vector = {}".format(search_vector))
    for r in db.vector_search("*", search_vector, 2, index_name="interests"):
        print("score = {}".format(r["score"]))
        print(db.get(r["type"], r["id"]))



