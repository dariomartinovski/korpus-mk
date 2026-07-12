#!/bin/bash

# Usage: ./generate_batches.sh <start_number> <end_number> <output_folder>
# Example: ./generate_batches.sh 1 110 ./output

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <start_number> <end_number> <output_folder>"
    echo "Example: $0 1 110 ./output"
    exit 1
fi

START=$1
END=$2
FOLDER=$3

# Validate that START and END are positive integers
if ! [[ "$START" =~ ^[0-9]+$ ]] || ! [[ "$END" =~ ^[0-9]+$ ]]; then
    echo "Error: start_number and end_number must be positive integers."
    exit 1
fi

if [ "$START" -gt "$END" ]; then
    echo "Error: start_number ($START) must be less than or equal to end_number ($END)."
    exit 1
fi

# Create the output folder if it doesn't exist
mkdir -p "$FOLDER"

echo "Generating batch files from batch$(printf '%03d' $START).json to batch$(printf '%03d' $END).json in '$FOLDER'..."

for i in $(seq "$START" "$END"); do
    filename=$(printf "%s/batch%03d.json" "$FOLDER" "$i")
    echo -n "" > "$filename"
done

echo "Done! $(($END - $START + 1)) file(s) created."