#!/bin/bash

signals=(
    nmssm_XtoYH 
    ggh )
modes=(
    jj_mass) # dnn 

for sig in ${signals[*]}; do 
    
    if [ "$sig" = "nmssm_XtoYH"]; then
        look_for='NMSSM_XtoYHto4B_'
    elif [ "$sig" = "ggh"]; then
        look_for='GluGlutoHHto4B_'
    fi 

    for mode in ${modes[*]}; do
    
        echo working on mode::: $mode
        path=hh/
    
        file_list=$(find "$path" -type f -name "fitDiagnostics*$look_for*$mode*.root")
        xlabel="$mode (GeV)"
        echo $file_list 
        # --fit : # {fit_s,fit_b,prefit,all}
        # --project-signals 2 \
        
        for fitDiagnostics in $file_list; do
            echo "$fitDiagnostics"
            output=$(dirname $fitDiagnostics)
            echo "Output dir:" $output
    
            combine_postfits -i $fitDiagnostics \
            				 --data \
            				 --unblind \
            				 --style hh/style_hh.yml \
            				 -vv \
                             -o $output \
            				 --fit all \
                             --xlabel "$xlabel" \
                             --lumi 61.90 \
            				 --year 2022 \
                             --sigs $sig \
                             --rmap $sig:r \
                             #--clipx true \
        done
    done
done
