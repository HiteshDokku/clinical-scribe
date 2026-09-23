import argparse
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True)
    parser.add_argument("--out-py", required=True)
    parser.add_argument("--out-ts", required=True)
    args = parser.parse_args()

    schema_path = Path(args.schema).resolve()
    py_dir = Path(args.out_py).resolve()
    ts_dir = Path(args.out_ts).resolve()

    py_dir.mkdir(parents=True, exist_ok=True)
    ts_dir.mkdir(parents=True, exist_ok=True)

    py_out = py_dir / "soap_note.py"
    ts_out = ts_dir / "soap_note.ts"

    print(f"Generating Python models to {py_out}...")
    # Generate Python using datamodel-code-generator via uvx
    py_cmd = [
        "uvx", "--from", "datamodel-code-generator", "datamodel-codegen",
        "--input", str(schema_path),
        "--input-file-type", "jsonschema",
        "--output", str(py_out),
        "--output-model-type", "pydantic_v2.BaseModel",
        "--use-standard-collections",
        "--use-union-operator",
        "--target-python-version", "3.12"
    ]
    try:
        subprocess.run(py_cmd, check=True, shell=sys.platform == "win32")
    except subprocess.CalledProcessError as e:
        print(f"Failed to generate Python models: {e}")
        sys.exit(1)

    print(f"Generating TypeScript interfaces to {ts_out}...")
    # Generate TypeScript using json-schema-to-typescript via npx
    # use cmd /c npx on Windows
    ts_cmd = ["npx", "json-schema-to-typescript", str(schema_path), "-o", str(ts_out)]
    if sys.platform == "win32":
        ts_cmd = ["cmd", "/c"] + ts_cmd
        
    try:
        subprocess.run(ts_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to generate TypeScript models: {e}")
        sys.exit(1)

    print("Contracts generated successfully.")

if __name__ == "__main__":
    main()
