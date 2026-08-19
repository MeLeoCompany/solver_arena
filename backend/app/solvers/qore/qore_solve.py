"""Solves one MPS file with QORE, run under its own CPython 3.8 interpreter.

Standalone by design — no imports from the app package, since this file
is executed by a different interpreter than the rest of the codebase.
Talks to the parent (app.services.jobs.external_runner) purely through
files: reads a JSON job spec, writes the solver's own log lines to
log_path as it goes, and writes a small JSON result + solution once done.
"""
import json
import os
import sys
import time

# QORE's OptimizationStatus names -> this project's SolveStatus values.
# Anything not listed here (RUNNING, INTERRUPTED, NOT_FOUND) is left
# unmapped (solve_status=None) rather than guessed.
_STATUS_MAP = {
    "OPTIMAL": "optimal",
    "SUB_OPTIMAL": "feasible",
    "NODE_LIMIT_REACHED": "feasible",
    "INFEASIBLE": "infeasible",
    "UNBOUNDED": "unbounded",
    "TIME_LIMIT_REACHED": "timeout",
}

# Statuses meaning the solve never produced anything usable (bad model /
# unsupported problem type) rather than a legitimate solve outcome.
_FAILURE_STATUSES = {"NOT_STARTED", "INCORRECT_DATA"}


def _write_result(result_path, result):
    with open(result_path, "w") as f:
        json.dump(result, f)


def main():
    spec_path = sys.argv[1]
    with open(spec_path, "r") as f:
        spec = json.load(f)

    if spec.get("license_file"):
        os.environ["QORE_LICENSE_FILE"] = spec["license_file"]
    if spec.get("module_dir"):
        sys.path.insert(0, spec["module_dir"])

    log_path = spec["log_path"]
    log_file = open(log_path, "a")

    def log(message):
        log_file.write(message + "\n")
        log_file.flush()

    result = {
        "state": "failed",
        "solve_status": None,
        "raw_status": None,
        "objective": None,
        "solve_time": None,
        "error": None,
    }

    try:
        try:
            import qore_opt_py as qore
        except Exception as exc:
            raise RuntimeError("failed to import qore_opt_py: {}".format(exc))

        opt = qore.QoreOpt()
        config = (spec.get("config") or "").strip()
        if config:
            opt.set_configuration(config)
        opt.set_up_logger("")

        model = qore.QoreModel()
        loaded = model.read_model_from_file(spec["mps_path"])
        if not loaded:
            raise RuntimeError("failed to read MPS file: {}".format(spec["mps_path"]))

        log(
            "parsed MPS: {} variables, {} constraints".format(
                model.variables_count, model.constraints_count
            )
        )

        quad_rows = spec.get("quad_rows")
        if quad_rows:
            # read_model_from_file() silently drops QMATRIX — the parent
            # process parsed it separately and hands us the full symmetric
            # Hessian here; set_quadratic_objective() takes it as-is (same
            # 0.5*x^T*H*x, full-symmetric convention as the MPS file).
            hessian = [
                qore.MatrixTriplet(int(r), int(c), float(v))
                for r, c, v in zip(quad_rows, spec["quad_cols"], spec["quad_values"])
            ]
            model.set_quadratic_objective(hessian)
            log("injected {} quadratic objective terms (QP) that read_model_from_file dropped".format(len(hessian)))

        opt.set_model(model)
        started = time.time()
        status = opt.optimize()
        elapsed = time.time() - started

        status_name = status.name
        log("optimize finished: status={} time={:.3f}s".format(status_name, elapsed))

        result["raw_status"] = status_name
        result["solve_time"] = elapsed

        if status_name in _FAILURE_STATUSES:
            result["state"] = "failed"
            result["error"] = "solver returned {}".format(status_name)
        else:
            solution = opt.get_solution()
            values = list(solution.variables_values)
            if values:
                with open(spec["solution_path"], "w") as sf:
                    json.dump(values, sf)

            result["state"] = "done"
            result["solve_status"] = _STATUS_MAP.get(status_name)
            result["objective"] = solution.objective
    except Exception as exc:
        log("ERROR: {}".format(exc))
        result["state"] = "failed"
        result["error"] = str(exc)
    finally:
        log_file.close()

    _write_result(spec["result_path"], result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
