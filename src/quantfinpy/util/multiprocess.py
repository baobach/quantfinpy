"""
Contains the logic from chapter 20 on multiprocessing and vectorization.
"""

# Start imports
import sys
import time
import datetime as dt

import multiprocessing as mp

import numpy as np
import pandas as pd

# End imports


# Snippet 20.5 (page 306), the lin_parts function
def lin_parts(num_atoms: int, num_threads: int) -> np.ndarray:
    """
    The simplest way to form molecules is to partition a list of atoms in subsets of equal size,
    where the number of subsets is the minimum between the number of processors and the number
    of atoms. For N subsets we need to find the N+1 indices that enclose the partitions.
    This logic is demonstrated in Snippet 20.5.

    This function partitions a list of atoms in subsets (molecules) of equal size.
    An atom is a set of indivisible set of tasks.

    Parameters
    ----------
    num_atoms : int
        Number of atoms.
    num_threads : int
        Number of processors.
    Returns
    -------
    np.ndarray
        Partition of atoms.
    Notes
    ---
    Reference: Advances in Financial Machine Learning, Snippet 20.5, page 306.
    """
    # Partition of atoms with a single loop
    parts = np.linspace(0, num_atoms, min(num_threads, num_atoms) + 1)
    parts = np.ceil(parts).astype(int)
    return parts


# Snippet 20.6 (page 308), The nested_parts function
def nested_parts(
    num_atoms: int, num_threads: int, upper_triangle: bool = False
) -> np.ndarray:
    """
    This function enables parallelization of nested loops.

    Parameters
    ----------
    num_atoms : int
        Number of atoms
    num_threads : int
        Number of processors
    upper_triangle : bool, optional
        Flag to order atoms as an upper triangular matrix (including the main diagonal), by default False

    Returns
    -------
    np.ndarray
        Partition of atoms

    Notes
    ---
    Reference: Advances in Financial Machine Learning, Snippet 20.6, page 308.
    """
    # Partition of atoms with an inner loop
    parts = [0]
    num_threads_ = min(num_threads, num_atoms)

    for _ in range(num_threads_):
        part = 1 + 4 * (
            parts[-1] ** 2 + parts[-1] + num_atoms * (num_atoms + 1.0) / num_threads_
        )
        part = (-1 + part**0.5) / 2.0
        parts.append(part)

    parts = np.round(parts).astype(int)

    if upper_triangle:  # The first rows are heaviest
        parts = np.cumsum(np.diff(parts)[::-1])
        parts = np.append(np.array([0]), parts)

    return parts


# Snippet 20.7 (page 310), The `mp_pandas_obj` function, a wrapper for mp_pandas_obj used at various points in the book
def mp_pandas_obj(
    func: callable,
    pd_obj: tuple,
    num_threads: int = 24,
    mp_batches: int = 1,
    lin_mols: bool = True,
    verbose: bool = True,
    **kargs
) -> pd.DataFrame:
    """
    Parallelize jobs, return a dataframe or series.

    Example: df1=mp_pandas_obj(func,('molecule',df0.index),24,**kwds)

    First, atoms are grouped into molecules, using linParts (equal number of atoms per molecule)
    or nestedParts (atoms distributed in a lower-triangular structure). When mpBatches is greater
    than 1, there will be more molecules than cores. Suppose that we divide a task into 10 molecules,
    where molecule 1 takes twice as long as the rest. If we run this process in 10 cores, 9 of the
    cores will be idle half of the runtime, waiting for the first core to process molecule 1.
    Alternatively, we could set mpBatches=10 so as to divide that task in 100 molecules. In doing so,
    every core will receive equal workload, even though the first 10 molecules take as much time as the
    next 20 molecules. In this example, the run with mpBatches=10 will take half of the time consumed by
    mpBatches=1.

    Second, we form a list of jobs. A job is a dictionary containing all the information needed to process
    a molecule, that is, the callback function, its keyword arguments, and the subset of atoms that form
    the molecule.

    Third, we will process the jobs sequentially if numThreads==1 (see Snippet 20.8), and in parallel
    otherwise (see Section 20.5.2). The reason that we want the option to run jobs sequentially is for
    debugging purposes. It is not easy to catch a bug when programs are run in multiple processors.
    Once the code is debugged, we will want to use numThreads>1.

    Fourth, we stitch together the output from every molecule into a single list, series, or dataframe.

    Parameters
    ----------
    func : function
        A callback function, which will be executed in parallel.
    pd_obj : tuple
        Element 0: The name of the argument used to pass molecules to the callback function.
        Element 1: A list of indivisible tasks (atoms), which will be grouped into molecules.
    num_threads : int
        The number of threads that will be used in parallel (one processor per thread).
    mp_batches : int
        Number of parallel batches (jobs per core).
    lin_mols : bool
        Tells if the method should use linear or nested partitioning.
    verbose : bool
        Flag to report progress on asynch jobs.
    **kargs : var args
        Keyword arguments needed by functions.

    Returns
    -------
    pd.DataFrame
        The result of the parallelized jobs.

    Notes
    -----
    Advances in Financial Machine Learning, Snippet 20.7, page 310.
    """

    if lin_mols:
        parts = lin_parts(len(pd_obj[1]), num_threads * mp_batches)
    else:
        parts = nested_parts(len(pd_obj[1]), num_threads * mp_batches)

    jobs = []
    for i in range(1, len(parts)):
        job = {pd_obj[0]: pd_obj[1][parts[i - 1] : parts[i]], "func": func}
        job.update(kargs)
        jobs.append(job)

    if num_threads == 1:
        out = process_jobs_(jobs)
    else:
        out = process_jobs(jobs, num_threads=num_threads, verbose=verbose)

    if isinstance(out[0], pd.DataFrame):
        df0 = pd.DataFrame()
    elif isinstance(out[0], pd.Series):
        df0 = pd.Series(dtype="float64")
    else:
        return out

    for i in out:
        df0 = pd.concat(
            out, axis=0
        )  # Update from old version that used append(i) which is incorrect. Concat is much more efficient.

    df0 = df0.sort_index()
    return df0


