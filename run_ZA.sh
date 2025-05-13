#!/bin/bash

dnn_cut='0p94'
modes=('mllbb' 'mbb') # 'dnn')

#path=ZA/unblinding_stage3__ext1p2_final/
#path=ZA/unblinding_stage3__ext2p3_mbb_mllbb/${dnn_cut}/MH-335.4_MA-82.14/bb_associatedProduction/ 
#path=ZA/unblinding_stage3__ext2p3_mbb_mllbb/${dnn_cut}/MH-846.11_MA-186.51/gg_fusion/'
#path=ZA/debug_large_excess_ver2/${dnn_cut}/MH-442.63_MA-95.27/gg_fusion/
#path=ZA/debug_large_excess_ver2/${dnn_cut}/MH-335.4_MA-82.14/gg_fusion/
#path=ZA/debug_large_excess_not_rebinned__ver2/${dnn_cut}/MH-335.4_MA-82.14/gg_fusion/
path=ZA/debug_large_excess_ver2/${dnn_cut}/


for mode in ${modes[*]}; do

    echo working on mode::: $mode
    file_list=$(find "$path" -type f -name "fitDiagnostics*$mode*.root")
    
    if [ "$mode" = "dnn" ]; then
        xlabel="DNN output (ZA node)"
    else
        xlabel="$mode (GeV), cut dnn_score >= $dnn_cut"
    fi

    # --fit : # {fit_s,fit_b,prefit,all}
    # --project-signals 2 \
    
    for fitDiagnostics in $file_list; do
        echo "$fitDiagnostics"
        output=$(dirname $fitDiagnostics)
    
        # Call the Python script and capture its output
        echo python3 ZATools.py --mode $mode -f $fitDiagnostics
        inputs=$(python3 ZATools.py --mode $mode -f $fitDiagnostics 2>/dev/null | tail -n 1)
        
        # Check if the Python script ran successfully
        if [ -z "$inputs" ]; then
            echo "Error running python3 ZATools.py --mode $mode -f $fitDiagnostics"
            exit 1  # Exit the loop with an error status
        fi 
    
        # Use cut command to split the string into two parts using '---' as the delimiter
        tot_cats=$(awk -F '---' '{print $1}' <<< "$inputs")
        catheader=$(awk -F '---' '{print $2}' <<< "$inputs")
    
    	if [[ "$fitDiagnostics" == *"gg_fusion"* ]]; then
            sig="ggH"
        else
            sig="bbH"
        fi
        
        # Use the captured values in the Bash script
        echo "Total Categories: $tot_cats"
        echo "Category Header: $catheader"
        echo "Output dir:" $output
        
        echo combine_postfits -i $fitDiagnostics \
        				 --data \
        				 --unblind \
        				 --style ZA/style_ZA.yml \
        				 -vv \
        				 --clipx true \
        				 -o $output \
        				 --fit all \
                         --xlabel "$xlabel" \
                         --lumi 138 \
                         --cats "$tot_cats" \
                         --catheader "$catheader" 
                         #--sigs $sig \
                         #--rmap $sig:r \
    done
done
