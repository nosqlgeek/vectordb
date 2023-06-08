import redis
import time
import numpy as np
from models.ptmodel import PassThroughModel
from redis.commands.search.field import (
    NumericField,
    TagField,
    TextField,
    VectorField
)
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

class VectorDB:

    '''
    Creates a VectorDB instance by connecting to the database server
    '''

    def __init__(self, host, port, password, model = PassThroughModel()):
        self.host = host
        self.port = int(port)
        self.password = password
        self.model = model
        self.con = redis.Redis(host=self.host, port=self.port, password=self.password, decode_responses=False)

    '''
    Waits for the index to be created.
    '''

    def _wait_for_index(self, index_name, delay=0.1):
        res = self.con.execute_command("FT.INFO", "idx:{}".format(index_name))

        while not res.index(b"indexing"):
            time.sleep(delay)
            print(str(res))
            res = self.con.execute_command("FT.INFO", "idx:{}".format(index_name))

    '''
    Creates a search index. 
    
    The default schema has a 'descr' text field, a 'labels' tag field, a numeric field called
    'time' and a vector field called 'vec'.
    '''

    def create_index(self,
                     dimension=-1,
                     index_name="vectors",
                     schema={"vec": "VectorField", "descr": "TextField", "labels": "TagField", "time": "NumericField"},
                     item_type="vec",
                     ):

        if dimension == -1:
            dimension = self.model.dim()

        # Example idx_schema:
        # (VectorField("vec", "HNSW", {"TYPE": "FLOAT32", "DIM": dimension, "DISTANCE_METRIC": "COSINE"}),
        #  TextField("descr"),
        #  TagField("labels", sortable=True),
        #  NumericField("time", sortable=True))
        idx_schema = []

        for k in schema:
            v = schema[k]

            if v == "VectorField":
                idx_schema.append(
                    VectorField(k, "HNSW", {"TYPE": "FLOAT32", "DIM": dimension, "DISTANCE_METRIC": "COSINE"}))
            elif v == "TextField":
                idx_schema.append(TextField(k))
            elif v == "TagField":
                idx_schema.append(TagField(k, sortable=True))
            elif v == "NumericField":
                idx_schema.append(NumericField(k, sortable=True))
            else:
                raise ValueError("Unknown type: {}".format(k))

        idx_def = IndexDefinition(prefix=["{}:".format(item_type)])

        self.con.ft("idx:{}".format(index_name)).create_index(tuple(idx_schema), idx_def)
        self._wait_for_index(index_name)
        return True


    '''
    Adds a vector with meta data to the database
    
    By default the PassTrough model is used, which mens that the input_data is just
    the input vector itself.
    
    If another model was passed during construction, then you need to use input_data that matches the expectation
    of this model (e.g., a string for the TextModel)
    '''

    def add(self, item_type, item_id, meta_data, input_data, vector_field="vec"):

        data = {"time":time.time()}

        for k in meta_data:
            if isinstance(meta_data[k], list):
                data[k] = ', '.join(meta_data[k])
            else:
                data[k] = meta_data[k]

        data[vector_field] = self.model.embed(input_data)

        #print("data = {}".format(str(data)))
        return self.con.hset("{}:{}".format(item_type, item_id), mapping=data)

    '''
    Deletes a vector from the database
    '''

    def delete(self, item_type, item_id):
        self.con.unlink("{}:{}".format(item_type, item_id))

    '''
    Performs a vector similarity search which returns the vector type, the id, and the similarity score
    
    By default, the PassThrough model is used, which means that the input data is the input vector. However,
    you can also pass input_data that matches the expectations of the model that was used during construction time.
    '''
    def vector_search(self, meta_data_query, input_data, num_neighbours, index_name="vectors", vector_field="vec"):
        search_vector = self.model.embed(input_data)
        vector_score_field = "__{}_score".format(vector_field)
        vector_query = "{}=>[KNN {} @{} $vector]".format(meta_data_query, num_neighbours, vector_field)

        redis_query = Query(vector_query).return_fields("_id", vector_score_field).sort_by(vector_score_field, True).dialect(2)
        result = self.con.ft("idx:{}".format(index_name)).search(redis_query, query_params={"vector": search_vector})
        return map(lambda d: {"id": d["id"].split(":")[1],
                              "type": d["id"].split(":")[0],
                              "score": d[vector_score_field]},
                   result.docs)

    '''
    Perform a simple search
    '''
    def search(self, meta_data_query, index_name="vectors" ):
        redis_query = Query(meta_data_query).return_fields("_id").dialect(2)
        result = self.con.ft("idx:{}".format(index_name)).search(redis_query)
        return map(lambda d: {"id": d["id"].split(":")[1],
                              "type": d["id"].split(":")[0]},
                   result.docs)

    '''
    Get the raw vector and its meta data
    '''
    def get(self, item_type, item_id):
        result = self.con.hgetall("{}:{}".format(item_type,item_id))

        casted = {}

        for k in result:
            key = k.decode("utf-8")
            try:
                casted[key]=float(result[k])
            except ValueError:
                try:
                    casted[key]=result[k].decode("utf-8")
                except ValueError:
                   casted[key]=np.frombuffer(result[k], dtype=np.float32).tolist()

        return casted