# Snippet 20.8, pg 311, Single thread execution, for debugging
def process_jobs_(jobs) -> list:
    """
    Single thread execution, for debugging.

    Run jobs sequentially, for debugging.

    Parameters
    ----------
    jobs : list
        List of jobs (molecules).

    Returns
    -------
    list
        Results of jobs.

    Notes
    -----
    Advances in Financial Machine Learning, Snippet 20.8, page 311.
    """
    out = []
    for job in jobs:
        out_ = expand_call(job)
        out.append(out_)

    return out


# Snippet 20.10 Passing the job (molecule) to the callback function
def expand_call(kargs):
    """
    Passing the job (molecule) to the callback function.

    Expand the arguments of a callback function, kargs['func'].

    Parameters
    ----------
    kargs : dict
        Dictionary containing the arguments needed by the callback function.

    Returns
    -------
    object
        The result of the callback function.

    Notes
    -----
    Advances in Financial Machine Learning, Snippet 20.10.
    """
    func = kargs["func"]
    del kargs["func"]
    out = func(**kargs)
    return out


# Snippet 20.9.1, pg 312, Example of Asynchronous call to pythons multiprocessing library
def report_progress(job_num: int, num_jobs: int, time0: float, task: str) -> None:
    """
        Example of Asynchronous call to pythons multiprocessing library

    Parameters
    ----------
    job_num : int
        Number of current job.
    num_jobs : int
        Total number of jobs.
    time0 : float
        Start time.
    task : str
        Task description.

    Notes
    -----
    Advances in Financial Machine Learning, Snippet 20.9.1, pg 312.
    """
    # Report progress as asynch jobs are completed
    msg = [float(job_num) / num_jobs, (time.time() - time0) / 60.0]
    msg.append(msg[1] * (1 / msg[0] - 1))
    time_stamp = str(dt.datetime.fromtimestamp(time.time()))

    msg = (
        time_stamp
        + " "
        + str(round(msg[0] * 100, 2))
        + "% "
        + task
        + " done after "
        + str(round(msg[1], 2))
        + " minutes. Remaining "
        + str(round(msg[2], 2))
        + " minutes."
    )

    if job_num < num_jobs:
        sys.stderr.write(msg + "\r")
    else:
        sys.stderr.write(
            msg + "\n"
        )  # Snippet 20.9.2, pg 312, Example of Asynchronous call to pythons multiprocessing library


def process_jobs(
    jobs: list, task: str = None, num_threads: int = 24, verbose: bool = True
) -> None:
    """
    Example of Asynchronous call to pythons multiprocessing library

    Run in parallel. jobs must contain a 'func' callback, for expand_call

    Parameters
    ----------
    jobs : list
        List of jobs (molecules).
    task : str
        Task description.
    num_threads : int
        The number of threads that will be used in parallel (one processor per thread).
    verbose : bool
        Flag to report progress on asynch jobs.

    Notes
    -----
    Advances in Financial Machine Learning, Snippet 20.9.2, pg 312.
    """

    if task is None:
        task = jobs[0]["func"].__name__

    pool = mp.Pool(processes=num_threads)
    outputs = pool.imap_unordered(expand_call, jobs)
    out = []
    time0 = time.time()

    # Process asynchronous output, report progress
    for i, out_ in enumerate(outputs, 1):
        out.append(out_)
        if verbose:
            report_progress(i, len(jobs), time0, task)

    pool.close()
    pool.join()  # This is needed to prevent memory leaks
    return out
