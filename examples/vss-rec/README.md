# Redis as a vector database for recommendations

This example shows how to use Redis Stack's vector similarity search to build a recommendation engine.

The idea is quite simple:

1. The interests of a user are expressed as a vector. Each component of the vector is associated with one category of interest.
2. If we know the interests of a specific user, we can search for the K-**N**(earest)**N**(eighbours) to find other users that share the same interests.
4. We can then inspect the behavior of these users (e.g., the purchase history) to recommend the user specific products.

The following table shows the vector `[0.9, 0.7, 0.2]`:

|books|comics|computers|
|---|---|---|
|0.9|0.7|0.2|


Let's assume that a user is only interested in a specific category if the interest value is larger than the threshold of `0.4`, which means that our user is interested in 'books' and 'comics' but not in  'computers'.

## How to use Redis

You can use Redis Stack's query and search capabilities to:

* Index vectors
* Find similar vectors

My source code example wraps the Redis commands by using a `VectorDB` class. Let's look at some of the methods I implemented for accessing Redis.

### `init`

The connection happens within the constructor of the class:

```
def __init__(self, host, port, password):
    self.host = host
    self.port = int(port)
    self.password = password
    self.con = redis.Redis(host=self.host, port=self.port, password=self.password, decode_responses=False)
```

### `create_index`

As the name indicates, this method creates a search index. The default schema has a `descr` text field, a `labels` tag field, a numeric field called `time`, and a vector field named `vec`.

The relevant code within this method is equivalent to the following:

```
idx_schema = (VectorField("vec", "HNSW", {"TYPE": "FLOAT32", "DIM": dimension, "DISTANCE_METRIC": "COSINE"}),
              TextField("descr"),
              TagField("labels", sortable=True),
              NumericField("time", sortable=True))
idx_def = IndexDefinition(prefix=["{}:".format(item_type)])
self.con.ft("idx:{}".format(index_name)).create_index(idx_schema, idx_def)
```

### `add`

This method adds a vector with metadata to the database. I use a [Redis hash](https://redis.io/docs/data-types/hashes/) in this case, but you can also store vectors within JSON with Redis Stack.

```
self.con.hset("{}:{}".format(item_type, item_id), mapping=data)
```

The data dictionary contains the fields `labels`, `descr`, `time`, and `vec`. The vector is stored as binary within the `vec` field. The library `numpy` is used to convert a more human-readable float vector (a Python list) to its byte string representation:

```
data["vec"] = np.array(vector).astype(np.float32).tobytes()
```

Here is an example of such a data dictionary:

```
data = {'time': 1683233711.983063, 'descr': 'Samuel is into books and comics', 'labels': 'books, comics', 'vec': b'fff?333?\xcd\xccL>'}
```

### `vector_search`

The `vector_search` method performs a vector similarity search. I decide only to return the id and vector score in my implementation. My vector query string takes a few arguments:

```
vector_query = "{}=>[KNN {} @{} $vector]".format(meta_data_query, num_neighbours, vector_field)
```

What I call `metadata query`  refers to a RediSearch query that is, in the first step, not related to the vector. This allows you to pre-filter based on additional metadata fields, such as the description (`desc`) or the `labels`.

You can then query the database the following way:

```
# The name of the vector score field depends on the name of the vector field
vector_score_field = "__{}_score".format("vec")
redis_query = Query(vector_query).return_fields("_id", vector_score_field).sort_by(vector_score_field, True).dialect(2)

self.con.ft("idx:{}".format(index_name)).search(redis_query, query_params={"vector": search_vector})
```

For further details, please look at the [vector similarity search reference documentation](https://redis.io/docs/stack/search/reference/vectors/).


## Putting it all together

As explained, I decided to add a thin layer of abstraction by implementing [this `VectorDB`](./vss-rec/vector_db.py) class.

The following example shows how to:

1. Create an index
2. Add some vectors with metadata
3. Perform a simple query for users that are labeled with specific interests
4. Execute a vector similarity search for the two nearest neighbours


Here is the source code:

```
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
```

The output of this program is:

```
Creating the index ...
Adding some vectors ...
data = {'time': 1683233711.983063, 'descr': 'Samuel is into books and comics', 'labels': 'books, comics', 'vec': b'fff?333?\xcd\xccL>'}
data = {'time': 1683233712.02643, 'descr': 'David likes books and comics.', 'labels': 'books, comics', 'vec': b'333?fff?\xcd\xcc\xcc='}
data = {'time': 1683233712.0603049, 'descr': 'Pieter likes comics.', 'labels': 'comics', 'vec': b'\x9a\x99\x99>fff?\xcd\xccL>'}
data = {'time': 1683233712.094195, 'descr': 'Morti is into comics and computers.', 'labels': 'comics, computers', 'vec': b'\xcd\xcc\xcc=fff?333?'}
The following users like books:
{'id': 'samuel', 'type': 'user'}
{'id': 'david', 'type': 'user'}
Checking for users with the same interest ...
search_vector = [0.9, 0.7, 0.2]
score = 5.96046447754e-08
{'time': 1683233711.983063, 'descr': 'Samuel is into books and comics', 'labels': 'books, comics', 'vec': [0.8999999761581421, 0.699999988079071, 0.20000000298023224]}
score = 0.0339003205299
{'time': 1683233712.02643, 'descr': 'David likes books and comics.', 'labels': 'books, comics', 'vec': [0.699999988079071, 0.8999999761581421, 0.10000000149011612]}
```

It's important to understand that a lower score means that a vector is closer to the search vector. In my case, the result is ordered (ascending) by the vector field's score.
