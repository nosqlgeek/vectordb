from sentence_transformers import SentenceTransformer
import numpy as np
from models.model import Model

class TextModel(Model):
    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/all-distilroberta-v1')

    '''
    Returns the vector of a given text
    '''
    def embed(self, emb_input):
        return self.model.encode(emb_input).astype(np.float32).tobytes()


    '''
    Get the dimension of the model by applying the model to a simple text
    '''
    def dim(self):
        vector = self.embed("Any text would do here.")
        return len(np.frombuffer(vector, dtype=np.float32).tolist())
