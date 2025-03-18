# Copyright (C) 2025 Politecnico di Torino
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# This is a template for the golden function(s) that can be used to define the expected behaviour
# of TestIt tests. The golden function(s) should use the NumPy library, as TestIt produces NumPy tensors
# as input data and expects NumPy tensors as output data.

import numpy as np

def matrix_multiply(inputs: list, parameters: list) -> list:
    """
    Multiplies two NumPy matrices and returns the result.

    :param A: First matrix (NumPy array)
    :param B: Second matrix (NumPy array)
    :return: Resulting matrix (NumPy array)
    """
    matrix_A = inputs[0]
    matrix_B = inputs[1]

    # Check if multiplication is valid
    if matrix_A.shape[1] != matrix_B.shape[0]:  
        raise ValueError("Matrix dimensions do not match for multiplication!")

    result = np.matmul(matrix_A, matrix_A)

    return [result]