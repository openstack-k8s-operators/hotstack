#!/usr/bin/env python3

import subprocess
import sys
import yaml
import shutil


def get_nncp_yaml_documents(yaml_file):
    try:
        with open(yaml_file, "r") as f:
            documents = list(yaml.safe_load_all(f))
    except Exception as e:
        print(f"Error reading YAML file: {e}")
        sys.exit(1)

    return documents


def validate_nncp_documents(docs):
    # Process each document that has spec.desiredState
    for _idx, doc in enumerate(docs):
        if doc and "spec" in doc and "desiredState" in doc["spec"]:
            desired_state = doc["spec"]["desiredState"]

            # Convert the desiredState back to YAML for nmstatectl
            content = yaml.dump(desired_state, default_flow_style=False)

            # Validate with nmstatectl
            cmd = ["nmstatectl", "-q", "validate", "--"]
            try:
                subprocess.run(
                    cmd, input=content, text=True, capture_output=True, check=True
                )
            except subprocess.CalledProcessError as e:
                print(f"Document {_idx}: Validation failed")
                if e.stderr:
                    print(f"Error: {e.stderr.strip()}")
                sys.exit(1)
            except Exception as e:
                print(f"Document {_idx}: Error running nmstatectl - {e}")
                sys.exit(1)


def main():
    print(sys.argv)
    if len(sys.argv) < 2:
        print("Usage: nmstate_validate.py <yaml_file> <yaml_file> ...")
        sys.exit(1)

    # Check if nmstatectl is installed
    if not shutil.which("nmstatectl"):
        print("nmstatectl is not installed")
        sys.exit(0)

    for yaml_file in sys.argv[1:]:
        print(f"Validating {yaml_file}")
        documents = get_nncp_yaml_documents(yaml_file)
        validate_nncp_documents(documents)


if __name__ == "__main__":
    main()
