'''Tools for reblocking of data to remove serial correlation from data sets.'''

import numpy

def reblock(data, rowvar=1, ddof=None):
    '''Blocking analysis of correlated data.

Repeatedly average neighbouring data points in order to remove the effect of
serial correlation on the estimate of the standard error of a data set, as
described by Flyvbjerg and Petersen[1]_.  The standard error is constant (within error bars) once the correlation has been removed.

Parameters
----------
data: numpy.array
    1D or 2D array containing multiple variables and data points.  See `rowvar`.
rowvar: int
    If `rowvar` is non-zero (default) then each row represents a variable and
    each column a data point per variable.  Otherwise the relationship is
    swapped.
ddof: int
    If not ``None``, then the standard error and covariance are normalised by
    ``(N - ddof)``, where ``N`` is the number of data points per variable.
    Otherwise, the numpy default is used (i.e. ``(N - 1)``).

Returns
-------
list of tuples
    Statistics from each reblocking iteration.  Each tuple contains:

    iblock
        the blocking iteration.  Each iteration successively averages
        neighbouring pairs of data points.  The final data point is discarded if
        the number of data points is odd.
    mean
        the mean of each variable in the data set.
    cov
        the covariance matrix.
    std_err
        the standard error of each variable.
    std_err_err
        an estimate of the error in the standard error, assuming a Gaussian
        distribution.

    mean, cov, std_err and std_err_err are all numpy arrays.

References
----------
.. [1]  "Error estimates on averages of correlated data", H. Flyvbjerg and
H.G. Petersen, J. Chem. Phys. 91, 461 (1989).
'''
    
    if ddof is not None and ddof != int(ddof):
        raise ValueError("ddof must be integer")
    if ddof is None:
        ddof = 1

    if data.ndim > 2:
        raise RuntimeError("do not understand how to reblock in more than two dimensions.")

    if data.ndim == 1 or data.shape[0] == 1:
        rowvar = 1
        axis = 0
    elif rowvar:
        axis = 1
    else:
        axis = 0

    iblock = 0
    stats = []
    while data.shape[axis] >= 2:

        mean = numpy.array(numpy.mean(data, axis=axis))
        cov = numpy.cov(data, rowvar=rowvar, ddof=ddof)
        if cov.ndim < 2:
            std_err = numpy.array(numpy.sqrt(cov / data.shape[axis]))
        else:
            std_err = numpy.sqrt(cov.diagonal() / data.shape[axis])
        std_err_err =  std_err * 1.0/(numpy.sqrt(2*(data.shape[axis]-ddof)))
        stats.append( (iblock, mean, cov, std_err, std_err_err) )

        # last even-indexed value (ignore the odd one, if relevant)
        last = 2*int(data.shape[axis]/2)
        if data.ndim == 1 or not rowvar:
            data = (data[:last:2] + data[1:last:2]) / 2
        else:
            data = (data[:,:last:2] + data[:,1:last:2]) / 2
        iblock += 1

    return stats

def find_optimal_block(ndata, stats):
    '''Find the optimal block length from a reblocking calculation.

Inspect a reblocking calculation and find the block length which minimises the
stochastic error and removes the effect of correlation from the data set.  This
follows the procedures detailed by Wolff[1]_ and Lee et al.[2]_.

Parameters
----------
ndata: int
    number of data points ('observations') in the data set.
stats: list of tuples
    statistics in the format as returned by ``reblock``.

Returns
-------
list of int
    the optimal block index for each variable (i.e. the first block index in
    which the correlation has been removed).  If NaN, then the statistics
    provided were not sufficient to estimate the correlation length and more
    data should be collected.

Notes
-----
Wolff (Eq 47) and Lee et al. (Eq 14) give the optimal block size to be
    B^3 = 2 n n_corr^2
where n is the number of data points in the data set, B is the number of
data points in each 'block' (ie the data set has been divided into n/B
contiguous blocks) and n_corr
Following the scheme proposed by Lee et al, we hence look for the largest
block size which satisfies 
    B^3 >= 2 n n_corr^2.
From Eq 13 in Lee et al. (which they cast in terms of the variance):
    n_err SE = SE_{true}
where the 'error factor', n_err, is the square root of the estimated
correlation length,  SE is the standard error of the data set and
SE_{true} is the true standard error once the correlation length has been
taken into account.  Hence the condition becomes:
    B^3 >= 2 n (SE(B) / SE(0))**4
where SE(B) is the estimate of the standard error of the data divided in
blocks of size B.

References
----------
.. [1] "Monte Carlo errors with less errors", U. Wolff, Comput. Phys. Commun.
156, 143 (2004) and arXiv:hep-lat/0306017.
.. [2] "Strategies for improving the efficiency of quantum Monte Carlo
calculations", R. M. Lee, G. J. Conduit, N. Nemec, P. Lopez Rios, and N. D.
Drummond, Phys. Rev. E. 83, 066706 (2011).
'''

    # Get the number of variables by looking at the number of means calculated
    # in the first stats entry.
    nvariables = stats[0][1].size
    optimal_block = [float('NaN')]*nvariables
    # If the data was just of a single variable, then the numpy arrays returned
    # by blocking are all 0-dimensions.  Make sure they're 1-D so we can use
    # enumerate safely (just to keep the code short).
    std_err_first = numpy.array(stats[0][3], ndmin=1)
    for (iblock, mean, cov, std_err, std_err_err) in reversed(stats):
        # 2**iblock data points per block.
        B3 = 2**(3*iblock)
        std_err = numpy.array(std_err, ndmin=1)
        for (i, var_std_err) in enumerate(std_err):
            if B3 > 2*ndata*(var_std_err/std_err_first[i])**4:
                optimal_block[i] = iblock

    return optimal_block
