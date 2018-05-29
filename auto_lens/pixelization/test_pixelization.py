from auto_lens.pixelization import pixelization

import pytest
import numpy as np
import math

class TestRegularizationMatrix(object):

    # The regularization matrix, H, is calculated by defining a set of B matrices which describe how source-plane
    # pixels map to one another. For example, if we had a 3x3 square grid:

    # ______
    # |0|1|2|
    # |3|4|5|
    # |6|7|8|
    # ^^^^^^^

    # Lets say we want to regularize this grid so that each square pixel is regularized with a pixel to its right and
    # below it.

    # So, 0 is regularized with pixels 1 and 3, pixel 1 with 2 and 4, but pixel 2 with only pixel 5, etc. So,
    #
    # We make two 9 x 9 B matrices, which describe regularization in each direction. So for regularization to the
    # right of each pixel:

    # B_x = [-1,  1,  0,  0,  0,  0,  0,  0,  0] # [0->1] This, row 0, correspodns to pixel 0 (signified by the -1). The 1's in columns 1 is saying we want to regularize pixel 0 with pixel 1.
    #       [ 0, -1,  1,  0,  0,  0,  0,  0,  0] # [1->2] Row 1 for pixel 1 (again, the -1 tells us this), regularized with pixels 2.
    #       [ 0,  0, -1,  0,  0,  0,  0,  0,  0] # [] NOTE - pixel 2 is NOT regularized with pixel 3 (check the square grid)!
    #       [ 0,  0,  0, -1,  1,  0,  0,  0,  0] # [3->4]
    #       [ 0,  0,  0,  0, -1,  1,  0,  0,  0] # [4->5]
    #       [ 0,  0,  0,  0,  0, -1,  0,  0,  0] # [] NOTE - pixel 5 not regularized with pixel 6!
    #       [ 0,  0,  0,  0,  0,  0, -1,  1,  0] # [6->7]
    #       [ 0,  0,  0,  0,  0,  0,  0, -1,  1] # [7->8]
    #       [ 0,  0,  0,  0,  0,  0,  0,  0, -1] # [] NOTE - Not regularized with anything

    # We now make another B matrix for the regularization beneath each pixel:

    # B_y = [-1,  0,  0,  1,  0,  0,  0,  0,  0] # [0->3] This, row 0, correspodns to pixel 0 (signified by the -1). The 1's in columns 3 is saying we want to regularize pixel 0 with pixel 3.
    #       [ 0, -1,  0,  0,  1,  0,  0,  0,  0] # [1->4] Row 1 for pixel 1 (again, the -1 tells us this), regularized with pixel 4
    #       [ 0,  0, -1,  0,  0,  1,  0,  0,  0] # [2->5]
    #       [ 0,  0,  0, -1,  0,  0,  1,  0,  0] # [3->6]
    #       [ 0,  0,  0,  0, -1,  0,  0,  1,  0] # [4->7]
    #       [ 0,  0,  0,  0,  0, -1,  0,  0,  1] # [5->8]
    #       [ 0,  0,  0,  0,  0,  0, -1,  0,  0] # [] No regularized performed in these last 3 rows / pixels
    #       [ 0,  0,  0,  0,  0,  0,  0, -1,  0] # []
    #       [ 0,  0,  0,  0,  0,  0,  0,  0, -1] # []

    # So, we basically just make B matrices representing regularization in each direction. For each, we can then compute
    # their corresponding regularization matrix, H, as, H = B * B.T (matrix multiplication)

    # So, H_x = B_x.T, * B_x H_y = B_y.T * B_y
    # And our overall regularization matrix, H = H_x + H_y

    # For an adaptive Voronoi grid, we do the exact same thing, however we make a B matrix for every shared Voronoi vertex
    # of each soure-pixel cluster. This means that the number of B matrices we compute is equal to the the number of
    # Voronoi vertices in the source-pixel with the most Voronoi vertices (i.e. the most neighbours a source-pixel has).

    ### COMBINING B MATRICES ###

    # Whereas the paper_plots above had each -1 going down the diagonal, this is not necessary. It valid to put each pairing
    # anywhere. So, if we had a 4x4 B matrix, where pixel 0 regularizes 1, 2 -> 3 and 3 -> 0, we can set this up
    # as one matrix even though the pixel 0 comes up twice!

    # B = [-1, 1, 0 ,0] # [0->1]
    #     [0, 0, 0 ,0] # We can skip rows by making them all zeros.
    #     [0, 0, -1 ,1] # [2->3]
    #     [1, 0, 0 ,-1] # [3->0] This is valid!

    # So, we don't have to make the same number of B matrices as Voronoi vertices, as we can combine them into a few B
    # matrices like this

    #### SKIPPING THE B MATRIX CALCULATION ####

    # The routine make_via_pixel_pairs doesn't use the B matrices to compute H at all!. They are used purely for testing.

    # This is because, if you know all the pairs between source pixels (which the Voronoi gridding can tell you), you
    # can bypass the B matrix multiplicaion entire and enter the values directly into the H matrix. Obviously, this saves
    # a huge amount of time and memory, but makes the routine hard to understand. Nevertheless, as the tests below confirm,
    # It produces a numerically equivalent result to the B matrices above.

    # It should be noted this routine is defined such that all pixels are regularized with one another (e.g. if 1->2,
    # then 2->1 as well). There are regularization schemes where this is not the case (i.e. 1->2 but not 2->1), however
    # For a constant regularization scheme this amounts to a scaling of the regularization coefficient. For a non-constant
    # shceme it wouldn't make sense to have directional regularization.

    #### WEIGHTED REGULARIZATION ####

    # The final thing we want to do is apply non-constant regularization. The idea here is that we given each source
    # pixel an 'effective regularization weight', instead of applying just one constant scheme overall. The AutoLens
    # paper motives why, but the idea is basically that different regions of the source-plane want different
    # levels of regularizations.

    # Say we have our regularization weights (see the code for how they are computed), how does this change our B matrix?
    # Well, we just multiple the regularization weight of each source-pixel by each row of B it has a -1 in, so:

    # regularization_weights = [1, 2, 3, 4]

    # B = [-1, 1, 0 ,0] # [0->1]
    #     [0, -2, 2 ,0] # [1->2]
    #     [0, 0, -3 ,3] # [2->3]
    #     [4, 0, 0 ,-4] # [3->0] This is valid!

    # If our -1's werent down the diagonal this would look like:

    # B = [4, 0, 0 ,-4] # [3->0]
    #     [0, -2, 2 ,0] # [1->2]
    #     [-1, 1, 0 ,0] # [0->1]
    #     [0, 0, -3 ,3] # [2->3] This is valid!

    # For the latter case, you can't just multiply regularization_weights by the matrix (as a vector). The pair routine
    # which computes H takes care of all of this :)

    def test__one_B_matrix_size_3x3__makes_correct_regularization_matrix(self):
        # Simple case, where we have just one regularization direction, regularizing pixel 0 -> 1 and 1 -> 2.

        # This means our B matrix is:

        # [-1, 1, 0]
        # [0, -1, 1]
        # [0, 0, -1]

        # Regularization Matrix, H = B * B.T.

        test_b_matrix = np.array([[-1, 1, 0],
                                  [1, -1, 0],
                                  [0, 0, 0]])

        test_regularization_matrix = np.matmul(test_b_matrix.T, test_b_matrix)

        no_verticies = np.array([1, 1, 0])
        pixel_pairs = np.array([[0, 1]])
        regularization_weights = np.ones((3))

        regularization_matrix = pixelization.setup_regularization_matrix_via_pixel_pairs(3, regularization_weights,
                                                                               no_verticies, pixel_pairs)

        assert (regularization_matrix == test_regularization_matrix).all()

    def test__one_B_matrix_size_4x4__makes_correct_regularization_matrix(self):
        test_b_matrix = np.array([[-1, 0, 1, 0],
                                  [0, -1, 0, 1],
                                  [1, 0, -1, 0],
                                  [0, 1, 0, -1]])

        test_regularization_matrix = np.matmul(test_b_matrix.T, test_b_matrix)

        no_verticies = np.array([1, 1, 1, 1])
        pixel_pairs = np.array([[0, 2], [1, 3]])
        regularization_weights = np.ones((4))

        regularization_matrix = pixelization.setup_regularization_matrix_via_pixel_pairs(4, regularization_weights,
                                                                               no_verticies, pixel_pairs)

        assert (regularization_matrix == test_regularization_matrix).all()

    def test__two_B_matrices_size_4x4__makes_correct_regularization_matrix(self):
        test_b_matrix_1 = np.array([[-1, 1, 0, 0],
                                    [0, -1, 1, 0],
                                    [0, 0, -1, 1],
                                    [1, 0, 0, -1]])

        test_regularization_matrix_1 = np.matmul(test_b_matrix_1.T, test_b_matrix_1)

        test_b_matrix_2 = np.array([[-1, 0, 0, 1],
                                    [1, -1, 0, 0],
                                    [0, 1, -1, 0],
                                    [0, 0, 1, -1]])

        test_regularization_matrix_2 = np.matmul(test_b_matrix_2.T, test_b_matrix_2)

        test_regularization_matrix = test_regularization_matrix_1 + test_regularization_matrix_2

        no_verticies = np.array([2, 2, 2, 2])
        pixel_pairs = np.array([[0, 1], [1, 2], [2, 3], [3, 0]])
        regularization_weights = np.ones((4))

        regularization_matrix = pixelization.setup_regularization_matrix_via_pixel_pairs(4, regularization_weights,
                                                                               no_verticies, pixel_pairs)

        assert (regularization_matrix == test_regularization_matrix).all()

    def test__two_B_matrices_size_4x4__makes_correct_regularization_matrix2(self):
        test_b_matrix_1 = np.matrix([[-1, 0, 1, 0],
                                     [0, -1, 1, 0],
                                     [1, 0, -1, 0],
                                     [1, 0, 0, -1]])

        test_regularization_matrix_1 = np.matmul(test_b_matrix_1.T, test_b_matrix_1)

        test_b_matrix_2 = np.matrix([[-1, 0, 0, 1],
                                     [0, 0, 0, 0],
                                     [0, 1, -1, 0],
                                     [0, 0, 0, 0]])

        test_regularization_matrix_2 = np.matmul(test_b_matrix_2.T, test_b_matrix_2)

        test_regularization_matrix = test_regularization_matrix_1 + test_regularization_matrix_2

        no_verticies = np.array([2, 1, 2, 1])
        pixel_pairs = np.array([[0, 2], [1, 2], [0, 3]])
        regularization_weights = np.ones((4))

        regularization_matrix = pixelization.setup_regularization_matrix_via_pixel_pairs(4, regularization_weights,
                                                                               no_verticies, pixel_pairs)

        assert (regularization_matrix == test_regularization_matrix).all()

    def test__two_pairs_two_B_matrices_size_3x3__makes_correct_regularization_matrix(self):
        # Here, we define the pixel_pairs first here and make the B matrices based on them.

        # You'll notice that actually, the B Matrix doesn't have to have the -1's going down the diagonal and we don't
        # have to have as many B matrices as we do the source pixel with the most Voronoi vertices. We can combine the
        # rows of each B matrix wherever we like ;0.

        pixel_pairs = np.array([[0, 1], [0, 2]])
        no_verticies = np.array([2, 1, 1])

        test_b_matrix_1 = np.array([[-1, 1, 0],  # Pair 1
                                    [-1, 0, 1],  # Pair 2
                                    [1, -1, 0]])  # Pair 1 flip

        test_regularization_matrix_1 = np.matmul(test_b_matrix_1.T, test_b_matrix_1)

        test_b_matrix_2 = np.array([[1, 0, -1],  # Pair 2 flip
                                    [0, 0, 0],
                                    [0, 0, 0]])

        test_regularization_matrix_2 = np.matmul(test_b_matrix_2.T, test_b_matrix_2)

        test_regularization_matrix = test_regularization_matrix_1 + test_regularization_matrix_2

        regularization_weights = np.ones((3))

        regularization_matrix = pixelization.setup_regularization_matrix_via_pixel_pairs(3, regularization_weights,
                                                                               no_verticies, pixel_pairs)


        assert (regularization_matrix == test_regularization_matrix).all()

    def test__eight_pairs_four_B_matrices_size_6x6__makes_correct_regularization_matrix(self):
        # Again, lets exploit the freedom we have when setting up our B matrices to make matching it to pairs a lot less
        # Stressful.

        pixel_pairs = np.array([[0, 2], [1, 2], [0, 3], [4, 5], [1, 5], [0, 4], [2, 3], [2, 5]])

        no_verticies = np.array([3, 2, 4, 2, 2, 3])

        test_b_matrix_1 = np.array([[-1, 0, 1, 0, 0, 0],  # Pair 1
                                    [0, -1, 1, 0, 0, 0],  # Pair 2
                                    [-1, 0, 0, 1, 0, 0],  # Pair 3
                                    [0, 0, 0, 0, -1, 1],  # Pair 4
                                    [0, -1, 0, 0, 0, 1],  # Pair 5
                                    [-1, 0, 0, 0, 1, 0]])  # Pair 6

        test_regularization_matrix_1 = np.matmul(test_b_matrix_1.T, test_b_matrix_1)

        test_b_matrix_2 = np.array([[0, 0, -1, 1, 0, 0],  # Pair 7
                                    [0, 0, -1, 0, 0, 1],  # Pair 8
                                    [0, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0]])

        test_regularization_matrix_2 = np.matmul(test_b_matrix_2.T, test_b_matrix_2)

        test_b_matrix_3 = np.array([[1, 0, -1, 0, 0, 0],  # Pair 1 flip
                                    [0, 1, -1, 0, 0, 0],  # Pair 2 flip
                                    [1, 0, 0, -1, 0, 0],  # Pair 3 flip
                                    [0, 0, 0, 0, 1, -1],  # Pair 4 flip
                                    [0, 1, 0, 0, 0, -1],  # Pair 5 flip
                                    [1, 0, 0, 0, -1, 0]])  # Pair 6 flip

        test_regularization_matrix_3 = np.matmul(test_b_matrix_3.T, test_b_matrix_3)

        test_b_matrix_4 = np.array([[0, 0, 1, -1, 0, 0],  # Pair 7 flip
                                    [0, 0, 1, 0, 0, -1],  # Pair 8 flip
                                    [0, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0]])

        test_regularization_matrix_4 = np.matmul(test_b_matrix_4.T, test_b_matrix_4)

        test_regularization_matrix = test_regularization_matrix_1 + test_regularization_matrix_2 + \
                                     test_regularization_matrix_3 + + test_regularization_matrix_4

        regularization_weights = np.ones((6))

        regularization_matrix = pixelization.setup_regularization_matrix_via_pixel_pairs(6, regularization_weights,
                                                                               no_verticies, pixel_pairs)

        assert (regularization_matrix == test_regularization_matrix).all()

    def test__one_B_matrix_size_3x3_variables_regularization_weights__makes_correct_regularization_matrix(self):
        # Simple case, where we have just one regularization direction, regularizing pixel 0 -> 1 and 1 -> 2.

        # This means our B matrix is:

        # [-1, 1, 0]
        # [0, -1, 1]
        # [0, 0, -1]

        # Regularization Matrix, H = B * B.T.I can

        regularization_weights = np.array([2.0, 4.0, 1.0])

        test_b_matrix = np.array([[-1, 1, 0],  # [[-2, 2, 0], (Matrix)
                                  [1, -1, 0],  # [4, -4, 0], (after)
                                  [0, 0, 0]])  # [0, 0,  0]]) (weights)

        test_b_matrix = (test_b_matrix.T * regularization_weights).T

        test_regularization_matrix = np.matmul(test_b_matrix.T, test_b_matrix)

        no_verticies = np.array([1, 1, 0])
        pixel_pairs = np.array([[0, 1]])

        regularization_matrix = pixelization.setup_regularization_matrix_via_pixel_pairs(3, regularization_weights,
                                                                               no_verticies, pixel_pairs)

        assert (regularization_matrix == test_regularization_matrix).all()

    def test__two_B_matrices_size_4x4_variables_regularization_weights__makes_correct_regularization_matrix(self):
        # Simple case, where we have just one regularization direction, regularizing pixel 0 -> 1 and 1 -> 2.

        # This means our B matrix is:

        # [-1, 1, 0]
        # [0, -1, 1]
        # [0, 0, -1]

        # Regularization Matrix, H = B * B.T.I can

        regularization_weights = np.array([2.0, 4.0, 1.0, 8.0])

        test_b_matrix_1 = np.array([[-2, 2, 0, 0],
                                    [-2, 0, 2, 0],
                                    [0, -4, 4, 0],
                                    [0, -4, 0, 4]])

        test_b_matrix_2 = np.array([[4, -4, 0, 0],
                                    [1, 0, -1, 0],
                                    [0, 1, -1, 0],
                                    [0, 8, 0, -8]])

        test_regularization_matrix_1 = np.matmul(test_b_matrix_1.T, test_b_matrix_1)
        test_regularization_matrix_2 = np.matmul(test_b_matrix_2.T, test_b_matrix_2)

        test_regularization_matrix = test_regularization_matrix_1 + test_regularization_matrix_2

        no_verticies = np.array([2, 3, 2, 1])
        pixel_pairs = np.array([[0, 1], [0, 2], [1, 2], [1, 3]])

        regularization_matrix = pixelization.setup_regularization_matrix_via_pixel_pairs(4, regularization_weights,
                                                                               no_verticies, pixel_pairs)

        assert (regularization_matrix == test_regularization_matrix).all()

    def test__four_B_matrices_size_6x6_with_regularization_weights__makes_correct_regularization_matrix(self):
        pixel_pairs = np.array([[0, 1], [0, 4], [1, 2], [1, 4], [2, 3], [2, 4], [2, 5], [3, 5], [4, 5]])
        no_verticies = np.array([2, 3, 4, 2, 4, 3])
        regularization_weights = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

        # I'm inputting the regularizationo weights directly thiss time, as it'd be a pain to multiply with a loop.

        test_b_matrix_1 = np.array([[-1, 1, 0, 0, 0, 0],  # Pair 1
                                    [-1, 0, 0, 0, 1, 0],  # Pair 2
                                    [0, -2, 2, 0, 0, 0],  # Pair 3
                                    [0, -2, 0, 0, 2, 0],  # Pair 4
                                    [0, 0, -3, 3, 0, 0],  # Pair 5
                                    [0, 0, -3, 0, 3, 0]])  # Pair 6

        test_b_matrix_2 = np.array([[0, 0, -3, 0, 0, 3],  # Pair 7
                                    [0, 0, 0, -4, 0, 4],  # Pair 8
                                    [0, 0, 0, 0, -5, 5],  # Pair 9
                                    [0, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0]])

        # Now do the same pairs but with the regularization direction and weights swapped.

        test_b_matrix_3 = np.array([[2, -2, 0, 0, 0, 0],  # Pair 1
                                    [5, 0, 0, 0, -5, 0],  # Pair 2
                                    [0, 3, -3, 0, 0, 0],  # Pair 3
                                    [0, 5, 0, 0, -5, 0],  # Pair 4
                                    [0, 0, 4, -4, 0, 0],  # Pair 5
                                    [0, 0, 5, 0, -5, 0]])  # Pair 6

        test_b_matrix_4 = np.array([[0, 0, 6, 0, 0, -6],  # Pair 7
                                    [0, 0, 0, 6, 0, -6],  # Pair 8
                                    [0, 0, 0, 0, 6, -6],  # Pair 9
                                    [0, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0]])

        test_regularization_matrix_1 = np.matmul(test_b_matrix_1.T, test_b_matrix_1)
        test_regularization_matrix_2 = np.matmul(test_b_matrix_2.T, test_b_matrix_2)
        test_regularization_matrix_3 = np.matmul(test_b_matrix_3.T, test_b_matrix_3)
        test_regularization_matrix_4 = np.matmul(test_b_matrix_4.T, test_b_matrix_4)

        test_regularization_matrix = test_regularization_matrix_1 + test_regularization_matrix_2 + \
                                     test_regularization_matrix_3 + test_regularization_matrix_4

        regularization_matrix = pixelization.setup_regularization_matrix_via_pixel_pairs(6, regularization_weights,
                                                                               no_verticies, pixel_pairs)

        assert (regularization_matrix == test_regularization_matrix).all()


