#!/bin/bash

era=fullrun2
dnn_cut='0p94'
modes=('mllbb' 'mbb') # 'dnn')
forceMuElCr=true
mergeCats=true
fit=fit_s       # {fit_s,fit_b,prefit,all}

workdir=/home/ucl/cp3/kjaffel/bamboodev/ZA_FullAnalysis/ZAStatAnalysis/

#path=ZA/unblinding_stage3__ext1p2_final/
#path=ZA/unblinding_stage3__ext2p3_mbb_mllbb/${dnn_cut}/MH-335.4_MA-82.14/bb_associatedProduction/ 
#path=ZA/unblinding_stage3__ext2p3_mbb_mllbb/${dnn_cut}/MH-846.11_MA-186.51/gg_fusion/'
#path=ZA/debug_large_excess_ver2/${dnn_cut}/MH-442.63_MA-95.27/gg_fusion/
#path=ZA/debug_large_excess_ver2/${dnn_cut}/MH-335.4_MA-82.14/gg_fusion/
#path=ZA/debug_large_excess_not_rebinned__ver2/${dnn_cut}/MH-335.4_MA-82.14/gg_fusion/
#path=ZA/debug_large_excess_ver2/${dnn_cut}/

lookfor=''
if $forceMuElCr; then
    lookfor='_MuEl_'
fi

plus_args=''
if $mergeCats; then
    plus_args=+' --cats '"${tot_cats}"
fi

for mode in ${modes[*]}; do

    echo Working on mode ... $mode
    path=$workdir/ul_combinerun2results/__ver15/floating_toponium/work__ULfullrun2/fit/$mode/2POIs_r/

    file_list=$(find "$path" -type f -name "fitDiagnostics*$lookfor*$mode*.root")
    
    if [ "$mode" = "dnn" ]; then
        xlabel="DNN output (ZA node)"
    else
        xlabel="$mode (GeV), cut dnn_score >= $dnn_cut"
    fi

    # --fit : # {fit_s,fit_b,prefit,all}
    # --project-signals 2 \
    
    for fitDiagnostics in $file_list; do
        
        output=$(dirname $fitDiagnostics)
        # Call the Python script and capture its output
        CMD="python3 ZATools.py --mode $mode -f $fitDiagnostics"
        inputs=$( $CMD 2>/dev/null | tail -n 1)
	    
        # Check if the Python script ran successfully
        if [ -z "$inputs" ]; then
            echo "Error running python3 ZATools.py --mode $mode -f $fitDiagnostics"
            eval $CMD  
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
        echo " - Total Categories: $tot_cats "
        echo " - Category Header: $catheader "
        echo " - Output dir: $output "
        
        combine_postfits -i $fitDiagnostics \
        				 --data \
        				 --unblind \
        				 --style ZA/style_ZA.yml \
        				 -vv \
        				 --clipx true \
        				 -o $output \
        				 --fit $fit \
                         --xlabel "$xlabel" \
                         --lumi 138 \
                         --catheader "$catheader" \
                         --cats "$tot_cats" \
                         #--sigs $sig \
                         #--rmap $sig:r \
        echo '================='
    done
done
