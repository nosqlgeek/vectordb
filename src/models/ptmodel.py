import numpy as np
from models.model import Model

'''
This model takes human-readable vector (a list of numeric values) and returns the binary representation
for embedding purposes
'''
class PassThroughModel(Model):
    '''
    Returns the float 32 vector of a given list of numbers
    '''
    def embed(self, emb_input):
        return np.array(emb_input).astype(np.float32).tobytes()

