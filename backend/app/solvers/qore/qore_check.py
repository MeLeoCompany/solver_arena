"""Availability smoke-test for QORE, run under its own CPython 3.8 interpreter.

Standalone by design — no imports from the app package, since this file
is executed by a different interpreter than the rest of the codebase.
"""
import json
import os
import sys


def main():
    spec_path = sys.argv[1]
    with open(spec_path, "r") as f:
        spec = json.load(f)

    if spec.get("license_file"):
        os.environ["QORE_LICENSE_FILE"] = spec["license_file"]
    if spec.get("module_dir"):
        sys.path.insert(0, spec["module_dir"])

    try:
        import qore_opt_py as qore
    except Exception as exc:
        sys.stderr.write("import failed: {}\n".format(exc))
        return 1

    try:
        qore.QoreOpt()
    except Exception as exc:
        sys.stderr.write("license/init failed: {}\n".format(exc))
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
