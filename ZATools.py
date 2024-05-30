import os
import json
import argparse
import ruamel

from ruamel.yaml import YAML

def WriteChannelOnPlotIt(channels, latex_opts):
    plotit_texts = {}
    for ch, cfg in channels.items():
        ch_per_bin = cfg[0].split('_')[4:]
        ch_per_bin[-1] = latex_opts[ch_per_bin[-1]]
        plotit_texts[ch] = ch_per_bin
    return plotit_texts

def get_cats_to_plot(channels):
    combine_cats_per_year = []
    all_ = []
    noCR = []
    for ch, cats in channels.items():
        c  = f"{ch}:{','.join(cats)}"
        c2 = f"{','.join(cats)}"
        combine_cats_per_year.append(c)
        all_.append(c2)
        if 'MuEl' not in c2:
            noCR.append(c2)
    #tot_cats = ';'.join(combine_cats_per_year)+f";fullrun2_{'_'.join(channels.keys())}:{','.join(all_)}" + f";fullrun2_noCR:{','.join(noCR)}"
    tot_cats = f"fullrun2_{'_'.join(channels.keys())}:{','.join(all_)}" + f";fullrun2_noCR:{','.join(noCR)}"
    
    reco = []
    region = []
    flavor = []
    texts = WriteChannelOnPlotIt(channels, latex_opts)
    for i, t in enumerate(texts.values()):
        nb, reg, flav = t
        if nb not in reco:
            reco.append(nb)
        if reg not in region:
            region.append(reg)
        if flav not in flavor:
            flavor.append(flav)

    catheader = f"{'+'.join(reco)} {'+'.join(region)}, {'+'.join(flavor)}"

    #print(tot_cats)
    print(tot_cats +'---'+ catheader)
    #print(catheader)

if __name__ == "__main__":
    latex_opts = {
        'ElEl'     : 'ee',
        'MuMu'     : '$\mu\mu$',
        'MuEl'     : '$\mu e$',
        'MuMu_ElEl': '$\mu\mu + ee$',
        'OSSF'     : '($\mu\mu + ee$)',
        'ElEl_MuEl': 'ee + $\mu e$',
        'MuMu_MuEl': '$\mu\mu + \mu e$',
        'OSSF_MuEl': '($\mu\mu + ee) + \mu e$',
        'MuMu_ElEl_MuEl': '$\mu\mu + ee + \mu e$',
    }

    parser = argparse.ArgumentParser(description='PreFit/PostFit Producer')
    parser.add_argument('-f', '--fitdiag', action='store', required=True, default=None, help='')
    options = parser.parse_args()

    basedir = os.path.dirname(options.fitdiag) 
    #FIXME
    with open(os.path.join(basedir.replace('ext1','ext1p1'), 'channels.json'), 'r') as file:
        channels = json.load(file)
    
    get_cats_to_plot(channels)
    yaml = YAML()
    with open("ZA/style_ZA_template.yml", 'r') as file:
        data = yaml.load(file)

    mass   = options.fitdiag.replace('.root','').split('_')
    mheavy = mass[-3] 
    mlight = mass[-1]

    if 'HToZA' in options.fitdiag: heavy, light = ['H', 'A']
    else:heavy, light = ['A', 'H']
    
    process    = f'gg{heavy}' if 'gg_fusion' in options.fitdiag else f'bb{heavy}' 
    #masslabel = f"{process}: $(m_{heavy},m_{light})= ({mheavy}, {mlight}) GeV$"
    masslabel  = f"{process}: $({mheavy}, {mlight}) GeV$"
    data['signal']['label'] = masslabel 
    data[process] = data.pop("signal")

    with open("ZA/style_ZA.yml", 'w') as file:
        yaml.dump(data, file)
