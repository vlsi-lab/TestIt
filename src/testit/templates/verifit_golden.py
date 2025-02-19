# This is a template for the golden function(s) that can be used to define the expected behaviour 
# of TestIt tests. The golden function(s) should use the NumPy library, as TestIt produces NumPy tensors
# as input data and expects NumPy tensors as output data. 

import numpy as np

def matrix_multiply(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Multiplies two NumPy matrices and returns the result.

    :param A: First matrix (NumPy array)
    :param B: Second matrix (NumPy array)
    :return: Resulting matrix (NumPy array)
    """
    if A.shape[1] != B.shape[0]:  # Check if multiplication is valid
        raise ValueError("Matrix dimensions do not match for multiplication!")

    return np.matmul(A, B)  # Perform matrix multiplication