class TestKMeans:

    def test__simple_points__sets_up_two_clusters(self):

        sparse_coordinates = np.array([[0.99, 0.99], [1.0, 1.0], [1.01, 1.01],
                                       [1.99, 1.99], [2.0, 2.0], [2.01, 2.01]])

        kmeans = pixelization.kmeans_cluster(sparse_coordinates, n_clusters=2)

        assert [2.0, 2.0] in kmeans.cluster_centers_
        assert [1.0, 1.0] in kmeans.cluster_centers_

        assert list(kmeans.labels_).count(0) == 3
        assert list(kmeans.labels_).count(1) == 3

    def test__simple_points__sets_up_three_clusters(self):

        sparse_coordinates = np.array([[-0.99, -0.99], [-1.0, -1.0], [-1.01, -1.01],
                                       [0.99, 0.99], [1.0, 1.0], [1.01, 1.01],
                                       [1.99, 1.99], [2.0, 2.0], [2.01, 2.01]])

        kmeans = pixelization.kmeans_cluster(sparse_coordinates, n_clusters=3)

        assert [2.0, 2.0] in kmeans.cluster_centers_
        assert [1.0, 1.0] in kmeans.cluster_centers_
        assert [-1.0, -1.0] in kmeans.cluster_centers_

        assert list(kmeans.labels_).count(0) == 3
        assert list(kmeans.labels_).count(1) == 3
        assert list(kmeans.labels_).count(2) == 3

    def test__simple_points__sets_up_three_clusters_more_points_in_third_cluster(self):

        sparse_coordinates = np.array([[-0.99, -0.99], [-1.0, -1.0], [-1.01, -1.01],

                                       [0.99, 0.99], [1.0, 1.0], [1.01, 1.01],
                                       [0.99, 0.99], [1.0, 1.0], [1.01, 1.01],

                                       [1.99, 1.99], [2.0, 2.0], [2.01, 2.01],
                                       [1.99, 1.99], [2.0, 2.0], [2.01, 2.01],
                                       [1.99, 1.99], [2.0, 2.0], [2.01, 2.01],
                                       [1.99, 1.99], [2.0, 2.0], [2.01, 2.01]])

        kmeans = pixelization.kmeans_cluster(sparse_coordinates, n_clusters=3)

        kmeans.cluster_centers_ = list(map(lambda x: pytest.approx(list(x), 1e-3), kmeans.cluster_centers_))

        assert [2.0, 2.0] in kmeans.cluster_centers_
        assert [1.0, 1.0] in kmeans.cluster_centers_
        assert [-1.0, -1.0] in kmeans.cluster_centers_

        assert list(kmeans.labels_).count(0) == 3 or 6 or 12
        assert list(kmeans.labels_).count(1) == 3 or 6 or 12
        assert list(kmeans.labels_).count(2) == 3 or 6 or 12

        assert list(kmeans.labels_).count(0) != list(kmeans.labels_).count(1) != list(kmeans.labels_).count(2)


