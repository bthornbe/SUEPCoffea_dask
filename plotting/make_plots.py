import pandas as pd 
import numpy as np
from hist import Hist
import argparse
import os
import awkward as ak
import uproot
import getpass
import pickle
import json
from tqdm import tqdm

parser = argparse.ArgumentParser(description='Famous Submitter')
parser.add_argument("-dataset", "--dataset"  , type=str, default="QCD", help="dataset name", required=True)
parser.add_argument("-t"   , "--tag"   , type=str, default="IronMan"  , help="production tag", required=False)
parser.add_argument("-e"   , "--era"   , type=int, default=2018  , help="era", required=False)
parser.add_argument('--doSyst', type=int, default=0, help="make systematic plots")
parser.add_argument('--isMC', type=int, default=1, help="Is this MC or data")
parser.add_argument('--blind', type=int, default=1, help="Blind the data (default=True)")
options = parser.parse_args()

# parameters for ABCD method
var1_label = 'spher'
var2_label = 'nconst'
var1_val = 0.50
var2_val = 25
nbins = 100
labels = ['ch']
output_label = 'V6'

# cross section
xsection = 1.0
with open('../data/xsections_{}.json'.format(options.era)) as file:
    MC_xsecs = json.load(file)
    try:
        xsection *= MC_xsecs[options.dataset]["xsec"]
        xsection *= MC_xsecs[options.dataset]["kr"]
        xsection *= MC_xsecs[options.dataset]["br"]
    except:
        print("WARNING: I did not find the xsection for that MC sample. Check the dataset name and the relevant yaml file")

#Get the list of files
username = getpass.getuser()
dataDir = "/mnt/T3_US_MIT/hadoop/scratch/{}/SUEP/{}/{}/".format(username,options.tag,options.dataset)
files = [file for file in os.listdir(dataDir)]

