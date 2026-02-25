import os
import json
import argparse
import ruamel

from ruamel.yaml import YAML


def WriteChannelOnPlotIt(data, latex_opts, mode):
    plotit_texts = {}
    for ch, cfg in data.items():
        if ch in ['xmin', 'xmax']:
            continue
        if mode =='dnn':
            node = cfg[0].split('_')[2]
            ch_per_bin = cfg[0].split('_')[5:]
        else:
            node = ''
            ch_per_bin = cfg[0].split('_')[4:]
        ch_per_bin[-1] = latex_opts[ch_per_bin[-1]]
        plotit_texts[ch] = [node]+ch_per_bin
    return plotit_texts


def get_cats_to_plot(filediagnostic, mode, process, channels):
    combine_cats_per_year = []
    all_cats = []
    SRonly_cats = []
    
    for ch, cats in channels.items():
        random_cat = cats[0].split('_UL')[0]
        c  = f"fullrun2_{ch}_{process}_{random_cat}:{','.join(cats)}"
        c2 = f"{','.join(cats)}"
        combine_cats_per_year.append(c)
        all_cats.append(c2)
        if 'MuEl' not in c2:
            SRonly_cats.append(c2)
    
    tot_cats  = ';'.join(combine_cats_per_year)
    #tot_cats += f";fullrun2_{'_'.join(channels.keys())}:{','.join(all_cats)}"
    #tot_cats += f";fullrun2_SRonly_cats:{','.join(SRonly_cats)}"
    
    reco = []
    region = []
    flavor = []
    
    texts = WriteChannelOnPlotIt(channels, latex_opts, mode)
    for i, t in enumerate(texts.values()):
        nb, reg, flav, node = t[1],t[2],t[3],t[0]
        if nb not in reco:
            reco.append(nb)
        if reg not in region:
            region.append(reg)
        if flav not in flavor:
            flavor.append(flav)
                
    if '_nb2_' in filediagnostic: nb = 'nb2'
    elif '_nb3_' in filediagnostic: nb = 'nb3'
    elif 'nb2PLusnb3' in filediagnostic: nb  = 'nb2+nb3'

    if 'resolved_boosted' in filediagnostic: reg = 'resolved+boosted'
    elif 'resolved' in filediagnostic: reg = 'resolved'
    elif 'boosted' in filediagnostic : reg = 'boosted'
    
    flav = ''
    for f in ['MuMu', 'ElEl', 'OSSF', 'MuEl']:
        if f == 'MuEl': flav +='+'
        if f in filediagnostic: flav +=latex_opts[f]
    
    catheader = f"{nb} {reg}, {flav}"
    #catheader = f"{'+'.join(reco)} {'+'.join(region)}, {'+'.join(flavor)}"
    #catheader = '' # reset for now
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

    # .e.g. fitDiagnosticsHToZATo2L2B_gg_fusion_nb2_resolved_boosted_OSSF_mbb_MH_442.63_MA_95.27.root
    opts = options.fitdiag.split('/')[-1].split('_')
    prod = '_'.join(opts[1:3])
    nb   = opts[3] 
    process = f'gg{heavy}' if prod == 'gg_fusion' else f'bb{heavy}' 
    basedir = os.path.dirname(options.fitdiag)
    file    = options.fitdiag.replace('.root', '').split('/')[-1]
    catname = file.split(prod)[-1].split(f'_{mode}_')[0] 
    mass    = file.split(mode +'_')[-1]
    mheavy  = mass.split('_')[-3] 
    mlight  = mass.split('_')[-1]
    mass    = mass.replace('.','p')
    
    if os.path.isfile(os.path.join(basedir, 'fit_b', f'channels.json')):
        jsf = os.path.join(basedir, 'fit_b', f'channels.json') 
    elif os.path.isfile(os.path.join(basedir, 'fit_s', f'channels.json')):
        jsf = os.path.join(basedir, 'fit_s', f'channels.json')
    else:
        print(f" file : 'channels.json' was not found in {os.path.join(basedir)}")

    with open(jsf, 'r') as jsfile: # can be found in prefit, fit_s, should be the same
        channels = json.load(jsfile)
        
        del channels['xmin']
        del channels['xmax']
        
        new_channels = {}
        for c, listv in channels.items():
            if not c in new_channels.keys(): new_channels[c] =[]
            new_channels[c] += [f"{mode}_{mass}_{v}" for v in listv]
    
    if not channels:
        ch_per_year = options.fitdiag.replace('.root', '').split('/')[-1].split('OSSF_')[-1]
        new_channels = {'ch1': [f"{ch_per_year}_{era}".replace('.','p') for era in ['UL16', 'UL17', 'UL18']]}
    
    get_cats_to_plot(file, mode, process, new_channels)
    yaml = YAML()
    with open("ZA/style_ZA_template.yml", 'r') as file:
        data = yaml.load(file)

    #masslabel = f"{process}: $(m_{heavy},m_{light})= ({mheavy}, {mlight}) GeV$"
    masslabel  = f"{process}: $({mheavy}, {mlight}) GeV$"
    data['signal']['label'] = masslabel 
    data[process] = data.pop("signal")

    with open("ZA/style_ZA.yml", 'w') as file:
        yaml.dump(data, file)
