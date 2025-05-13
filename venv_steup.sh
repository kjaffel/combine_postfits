#!/bin/sh

use_singularity=true  # recommended 

if $use_singularity; then
    # need LCG106 version or above https://lcginfo.cern.ch/release/106/
    cms_env # for ingrid1-gwceci users 
    el9 bash
    source /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh
else
    # Install pyenv (once): https://github.com/pyenv/pyenv#installation
    #curl https://pyenv.run | bash
    
    #pyenv install -list # check available versions
    what=3.10.10         # Package 'combine-postfits' requires python >=3.10'
    
    # Add to ~/.bashrc or ~/.bash_profile
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv virtualenv-init -)"
    
    #pyenv install $what (only once)
    pyenv global $what
    
    # Create venv
    #pyenv virtualenv ${what} myenv${what}
    #pyenv activate myenv${what} 
fi

workdir=${HOME}/ # change if you want to

pushd ${workdir}

if [[ ! -d "combine_postfits" ]]; then
    git clone -o origin https://github.com/andrzejnovak/combine_postfits.git
    pushd combine_postfits  
    git remote add upstream https://github.com/kjaffel/combine_postfits.git
    git fetch upstream
fi

pushd combine_postfits
git checkout ForZAllbb_analysis 

#  only first time
#pip install -e .


