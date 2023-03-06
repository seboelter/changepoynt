# this file contains utility functions for handling and computing matrices needed for some of the algorithms in this
# package
import numpy as np
from numba import jit
from scipy.linalg import eigh_tridiagonal


@jit(nopython=True)
def power_method(a_matrix: np.ndarray, x_vector: np.ndarray, n_iterations: int) -> (float, np.ndarray):
    """
    This function searches the largest (dominant) eigenvalue and corresponding eigenvector by repeated multiplication
    of the matrix A with an initial vector. It assumes a dominant eigenvalue bigger than the second one, otherwise
    it won't converge.

    For proof and explanation look at:
    https://pythonnumericalmethods.berkeley.edu/notebooks/chapter15.02-The-Power-Method.html
    :param a_matrix: 2D-Matrix of size NxN filled with floats
    :param x_vector: Vector of size Nx1 filled with floats
    :param n_iterations: the amount of iterations for the approximation
    :return: the dominant eigenvalue and corresponding eigenvector
    """

    # go through the iterations and continue to scale the returned vector, so we do not reach extreme values
    # during the iteration we scale the vector by its maximum as we can than easily extract the eigenvalue
    for _ in range(n_iterations):

        # multiplication with a_matrix.T @ a_matrix as can be seen in explanation of
        # https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html
        x_vector = a_matrix.T @ a_matrix @ x_vector

        # scale the vector so we keep the values in bound
        x_vector = x_vector / np.max(x_vector)

    # get the normed eigenvector
    x_vector = x_vector / np.linalg.norm(x_vector)

    # get the corresponding eigenvalue
    eigenvalue = np.linalg.norm(a_matrix @ x_vector)
    return eigenvalue, (a_matrix @ x_vector)/eigenvalue


@jit(nopython=True)
def lanczos(a_matrix: np.ndarray, r_0: np.ndarray, k: int) -> (np.ndarray, np.ndarray):
    """
    This function computes the tri-diagonalization matrix from the square matrix C which is the result of the lanczos
    algorithm.

    The algorithm has been described and proven in:
    Idé, Tsuyoshi, and Koji Tsuda.
    "Change-point detection using krylov subspace learning."
    Proceedings of the 2007 SIAM International Conference on Data Mining.
    Society for Industrial and Applied Mathematics, 2007.

    :param a_matrix: 2D-Matrix of size NxN filled with floats where we want to find the krylov subspace approx. for
    :param r_0: intial starting vector for the subspace approximation
    :param k: size of the approximation
    :return: Returns the alpha and beta values for the tridiagonal, symmetric matrix T. alphas are the values from the
    main diagonal and beta from the off diagonal as described in
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.eigh_tridiagonal.html (alpha = d, beta = e)
    """

    # save the initial vector
    r_i = r_0
    q_i = np.zeros_like(r_i)

    # initialization of the diagonal elements
    alphas = np.zeros(shape=(k + 1,), dtype=np.float64)
    betas = np.ones(shape=(k + 1,), dtype=np.float64)

    # Subroutine 1 of the paper
    for j in range(k + 1):
        # compute r_(j+1)
        new_q = r_i / betas[j]

        # compute the new alpha
        alphas[j + 1] = new_q.T @ a_matrix @ new_q

        # compute the new r
        r_i = a_matrix @ new_q - alphas[j + 1] * new_q - betas[j] * q_i

        # compute the next beta
        betas[j + 1] = np.linalg.norm(r_i)

        # update the previous q
        q_i = new_q

    return alphas[1:], betas[1:-1]


def tridiagonal_eigenvalues(alphas: np.ndarray, betas: np.ndarray, amount=-1):
    """
    This function uses a fast approach for symmetric tridiagonal matrices to calculate the [amount] highest eigenvalues
    and corresponding eigenvectors.

    :param alphas: main diagonal elements
    :param betas: off diagonal elements
    :param amount: The amount of eigenvalues you want to compute (from the highest)
    :return: eigenvalues and corresponding eigenvectors
    """

    # check whether we need to use default parameters
    if amount < 0: amount = alphas.shape[0]

    # assertions about shape and dimensions as well as amount of eigenvectors
    assert 0 < amount <= alphas.shape[0], 'We can only calculate one to size of matrix eigenvalues.'
    assert alphas.ndim == 1, 'The alphas need to be vectors.'
    assert betas.ndim == 1, 'The betas need to be vectors.'
    assert alphas.shape[0] - 1 == betas.shape[0], 'Alpha size needs to be exactly one bigger than beta size.'

    # compute the decomposition
    eigenvalues, eigenvectors = eigh_tridiagonal(d=alphas, e=betas,
                                                 select='i', select_range=(alphas.shape[0]-amount, alphas.shape[0]-1))

    # return them to be in sinking order
    return eigenvalues[::-1], eigenvectors[:, ::-1]


if __name__ == '__main__':
    import time

    # set a random seed
    np.random.seed(1234)

    # create the random starting vector
    x = np.random.rand(100)
    x /= np.linalg.norm(x)
    A = np.random.rand(100, 100)

    # test the power method
    eigval, eigvec = power_method(A, x, n_iterations=100)
    eigvecs, eigvals, _ = np.linalg.svd(A)
    print(eigval, eigvals[0])

    # test the tridiagonalization method
    size = 1000
    d = 3 * np.random.rand(size)
    e = -1 * np.random.rand(size-1)
    start = time.time()
    tri_eigvals, tri_eigvecs = tridiagonal_eigenvalues(d, e, size//2)
    print(f'Specialized tridiagonal SVD took: {time.time()-start} s.')
    T = np.diag(d) + np.diag(e, k=1) + np.diag(e, k=-1)
    start = time.time()
    eigvecs, eigvals, _ = np.linalg.svd(T)
    print(f'Normal SVD took: {time.time() - start} s.')
