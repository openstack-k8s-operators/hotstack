#!/bin/bash

set -x

if ! command -v nmstatectl; then
    echo "nmstatectl is not installed"
    exit 0
fi

if ! command -v yq; then
    echo "yq is not installed"
    exit 0
fi

for document_idx in $(yq '.spec.desiredState | document_index' "$1" | grep -v "\---")
do
    yq ".spec.desiredState | select(document_index == $document_idx)" "$1" | nmstatectl -q validate --
done