class TestVoronoi:

    def test__points_in_x_cross_shape__sets_up_diamond_voronoi_vertices(self):
        # 5 points in the shape of the face of a 5 on a die - makes a diamond Voronoi diagram

        points = np.array([[-1.0, 1.0], [1.0, 1.0],
                           [0.0, 0.0],
                           [-1.0, -1.0], [1.0, -1.0]])

        voronoi = pixelization.setup_voronoi(points)

        voronoi.vertices = list(map(lambda x: list(x), voronoi.vertices))

        assert [0, 1.] in voronoi.vertices
        assert [-1., 0.] in voronoi.vertices
        assert [1., 0.] in voronoi.vertices
        assert [0., -1.] in voronoi.vertices

    def test__9_points_in_square___sets_up_square_of_voronoi_vertices(self):
        # 9 points in a square - makes a square (this is the example int he scipy documentaiton page)

        points = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0],
                           [0.0, 1.0], [1.0, 1.0], [2.0, 1.0],
                           [0.0, 2.0], [1.0, 2.0], [2.0, 2.0]])

        voronoi = pixelization.setup_voronoi(points)

        # ridge points is a numpy array for speed, but convert to list for the comparisons below so we can use in
        # to look for each list

        voronoi.vertices = list(map(lambda x: list(x), voronoi.vertices))

        assert [0.5, 1.5] in voronoi.vertices
        assert [1.5, 0.5] in voronoi.vertices
        assert [0.5, 0.5] in voronoi.vertices
        assert [1.5, 1.5] in voronoi.vertices

    def test__points_in_x_cross_shape__sets_up_pairs_of_voronoi_cells(self):
        # 5 points in the shape of the face of a 5 on a die - makes a diamond Voronoi diagram

        points = np.array([[-1.0, 1.0], [1.0, 1.0],
                           [0.0, 0.0],
                           [-1.0, -1.0], [1.0, -1.0]])

        voronoi = pixelization.setup_voronoi(points)

        # ridge points is a numpy array for speed, but convert to list for the comparisons below so we can use in
        # to look for each list

        voronoi.ridge_points = list(map(lambda x: list(x), voronoi.ridge_points))

        assert len(voronoi.ridge_points) == 8

        assert [2, 0] in voronoi.ridge_points or [0, 2] in voronoi.ridge_points
        assert [2, 1] in voronoi.ridge_points or [1, 2] in voronoi.ridge_points
        assert [2, 3] in voronoi.ridge_points or [3, 2] in voronoi.ridge_points
        assert [2, 4] in voronoi.ridge_points or [4, 2] in voronoi.ridge_points
        assert [0, 1] in voronoi.ridge_points or [1, 0] in voronoi.ridge_points
        assert [0.3] in voronoi.ridge_points or [3, 0] in voronoi.ridge_points
        assert [3, 4] in voronoi.ridge_points or [4, 3] in voronoi.ridge_points
        assert [4, 1] in voronoi.ridge_points or [1, 4] in voronoi.ridge_points

    def test__9_points_in_square___sets_up_pairs_of_voronoi_cells(self):
        # 9 points in a square - makes a square (this is the example int he scipy documentaiton page)

        points = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0],
                           [0.0, 1.0], [1.0, 1.0], [2.0, 1.0],
                           [0.0, 2.0], [1.0, 2.0], [2.0, 2.0]])

        voronoi = pixelization.setup_voronoi(points)

        # ridge points is a numpy array for speed, but convert to list for the comparisons below so we can use in
        # to look for each list

        voronoi.ridge_points = list(map(lambda x: list(x), voronoi.ridge_points))

        assert len(voronoi.ridge_points) == 12

        assert [0, 1] in voronoi.ridge_points or [1, 0] in voronoi.ridge_points
        assert [1, 2] in voronoi.ridge_points or [2, 1] in voronoi.ridge_points
        assert [3, 4] in voronoi.ridge_points or [4, 3] in voronoi.ridge_points
        assert [4, 5] in voronoi.ridge_points or [5, 4] in voronoi.ridge_points
        assert [6, 7] in voronoi.ridge_points or [7, 6] in voronoi.ridge_points
        assert [7, 8] in voronoi.ridge_points or [8, 7] in voronoi.ridge_points

        assert [0, 3] in voronoi.ridge_points or [3, 0] in voronoi.ridge_points
        assert [1, 4] in voronoi.ridge_points or [4, 1] in voronoi.ridge_points
        assert [4, 7] in voronoi.ridge_points or [7, 4] in voronoi.ridge_points
        assert [2, 5] in voronoi.ridge_points or [5, 2] in voronoi.ridge_points
        assert [5, 8] in voronoi.ridge_points or [8, 5] in voronoi.ridge_points
        assert [3, 6] in voronoi.ridge_points or [6, 3] in voronoi.ridge_points

    def test__points_in_x_cross_shape__neighbors_of_each_source_pixel_correct(self):
        # 5 points in the shape of the face of a 5 on a die - makes a diamond Voronoi diagram

        points = np.array([[-1.0, 1.0], [1.0, 1.0],
                           [0.0, 0.0],
                           [-1.0, -1.0], [1.0, -1.0]])

        voronoi = pixelization.setup_voronoi(points)

        assert voronoi.neighbors_total[0] == 3
        assert voronoi.neighbors_total[1] == 3
        assert voronoi.neighbors_total[2] == 4
        assert voronoi.neighbors_total[3] == 3
        assert voronoi.neighbors_total[4] == 3

        assert set(voronoi.neighbors[0]) == set([2, 1, 3])
        assert set(voronoi.neighbors[1]) == set([2, 0, 4])
        assert set(voronoi.neighbors[2]) == set([0, 1, 3, 4])
        assert set(voronoi.neighbors[3]) == set([2, 0, 4])
        assert set(voronoi.neighbors[4]) == set([2, 1, 3])

    def test__9_points_in_square___neighbors_of_each_source_pixel_correct(self):
        # 9 points in a square - makes a square (this is the example int he scipy documentaiton page)

        points = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0],
                           [0.0, 1.0], [1.0, 1.0], [2.0, 1.0],
                           [0.0, 2.0], [1.0, 2.0], [2.0, 2.0]])

        voronoi = pixelization.setup_voronoi(points)

        assert voronoi.neighbors_total[0] == 2
        assert voronoi.neighbors_total[1] == 3
        assert voronoi.neighbors_total[2] == 2
        assert voronoi.neighbors_total[3] == 3
        assert voronoi.neighbors_total[4] == 4
        assert voronoi.neighbors_total[5] == 3
        assert voronoi.neighbors_total[6] == 2
        assert voronoi.neighbors_total[7] == 3
        assert voronoi.neighbors_total[8] == 2

        assert set(voronoi.neighbors[0]) == set([1, 3])
        assert set(voronoi.neighbors[1]) == set([0, 2, 4])
        assert set(voronoi.neighbors[2]) == set([1, 5])
        assert set(voronoi.neighbors[3]) == set([0, 4, 6])
        assert set(voronoi.neighbors[4]) == set([1, 3, 5, 7])
        assert set(voronoi.neighbors[5]) == set([2, 4, 8])
        assert set(voronoi.neighbors[6]) == set([3, 7])
        assert set(voronoi.neighbors[7]) == set([4, 6, 8])
        assert set(voronoi.neighbors[8]) == set([5, 7])


