# ALGLIB's minlp module has no generic name->id settings mechanism like
# cuOpt/CPLEX — just these two knobs, set via direct function calls
# (minlpsetalgodss/minlpsetalgoipm) in execute.py.
ALGLIB_PARAMETERS = [
    "algorithm",  # "dss" (dual simplex, default) or "ipm" (interior point method)
    "eps",  # convergence tolerance, float >= 0 (0 = library picks automatically)
]
