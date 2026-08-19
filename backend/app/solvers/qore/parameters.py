# QORE has no discrete name=value parameter set like the other solvers —
# tuning goes through a single JSON configuration blob passed straight to
# QoreOpt.set_configuration(). The frontend renders one "config" field
# (a JSON textarea) for this solver instead of the usual flag autocomplete.
QORE_PARAMETERS = [
    "config",
]