class TestMatchCoordinatesFromClusters:

    def test__sub_coordinates_to_source_pixels_via_nearest_neighbour__case1__correct_pairs(self):

        source_pixels = np.array([[1.0, 1.0], [-1.0, 1.0], [-1.0, -1.0], [1.0, -1.0]])
        sub_coordinates = np.array([[[1.1, 1.1], [-1.1, 1.1], [-1.1, -1.1], [1.1, -1.1]]])
        image_total = 1
        sub_total = 4

        image_sub_to_source = pixelization.sub_coordinates_to_source_pixels_via_nearest_neighbour(
            sub_coordinates, image_total, sub_total, source_pixels)

        assert image_sub_to_source[0,0] == 0
        assert image_sub_to_source[0,1] == 1
        assert image_sub_to_source[0,2] == 2
        assert image_sub_to_source[0,3] == 3

    def test__sub_coordinates_to_source_pixels_via_nearest_neighbour___case2__correct_pairs(self):

        source_pixels = np.array([[1.0, 1.0], [-1.0, 1.0], [-1.0, -1.0], [1.0, -1.0]])
        sub_coordinates = np.array([[[1.1, 1.1], [-1.1, 1.1], [-1.1, -1.1], [1.1, -1.1]],
                                    [[0.9, -0.9], [-0.9, -0.9], [-0.9, 0.9], [0.9, 0.9]]])
        image_total = 2
        sub_total = 8

        image_sub_to_source = pixelization.sub_coordinates_to_source_pixels_via_nearest_neighbour(
            sub_coordinates, image_total, sub_total, source_pixels)

        assert image_sub_to_source[0,0] == 0
        assert image_sub_to_source[0,1] == 1
        assert image_sub_to_source[0,2] == 2
        assert image_sub_to_source[0,3] == 3
        assert image_sub_to_source[1,0] == 3
        assert image_sub_to_source[1,1] == 2
        assert image_sub_to_source[1,2] == 1
        assert image_sub_to_source[1,3] == 0

    def test__sub_coordinates_to_source_pixels_via_nearest_neighbour___case3__correct_pairs(self):

        source_pixels = np.array([[1.0, 1.0], [-1.0, 1.0], [-1.0, -1.0], [1.0, -1.0], [0.0, 0.0], [2.0, 2.0]])
        sub_coordinates = np.array([[[0.1, 0.1], [-0.1, -0.1], [0.49, 0.49]],
                                    [[0.51, 0.51], [1.01, 1.01], [1.51, 1.51]]])
        image_total = 2
        sub_total = 6

        image_sub_to_source = pixelization.sub_coordinates_to_source_pixels_via_nearest_neighbour(
            sub_coordinates, image_total, sub_total, source_pixels)

        assert image_sub_to_source[0,0] == 4
        assert image_sub_to_source[0,1] == 4
        assert image_sub_to_source[0,2] == 4
        assert image_sub_to_source[1,0] == 0
        assert image_sub_to_source[1,1] == 0
        assert image_sub_to_source[1,2] == 5

    def test__find_index_of_nearest_sparse_coordinate__simple_values(self):
        
        image_to_sparse = [0, 3, 2, 5, 1, 4]

        assert pixelization.find_nearest_sparse(0, image_to_sparse) == 0
        assert pixelization.find_nearest_sparse(1, image_to_sparse) == 3
        assert pixelization.find_nearest_sparse(2, image_to_sparse) == 2
        assert pixelization.find_nearest_sparse(3, image_to_sparse) == 5
        assert pixelization.find_nearest_sparse(4, image_to_sparse) == 1
        assert pixelization.find_nearest_sparse(5, image_to_sparse) == 4

    def test__find_index_of_nearest_sparse_source_pixel__simple_values(self):
        
        source_to_sparse = [0, 3, 2, 5, 1, 4]

        assert pixelization.find_nearest_sparse_source(0, source_to_sparse) == 0
        assert pixelization.find_nearest_sparse_source(1, source_to_sparse) == 3
        assert pixelization.find_nearest_sparse_source(2, source_to_sparse) == 2
        assert pixelization.find_nearest_sparse_source(3, source_to_sparse) == 5
        assert pixelization.find_nearest_sparse_source(4, source_to_sparse) == 1
        assert pixelization.find_nearest_sparse_source(5, source_to_sparse) == 4

    def test__find_separation_of_coordinate_and_nearest_sparse_source_pixel__simple_values(self):
        source_pixel_centers = [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]]

        sub_coordinate = [1.5, 0.0]

        nearest_sparse_source_pixel_index = 0

        separation0 = pixelization.find_separation_sub_coordinate_and_nearest_sparse_source(source_pixel_centers,
                                                                                  sub_coordinate,
                                                                                  nearest_sparse_source_pixel_index)

        nearest_sparse_source_pixel_index = 1

        separation1 = pixelization.find_separation_sub_coordinate_and_nearest_sparse_source(source_pixel_centers,
                                                                                  sub_coordinate,
                                                                                  nearest_sparse_source_pixel_index)

        nearest_sparse_source_pixel_index = 2

        separation2 = pixelization.find_separation_sub_coordinate_and_nearest_sparse_source(source_pixel_centers,
                                                                                  sub_coordinate,
                                                                                  nearest_sparse_source_pixel_index)

        assert separation0 == 1.5 ** 2
        assert separation1 == 0.5 ** 2
        assert separation2 == 0.5 ** 2

    def test__find_separation_and_index_of_nearest_neighboring_source_pixel__simple_case(self):
        sub_coordinate = np.array([0.0, 0.0])
        source_pixel_centers = np.array([[0.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, -0.5]])

        # Lets assume we're currently on source_pixel 0 and all other source_pixels are neighbors

        source_pixel_neighbors = [1, 2, 3, 4]

        index, separation = pixelization.find_separation_and_nearest_neighboring_source(sub_coordinate,
                                                                              source_pixel_centers,
                                                                              source_pixel_neighbors)

        assert separation == (-0.5) ** 2
        assert index == 4

    def test__find_separation_and_index_of_nearest_neighboring_source_pixel__skips_if_not_a_neighbor(self):
        sub_coordinate = np.array([0.0, 0.0])
        source_pixel_centers = np.array([[0.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, -0.5], [0.0, -0.01]])

        # Lets assume we're currently on source_pixel 0 and the new source_pixel added above is not a neighbor (this doesn't make
        # sense geometrically, but tests the code functionality).

        source_pixel_neighbors = [1, 2, 3, 4]

        index, separation = pixelization.find_separation_and_nearest_neighboring_source(sub_coordinate,
                                                                              source_pixel_centers,
                                                                              source_pixel_neighbors)

        assert separation == (-0.5) ** 2
        assert index == 4

    def test__sub_coordinates_to_source_pixels_via_sparse_pairs__source_pixels_in_x_shape__correct_pairs(self):

        source_centers = np.array([[-1.0, 1.0], [1.0, 1.0],
                                         [0.0, 0.0],
                                  [-1.0, -1.0], [1.0, -1.0]])

        # Make it so the central top, left, right and bottom coordinate all pair with the central source_pixel (index=2)

        sub_coordinates = np.array([[[-1.1, 1.1], [-0.9, 1.1], [-1.1, 0.9], [-0.9, 0.9]],
                                    [[-0.1, 0.1], [0.1, 0.1], [-0.1, -0.1], [0.1, -0.1]],
                                    [ [0.9, 1.1], [1.1, 1.1], [0.9, 0.9], [1.1, 0.9]]])

        image_total = 3
        sub_total = 12
        
        image_coordinates = np.array([[-1.0, 1.0], 
                                      [0.0, 0.0],
                                      [1.0, 1.0]])
    
        voronoi = pixelization.setup_voronoi(source_centers)

        image_sub_to_source_via_nearest_neighbour = pixelization.sub_coordinates_to_source_pixels_via_nearest_neighbour(
            sub_coordinates, image_total, sub_total, source_centers)

        # The sparse_grid coordinates are not required by the pairing routine routine below, but included here for clarity
        sparse_coordinates = np.array([[-1.0, 1.0], [0.0, 0.0], [1.0, 1.0]])

        image_to_sparse = np.array([0, 1, 2])

        sparse_to_source = np.array([1, 2, 4])

        image_sub_to_source_via_pairs = pixelization.sub_coordinates_to_source_pixels_via_sparse_pairs(
            sub_coordinates, image_total, sub_total, source_centers, voronoi.neighbors, image_to_sparse, sparse_to_source)

        assert (image_sub_to_source_via_nearest_neighbour == image_sub_to_source_via_pairs).all()

    def test__sub_coordinates_to_source_pixels_via_sparse_pairs__grid_of_source_pixels__correct_pairs(self):

        source_centers = np.array([[0.1, 0.1], [1.1, 0.1], [2.1, 0.1],
                                  [0.1, 1.1], [1.1, 1.1], [2.1, 1.1]])

        sub_coordinates = np.array([[[0.05, 0.15], [0.15, 0.15], [0.05, 0.05], [0.15, 0.05]],
                                    [[1.05, 0.15], [1.15, 0.15], [1.05, 0.05], [1.15, 0.05]],
                                    [[2.05, 0.15], [2.15, 0.15], [2.05, 0.05], [2.15, 0.05]],
                                    [[0.05, 1.15], [0.15, 1.15], [0.05, 1.05], [0.15, 1.05]],
                                    [[1.05, 1.15], [1.15, 1.15], [1.05, 1.05], [1.15, 1.05]],
                                    [[2.05, 1.15], [2.15, 1.15], [2.05, 1.05], [2.15, 1.05]]])

        image_total = 6
        sub_total = 24

        image_coordinates = np.array([[0.1, 0.1], [1.1, 0.1], [2.1, 0.1],
                                      [0.1, 1.1], [1.1, 1.1], [2.1, 1.1]])

        voronoi = pixelization.setup_voronoi(source_centers)

        image_sub_to_source_via_nearest_neighbour = pixelization.sub_coordinates_to_source_pixels_via_nearest_neighbour(
            sub_coordinates, image_total, sub_total, source_centers)

        # The sparse_grid coordinates are not required by the pairing routine routine below, but included here for clarity
        sparse_coordinates = np.array([[-0.9, -0.9], [1.0, 1.0], [2.0, 1.0]])

        image_to_sparse = np.array([0, 1, 2, 1, 1, 2])
        sparse_to_source = np.array([3, 4, 5])

        image_sub_to_source_via_pairs = pixelization.sub_coordinates_to_source_pixels_via_sparse_pairs(
            sub_coordinates, image_total, sub_total, source_centers, voronoi.neighbors,
            image_to_sparse, sparse_to_source)

        assert (image_sub_to_source_via_nearest_neighbour == image_sub_to_source_via_pairs).all()