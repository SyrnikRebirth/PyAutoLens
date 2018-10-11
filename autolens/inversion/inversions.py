import numba
import numpy as np

from autolens import exc


# TODO : Unit test this properly, using a cleverly made mock data-set

def inversion_from_mapper_regularization_and_data(image, noise_map, convolver, mapper, regularization):
    blurred_mapping_matrix = convolver.convolve_mapping_matrix(mapping_matrix=mapper.mapping_matrix)

    data_vector = data_vector_from_blurred_mapping_matrix_and_data(blurred_mapping_matrix=blurred_mapping_matrix,
                                                                   image=image, noise_map=noise_map)

    curvature_matrix = curvature_matrix_from_blurred_mapping_matrix(blurred_mapping_matrix=blurred_mapping_matrix,
                                                                    noise_map=noise_map)

    # TODO : Turn into factory for different regularization schemes (e.g. Constant / Weighted need different input)

    regularization_matrix = regularization.regularization_matrix_from_pixel_neighbors(
        pixel_neighbors=mapper.pixel_neighbors)

    curvature_reg_matrix = np.add(curvature_matrix, regularization_matrix)

    solution_vector = np.linalg.solve(curvature_reg_matrix, data_vector)

    return Inversion(blurred_mapping_matrix=blurred_mapping_matrix, regularization_matrix=regularization_matrix,
                     curvature_matrix=curvature_matrix, curvature_reg_matrix=curvature_reg_matrix,
                     solution_vector=solution_vector)


@numba.jit(nopython=True, cache=True)
def data_vector_from_blurred_mapping_matrix_and_data(blurred_mapping_matrix, image, noise_map):
    """ Compute the curvature_matrix matrix directly - used to integration_old test that our curvature_matrix matrix generator approach
    truly works."""

    mapping_shape = blurred_mapping_matrix.shape

    data_vector = np.zeros(mapping_shape[1])

    for image_index in range(mapping_shape[0]):
        for pix_index in range(mapping_shape[1]):
            data_vector[pix_index] += image[image_index] * \
                                      blurred_mapping_matrix[image_index, pix_index] / (noise_map[image_index] ** 2.0)

    return data_vector


def curvature_matrix_from_blurred_mapping_matrix(blurred_mapping_matrix, noise_map):
    flist = np.zeros(blurred_mapping_matrix.shape[0])
    iflist = np.zeros(blurred_mapping_matrix.shape[0], dtype='int')
    return curvature_matrix_from_blurred_mapping_matrix_jit(blurred_mapping_matrix, noise_map, flist, iflist)


@numba.jit(nopython=True, cache=True)
def curvature_matrix_from_blurred_mapping_matrix_jit(blurred_mapping_matrix, noise_map, flist, iflist):
    curvature_matrix = np.zeros((blurred_mapping_matrix.shape[1], blurred_mapping_matrix.shape[1]))

    for image_index in range(blurred_mapping_matrix.shape[0]):
        index = 0
        for pixel_index in range(blurred_mapping_matrix.shape[1]):
            if blurred_mapping_matrix[image_index, pixel_index] > 0.0:
                index += 1
                flist[index] = blurred_mapping_matrix[image_index, pixel_index] / noise_map[image_index]
                iflist[index] = pixel_index

        if index > 0:
            for i1 in range(index + 1):
                for j1 in range(index + 1):
                    ix = iflist[i1]
                    iy = iflist[j1]
                    curvature_matrix[ix, iy] += flist[i1] * flist[j1]

    for i in range(blurred_mapping_matrix.shape[1]):
        for j in range(blurred_mapping_matrix.shape[1]):
            curvature_matrix[i, j] = curvature_matrix[j, i]

    return curvature_matrix


@numba.jit(nopython=True, cache=True)
def reconstructed_data_vector_from_blurred_mapping_matrix_and_solution_vector(blurred_mapping_matrix, solution_vector):
    """ Map the reconstructed_image pix s_vector back to the masked_image-plane to compute the inversion's model-masked_image.
    """
    reconstructed_data_vector = np.zeros(blurred_mapping_matrix.shape[0])
    for i in range(blurred_mapping_matrix.shape[0]):
        for j in range(solution_vector.shape[0]):
            reconstructed_data_vector[i] += solution_vector[j] * blurred_mapping_matrix[i, j]

    return reconstructed_data_vector


class Inversion(object):

    def __init__(self, blurred_mapping_matrix, regularization_matrix, curvature_matrix, curvature_reg_matrix,
                 solution_vector):
        """The matrices, mappings which have been used to linearly invert and fit a data-set.

        Parameters
        -----------
        blurred_mapping_matrix : ndarray | None
            The matrix representing the mapping_matrix between reconstructed_image-pixels and data-pixels, including a \
            blurring operation (f).
        regularization_matrix : ndarray | None
            The matrix defining how the reconstructed_image's pixels are regularized with one another (H).
        curvature_matrix : ndarray | None
            The curvature_matrix between each reconstructed_image pixel and all other reconstructed_image pixels (F).
        curvature_reg_matrix : ndarray | None
            The curvature_matrix + regularizationo matrix.
        reconstructed_image : ndarray | None
            The vector containing the reconstructed fit of the data.
        """
        self.blurred_mapping_matrix = blurred_mapping_matrix
        self.regularization_matrix = regularization_matrix
        self.curvature_matrix = curvature_matrix
        self.curvature_reg_matrix = curvature_reg_matrix
        self.solution_vector = solution_vector

    @property
    def reconstructed_data_vector(self):
        return reconstructed_data_vector_from_blurred_mapping_matrix_and_solution_vector(self.blurred_mapping_matrix,
                                                                                         self.solution_vector)

    @property
    def regularization_term(self):
        """ Compute the regularization_matrix term of a inversion's Bayesian likelihood function. This represents the sum \
         of the difference in fluxes between every pair of neighboring pixels. This is computed as:

         s_T * H * s = s_vector.T * regularization_matrix_const * s_vector

         The term is referred to as 'G_l' in Warren & Dye 2003, Nightingale & Dye 2015.

         The above works include the regularization_matrix coefficient (lambda) in this calculation. In PyAutoLens, this is  \
         already in the regularization_matrix matrix and thus included in the matrix multiplication.
         """
        return np.matmul(self.solution_vector.T, np.matmul(self.regularization_matrix, self.solution_vector))

    @property
    def log_det_curvature_reg_matrix_term(self):
        return self.log_determinant_of_matrix_cholesky(self.curvature_reg_matrix)

    @property
    def log_det_regularization_matrix_term(self):
        return self.log_determinant_of_matrix_cholesky(self.regularization_matrix)

    @staticmethod
    def log_determinant_of_matrix_cholesky(matrix):
        """There are two terms in the inversion's Bayesian likelihood function which require the log determinant of \
        a matrix. These are (Nightingale & Dye 2015, Nightingale, Dye and Massey 2018):

        ln[det(F + H)] = ln[det(cov_reg_matrix)]
        ln[det(H)]     = ln[det(regularization_matrix_const)]

        The cov_reg_matrix is positive-definite, which means its log_determinant can be computed efficiently \
        (compared to using np.det) by using a Cholesky decomposition first and summing the log of each diagonal term.

        Parameters
        -----------
        matrix : ndarray
            The positive-definite matrix the log determinant is computed for.
        """
        try:
            return 2.0 * np.sum(np.log(np.diag(np.linalg.cholesky(matrix))))
        except np.linalg.LinAlgError:
            raise exc.InversionException()