# output histos
def create_output_file(l):
    output = {
            # variables from the dataframe
            "SUEP_"+label+"_nconst" : Hist.new.Reg(499, 0, 500, name="nconst_"+label, label="# Tracks in SUEP").Weight(),
            "SUEP_"+label+"_ntracks" : Hist.new.Reg(499, 0, 500, name="ntracks_"+label, label="# Tracks in event").Weight(),
            "SUEP_"+label+"_pt" : Hist.new.Reg(100, 0, 2000, name="pt_"+label, label=r"$p_T$").Weight(),
            "SUEP_"+label+"_pt_avg" : Hist.new.Reg(100, 0, 100, name="pt_avg_"+label, label=r"Components $p_T$ Avg.").Weight(),
            "SUEP_"+label+"_pt_avg_b" : Hist.new.Reg(100, 0, 100, name="pt_avg_b_"+label, label=r"Components $p_T$ avg (boosted frame)").Weight(),
            "SUEP_"+label+"_eta" : Hist.new.Reg(100, -5, 5, name="eta_"+label, label=r"$\eta$").Weight(),
            "SUEP_"+label+"_phi" : Hist.new.Reg(100, 0, 6.5, name="phi_"+label, label=r"$\phi$").Weight(),
            "SUEP_"+label+"_mass" : Hist.new.Reg(150, 0, 4000, name="mass_"+label, label="Mass").Weight(),
            "SUEP_"+label+"_spher" : Hist.new.Reg(100, 0, 1, name="spher_"+label, label="Sphericity").Weight(),
            "SUEP_"+label+"_aplan" : Hist.new.Reg(100, 0, 1, name="aplan_"+label, label="Aplanarity").Weight(),
            "SUEP_"+label+"_FW2M" : Hist.new.Reg(100, 0, 1, name="FW2M_"+label, label="2nd Fox Wolfram Moment").Weight(),
            "SUEP_"+label+"_D" : Hist.new.Reg(100, 0, 1, name="D_"+label, label="D").Weight(),
            "SUEP_"+label+"_girth": Hist.new.Reg(50, 0, 1.0, name="girth_"+label, label=r"Girth").Weight(),
            "SUEP_"+label+"_rho0" : Hist.new.Reg(100, 0, 20, name="rho0_"+label, label=r"$\rho_0$").Weight(),
            "SUEP_"+label+"_rho1" : Hist.new.Reg(100, 0, 20, name="rho1_"+label, label=r"$\rho_1$").Weight(),

            # r=1 sphericity tensor variables
            "SUEP_"+label+"_spher_1" : Hist.new.Reg(100, 0, 1, name="spher_1_"+label, label="sphericity_1").Weight(),
            "SUEP_"+label+"_aplan_1" : Hist.new.Reg(100, 0, 1, name="aplan_1_"+label, label="Aplanarity_1").Weight(),
            "SUEP_"+label+"_FW2M_1" : Hist.new.Reg(100, 0, 1, name="FW2M_1_"+label, label="2nd Fox Wolfram Moment_1").Weight(),
            "SUEP_"+label+"_D_1" : Hist.new.Reg(100, 0, 1, name="D_1_"+label, label="D_1").Weight(),
            "SUEP_"+label+"_C_1" : Hist.new.Reg(100, 0, 1, name="C_1_"+label, label="C_1").Weight(),


            # new hists
            "A_"+label: Hist.new.Reg(nbins, 0, 1, name="A_"+label).Weight(),
            "B_"+label: Hist.new.Reg(nbins, 0, 1, name="B_"+label).Weight(),
            "C_"+label: Hist.new.Reg(nbins, 0, 1, name="C_"+label).Weight(),
            "D_exp_"+label: Hist.new.Reg(nbins, 0, 1, name="D_exp_"+label).Weight(),
            "D_obs_"+label: Hist.new.Reg(nbins, 0, 1, name="D_obs_"+label).Weight(),
            "ABCDvars_2D_"+label : Hist.new.Reg(100, 0, 1, name= var1_label +label).Reg(99, 0, 200, name=var2_label).Weight(),
            "2D_girth_nconst_"+label : Hist.new.Reg(50, 0, 1.0, name="girth_"+label).Reg(99, 0, 200, name="nconst_"+label).Weight(),
            "2D_rho0_nconst_"+label : Hist.new.Reg(100, 0, 20, name="rho0_"+label).Reg(99, 0, 200, name="nconst_"+label).Weight(),
            "2D_rho1_nconst_"+label : Hist.new.Reg(100, 0, 20, name="rho1_"+label).Reg(99, 0, 200, name="nconst_"+label).Weight(),
            "2D_spher_ntracks_"+label : Hist.new.Reg(100, 0, 1.0, name="spher_"+label).Reg(200, 0, 500, name="ntracks_"+label).Weight(),
            "2D_spher_nconst_"+label : Hist.new.Reg(100, 0, 1.0, name="spher_"+label).Reg(99, 0, 200, name="nconst_"+label).Weight(),
            "ht_" + label : Hist.new.Reg(1000, 0, 30000, name="ht_"+label, label='HT ' + label).Weight(),
        
            # region specific kinematic variables
            "A_pt_"+label : Hist.new.Reg(100, 0, 2000, name="A pt_"+label, label=r"A $p_T$").Weight(),
            "B_pt_"+label : Hist.new.Reg(100, 0, 2000, name="B pt_"+label, label=r"B $p_T$").Weight(),
            "C_pt_"+label : Hist.new.Reg(100, 0, 2000, name="C pt_"+label, label=r"C $p_T$").Weight(),
            "A_nconst_"+label : Hist.new.Reg(499, 0, 500, name="A nconst_"+label, label="A # Tracks in SUEP").Weight(),
            "B_nconst_"+label : Hist.new.Reg(499, 0, 500, name="B nconst_"+label, label="B # Tracks in SUEP").Weight(),
            "C_nconst_"+label : Hist.new.Reg(499, 0, 500, name="C nconst_"+label, label="C # Tracks in SUEP").Weight(),
            "A_pt_nconst_"+label : Hist.new.Reg(100, 0, 2000, name="A pt_"+label).Reg(499, 0, 500, name="A nconst_"+label).Weight(),
            "B_pt_nconst_"+label : Hist.new.Reg(100, 0, 2000, name="B pt_"+label).Reg(499, 0, 500, name="B nconst_"+label).Weight(),
            "C_pt_nconst_"+label : Hist.new.Reg(100, 0, 2000, name="C pt_"+label).Reg(499, 0, 500, name="C nconst_"+label).Weight(),
            "AB_pt_"+label : Hist.new.Reg(100, 0, 2000, name="AB pt_"+label, label=r"$p_T$").Weight(),
            "AB_eta_"+label : Hist.new.Reg(100, -5, 5, name="AB eta_"+label, label=r"$\eta$").Weight(),
            "AB_phi_"+label : Hist.new.Reg(100, 0, 6.5, name="AB phi_"+label, label=r"$\phi$").Weight(),
            "AC_pt_"+label : Hist.new.Reg(100, 0, 2000, name="AC pt_"+label, label=r"$p_T$").Weight(),
            "AC_eta_"+label : Hist.new.Reg(100, -5, 5, name="AC eta_"+label, label=r"$\eta$").Weight(),
            "AC_phi_"+label : Hist.new.Reg(100, 0, 6.5, name="AC phi_"+label, label=r"$\phi$").Weight(),
    }
    if label == 'ch':# Christos only
        output2 = {
            "SUEP_"+label+"_dphi_chcands_ISR":Hist.new.Reg(100, 0, 4, name="dphi_chcands_ISR").Weight(),
            "SUEP_"+label+"_dphi_SUEPtracks_ISR": Hist.new.Reg(100, 0, 4, name="dphi_SUEPtracks_ISR").Weight(),
            "SUEP_"+label+"_dphi_ISRtracks_ISR":Hist.new.Reg(100, 0, 4, name="dphi_ISRtracks_ISR").Weight(),
            "SUEP_"+label+"_dphi_SUEP_ISR":Hist.new.Reg(100, 0, 4, name="dphi_SUEP_ISR").Weight(),
        }
        output.update(output2)
    if options.isMC and options.doSyst:# Systematic plots
        output3 = {
            #"SUEP_"+label+"_variable_"+sys:Hist.new.Reg(100, 0, 4, name="variable").Weight(),
        }
        output.update(output3)
    return output

