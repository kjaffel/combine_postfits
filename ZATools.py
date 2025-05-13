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


def get_cats_to_plot(mode, channels):
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
    #tot_cats = ';'.join(combine_cats_per_year)+f";fullrun2_{'_'.join(channels.keys())}:{','.join(all_)}" #+ f";fullrun2_noCR:{','.join(noCR)}"
    tot_cats = f"fullrun2_{mode}_{'_'.join(channels.keys())}:{','.join(all_)}" + f";fullrun2_noCR_{mode}:{','.join(noCR)}"
    
    reco = []
    region = []
    flavor = []
    """
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
    """
    catheader = ''
    #print(tot_cats)
    #print(catheader)
    print(tot_cats +'---'+ catheader)
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PreFit/PostFit Producer')
    parser.add_argument('-f', '--fitdiag', action='store', required=True, default=None, help='')
    parser.add_argument('--mode', action='store', required=True, choices=['dnn', 'mbb', 'mllbb'], help='')
    options = parser.parse_args()
    
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

    if 'HToZA' in options.fitdiag: heavy, light = ['H', 'A']
    else: heavy, light = ['A', 'H']
    
    mode = options.mode
    forceMuElCr = True

    # .e.g. fitDiagnosticsHToZATo2L2B_gg_fusion_nb2_resolved_boosted_OSSF_mbb_MH_442.63_MA_95.27.root
    opts = options.fitdiag.split('/')[-1].split('_')
    prod = '_'.join(opts[1:3])
    nb   = opts[3] 
    process = f'gg{heavy}' if prod == 'gg_fusion' else f'bb{heavy}' 
    basedir = os.path.dirname(options.fitdiag) 
    catname = options.fitdiag.replace('.root', '').split('/')[-1].split(prod)[-1].split(f'_{mode}_')[0] 
    
    #================== FIXME
    #with open(os.path.join(basedir, f'channels{catname}_fit_b.json'), 'r') as file:
    with open(os.path.join(basedir, f'channels_{mode}_{nb}_resolved_boosted_OSSF_fit_b.json'), 'r') as file:
        channels = json.load(file)
    if not channels:
        with open(os.path.join(basedir, f'channels_{mode}_{nb}_resolved_boosted_OSSF_fit_s.json'), 'r') as file:
            channels = json.load(file)
    if not channels:
        ch_per_year = options.fitdiag.replace('.root', '').split('/')[-1].split('OSSF_')[-1]
        channels ={'ch1': [f"{ch_per_year}_{era}".replace('.','p') for era in ['UL16', 'UL17', 'UL18']]}
    #===================

    get_cats_to_plot(mode, channels)
    yaml = YAML()
    with open("ZA/style_ZA_template.yml", 'r') as file:
        data = yaml.load(file)

    mass   = options.fitdiag.replace('.root','').split('_')
    mheavy = mass[-3] 
    mlight = mass[-1]

    #masslabel = f"{process}: $(m_{heavy},m_{light})= ({mheavy}, {mlight}) GeV$"
    masslabel  = f"{process}: $({mheavy}, {mlight}) GeV$"
    data['signal']['label'] = masslabel 
    data[process] = data.pop("signal")

    with open("ZA/style_ZA.yml", 'w') as file:
        yaml.dump(data, file)
