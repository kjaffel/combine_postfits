#!/bin/bash

path='ZA/unblinding_stage3__ext1'
file_list=$(find "$path" -type f -name "fitDiagnostics*MuEl*.root")


for fitDiagnostics in $file_list; do
    echo "$fitDiagnostics"
    output=$(dirname $fitDiagnostics)

    echo python3 zatools.py -f $fitDiagnostics
    # Call the Python script and capture its output
    inputs=$(python3 ZATools.py -f $fitDiagnostics 2>/dev/null | tail -n 1)
    
    # Check if the Python script ran successfully
    if [ -z "$inputs" ]; then
        echo "Error running python3 ZATools.py -f $fitDiagnostics"
        exit 1  # Exit the loop with an error status
    fi 

    # Use cut command to split the string into two parts using '---' as the delimiter
    tot_cats=$(awk -F '---' '{print $1}' <<< "$inputs")
    catheader=$(awk -F '---' '{print $2}' <<< "$inputs")
    
    # Use the captured values in the Bash script
    echo "Total Categories: $tot_cats"
    echo "Category Header: $catheader"
    echo "Output dir:" $output
    
    combine_postfits -i $fitDiagnostics \
    				 --data \
    				 --unblind \
    				 --style ZA/style_ZA.yml \
    				 -vv \
    				 --clipx false \
    				 -o $output \
    				 --fit all \
    				 --xlabel "DNN output" \
                     --cats "$tot_cats" \
                     #--catheader "$catheader" \
                     #--lumi 138 \
done