# load hdf5 with pandas
def h5load(ifile, label):
    try:
        with pd.HDFStore(ifile) as store:
            try:
                data = store[label] 
                metadata = store.get_storer(label).attrs.metadata
                return data, metadata
            except ValueError: 
                print("Empty file!", ifile)
                return 0, 0
            except KeyError:
                print("No key",label,ifile)
                return 0, 0
    except:
        print("Some error occurred", ifile)
        return 0, 0
        
# fill ABCD hists with dfs from hdf5 files
frames = {"mult":[],"ch":[]}
nfailed = 0
weight = 0
fpickle =  open("outputs/" + options.dataset+ "_" + output_label + '.pkl', "wb")
output = {}
for label in labels: output.update(create_output_file(label))
for ifile in tqdm(files):
    ifile = dataDir+"/"+ifile

    if os.path.exists(options.dataset+'.hdf5'): os.system('rm ' + options.dataset+'.hdf5')
    xrd_file = "root://t3serv017.mit.edu:/" + ifile.split('hadoop')[1]
    os.system("xrdcp {} {}.hdf5".format(xrd_file, options.dataset))

    df_vars, metadata = h5load(options.dataset+'.hdf5', 'vars')    

    # check if file is corrupted, or empty
    if type(df_vars) == int: 
        nfailed += 1
        continue
    if df_vars.shape[0] == 0: continue
    
    if options.isMC: weight += metadata['gensumweight']
    
    # store hts for the all event to be indexed
    hts = df_vars['ht']
    
    for label in labels:
        df, metadata = h5load(options.dataset+'.hdf5', label) 
        # parameters for ABCD plots
        var1 = 'SUEP_'+label+'_' + var1_label
        var2 = 'SUEP_'+label+'_' + var2_label

        sizeA, sizeC = 0,0
                
        # selections
        if var2_label == 'nconst': df = df.loc[df['SUEP_'+label+'_nconst'] >= 10]
        if var1_label == 'spher': df = df.loc[df['SUEP_'+label+'_spher'] >= 0.25]
        #df = df.loc[df['SUEP_'+label+'_pt'] >= 300]
        if options.blind and not options.isMC:
             df = df.loc[((df[var1] < var1_val) & (df[var2] < var2_val)) | ((df[var1] >= var1_val) & (df[var2] < var2_val)) | ((df[var1] < var1_val) & (df[var2] >= var2_val))]
        df = df.loc[df['SUEP_ch_pt'] >= 300]

        # divide the dfs by region
        df_A = df.loc[(df[var1] < var1_val) & (df[var2] < var2_val)]
        df_B = df.loc[(df[var1] >= var1_val) & (df[var2] < var2_val)]
        df_C = df.loc[(df[var1] < var1_val) & (df[var2] >= var2_val)]
        df_D_obs = df.loc[(df[var1] >= var1_val) & (df[var2] >= var2_val)]
        
        sizeC += df_C.shape[0]
        sizeA += df_A.shape[0]

        # fill the ABCD histograms
        output["A_"+label].fill(df_A[var1])
        output["B_"+label].fill(df_B[var1])
        output["D_exp_"+label].fill(df_B[var1])
        output["C_"+label].fill(df_C[var1])
        output["D_obs_"+label].fill(df_D_obs[var1])
        output["ABCDvars_2D_"+label].fill(df[var1], df[var2])  

        # fill the distributions as they are saved in the dataframes
        plot_labels = [key for key in df.keys() if key in list(output.keys())]
        for plot in plot_labels: output[plot].fill(df[plot])  

        # fill some new distributions  
        output["2D_girth_nconst_"+label].fill(df["SUEP_"+label+"_girth"], df["SUEP_"+label+"_nconst"])
        output["2D_rho0_nconst_"+label].fill(df["SUEP_"+label+"_rho0"], df["SUEP_"+label+"_nconst"])
        output["2D_rho1_nconst_"+label].fill(df["SUEP_"+label+"_rho1"], df["SUEP_"+label+"_nconst"])
        output["2D_spher_nconst_"+label].fill(df["SUEP_"+label+"_spher"], df["SUEP_"+label+"_nconst"])
        output["2D_spher_ntracks_"+label].fill(df["SUEP_"+label+"_spher"], df["SUEP_"+label+"_ntracks"])
        output["AB_phi_"+label].fill(df['SUEP_' + label + '_phi'].loc[(df[var2] < var2_val)])
        output["AB_eta_"+label].fill(df['SUEP_' + label + '_eta'].loc[(df[var2] < var2_val)])
        output["AB_pt_"+label].fill(df['SUEP_' + label + '_pt'].loc[(df[var2] < var2_val)])
        output["AC_phi_"+label].fill(df['SUEP_' + label + '_phi'].loc[(df[var1] < var1_val)])
        output["AC_eta_"+label].fill(df['SUEP_' + label + '_eta'].loc[(df[var1] < var1_val)])
        output["AC_pt_"+label].fill(df['SUEP_' + label + '_pt'].loc[(df[var1] < var1_val)])
        output["A_pt_"+label].fill(df_A['SUEP_' + label + '_pt'])
        output["B_pt_"+label].fill(df_B['SUEP_' + label + '_pt'])
        output["C_pt_"+label].fill(df_C['SUEP_' + label + '_pt'])
        output["A_nconst_"+label].fill(df_A['SUEP_' + label + '_nconst'])
        output["B_nconst_"+label].fill(df_B['SUEP_' + label + '_nconst'])
        output["C_nconst_"+label].fill(df_C['SUEP_' + label + '_nconst'])
        output["A_pt_nconst_"+label].fill(df_A['SUEP_' + label + '_pt'], df_A['SUEP_' + label + '_nconst'])
        output["B_pt_nconst_"+label].fill(df_B['SUEP_' + label + '_pt'], df_B['SUEP_' + label + '_nconst'])
        output["C_pt_nconst_"+label].fill(df_C['SUEP_' + label + '_pt'], df_C['SUEP_' + label + '_nconst'])
        output["ht_" + label].fill(hts[df['SUEP_' + label + '_index']])
    os.system('rm ' + options.dataset+'.hdf5')    
        
# ABCD method to obtain D expected
for label in labels:
    if sizeA>0.0:
        CoverA =  sizeC / sizeA
    else:
        CoverA = 0.0
        print("A region has no occupancy")
    output["D_exp_"+label] = output["D_exp_"+label]*(CoverA)
    
# apply normalization
if weight > 0.0 and options.isMC:
    for plot in list(output.keys()): output[plot] = output[plot]*xsection/weight
else:
    print("Weight is 0")
        
#Save to pickle
pickle.dump(output, fpickle)
print("Number of files that failed to be read:", nfailed)

with uproot.recreate("outputs/" + options.dataset+ "_" + output_label + '.root') as froot:
     for h, hist in output.items():
         froot[h] = hist
