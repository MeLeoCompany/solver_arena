"""Regenerates qore_opt_py's .pyi stub via mypy's stubgen, run under QORE's
own CPython 3.8 interpreter — stubgen has to import the compiled extension
module to introspect it (no source to read), same ABI constraint as
qore_solve.py/qore_check.py.

Standalone by design — no imports from the app package.
"""
import json
import sys


def main():
    spec_path = sys.argv[1]
    with open(spec_path, "r") as f:
        spec = json.load(f)

    sys.path.insert(0, spec["module_dir"])

    try:
        from mypy.stubgen import main as stubgen_main
    except ImportError as exc:
        sys.stderr.write("mypy not installed for this interpreter: {}\n".format(exc))
        return 1

    try:
        stubgen_main(["-m", "qore_opt_py", "-o", spec["output_dir"]])
    except SystemExit as exc:
        if exc.code not in (0, None):
            sys.stderr.write("stubgen exited with code {}\n".format(exc.code))
            return 1
    except Exception as exc:
        sys.stderr.write("stubgen crashed: {}\n".format(exc))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
