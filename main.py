#!/usr/bin/env python

# main file to run verification step
import os
import encodeMission
from extractJSON import *
from generate_MDP_pruned import *
import parseADV
import random

def callPRISM(MDPpath, propertyPath, outputPath, PRISMpath):
    ''' run PRISM in terminal from PRISMpath (/Applications/prism-4.5-osx64/bin)
    save output log in outputPath
    '''
    os.chdir(PRISMpath)
    command = './prism ' + MDPpath + ' ' + propertyPath + ' > ' + outputPath 
    print(command)
    os.system(command)

def outputADV(MDPpath, propertyPath, PRISMpath):
    # save adversary files
    os.chdir(PRISMpath)
    command = './prism ' + MDPpath + ' ' + propertyPath + '  -exportadvmdp adv.tra -exportprodstates prod.sta'
    os.system(command)

def outputResult(outputPath):
    with open(outputPath) as file:
        resultLine = line_with_string2('Result: ', file)
    try:
        resultList = resultLine.split(' ')
        print(resultLine)
    except:
        raise ValueError('Error occurred when running PRISM. See ' + outputPath + ' for details.')
        return
    # return float(resultList[1])
    return resultLine


def constructTeam(team):
    ''' add unique IDs to sensors in a team '__<num>'
    '''
    allsensors = []
    for a in list(team.keys()):
        for i in range(len(team[a])):
            s = list(team[a][i].keys())[0]    # sensor
            num = allsensors.count(s)+1
            team[a][i][s+'__'+str(num)] = team[a][i].pop(s)     # replace sensor with sensor__num
            allsensors.append(s)

def main(team):
    # data from knowledge graph 
    pathTimeJSON = 'accesses.json'
    pathMissionJSON = 'mission.json'
    pathToDict = '../KG_examples/outputs_KGMLN_1/output.dict'
    # bin directory of PRISM application
    PRISMpath = '/Applications/prism-4.5-osx64/bin'      

    # name of files for PRISM (saved to current directory)
    missionFile = "prop.txt"             # specification
    mdpFile = "KG_MDP.txt"                   # MDP
    outputFile = "output.txt"            # output log

    # res1 = [random.randrange(0, 1000)/1000. for i in range(168)] 
    # res2 =     [random.randrange(0, 1000)/1000. for i in range(168)] 

    # team = {'GOES-17': [{'ABI': {'Cloud type': res1}    }], \
    #     'Metop-A': [{'IASI': {'Land surface temperature': res2}}]}

    constructTeam(team)
    target = findTarget(pathMissionJSON)
    teamTime = findTimeBounds(team, target, pathTimeJSON)
    a_prefix, s_prefix, m_prefix = 'a', 's', 'm'
    teamTimeID = generate_teamTimeID(pathToDict, teamTime, a_prefix, s_prefix)
    a_list, s_list, m_list = generateASMlists(team, pathToDict, a_prefix, s_prefix, m_prefix)
    num_a, num_s, num_m = len(a_list), len(s_list), len(m_list)
    num_s = len(s_list)

    # mission for PRISM
    missionLength = encodeMission.findMissionLength(pathMissionJSON)
    # missionPCTL = encodeMission.generateMissionPCTL(pathMissionJSON, m_list, missionFile, saveFile = True)
    missionPCTL = encodeMission.generateMissionMulti(m_list, missionFile, rewardList, saveFile = True)
    
    # relationship matrices
    relation_as = construct_asMatrix(team, pathToDict, num_a, num_s, a_prefix, s_prefix, a_list, s_list)
    relation_ms = construct_msMatrix(team, pathToDict, num_m, num_s, m_prefix, s_prefix, m_list, s_list)
    
    relation_ms_no, probDict = notMeasMat(team, pathToDict, relation_ms, num_m, num_s,  m_prefix, s_prefix, m_list, s_list)

    # modules for PRISM MDP
    KG_module = constructKGModule(num_a, num_s, num_m, a_prefix, s_prefix,m_prefix,a_list, s_list,teamTime, teamTimeID, relation_as, relation_ms,relation_ms_no, probDict,pathToDict,missionLength)

    rewardsName = 'numAgents'   # criteria we care about
    rewards_module = constructNumAgentsCost(num_a, num_s, teamTime, teamTimeID, relation_as, a_prefix, s_prefix, a_list, s_list, m_list, pathToDict, rewardsName)
    KG_module, rewards_module = replaceIdx(a_list, s_list, m_list, KG_module, rewards_module)

    modules = [KG_module, rewards_module]
    saveMDPfile(modules, mdpFile)

    # save PRISM files to current directory
    current_dir = str(os.getcwd())
    MDPpath = current_dir + '/' + mdpFile
    propertyPath = current_dir + '/' + missionFile
    outputPath = current_dir + '/' + outputFile    
    callPRISM(MDPpath, propertyPath, outputPath, PRISMpath)
    # change directory back
    os.chdir(current_dir)
    result = outputResult(outputPath)
    
    outputADV(MDPpath, propertyPath, PRISMpath)
    # change directory back
    os.chdir(current_dir)

    print('\n ===================== PARETO FRONT POINTS ===================== ')
    print(result)
    print('\n ===================== POSSIBLE TEAMS ===================== ')
    parseADV.parseADVmain(pathToDict, PRISMpath)

if __name__== "__main__":

    # team1 =  {'GOES-17': [{'ABI': {'Cloud type': [0.84130652]} }], \
    #         'GOES-16': [{'ABI': {'Fire temperature': [0.99999966], 'Cloud type': [0.84130652]} }], \
    #         'CARTOSAT-2B': [{'PAN (Cartosat-2A/2B)': {'Land surface topography': [0.95]} }], \
    #         'ZY-3-01': [{'CCD (ZY-1-02C and ZY-3)': {'Land surface topography': [1.]} }], \
    #         'Jason-3': [{'POSEIDON-3B Altimeter': {'Land surface topography': [1.]} }], \
    #         'Sentinel-3 B': [{'SLSTR': {'Land surface temperature': [0.99899652]}}], \
    #         'NOAA-19': [{'AMSU-A': {'Land surface temperature': [0.99899652]}}], \
    #         'Terra':[{'ASTER': {'Land surface topography': [1.], 'Land surface temperature': [0.99899652], 'Cloud type': [0.84130652]}}, {'MODIS': {'Land surface temperature': [0.99899652], 'Fire temperature': [0.99999966]}}], \
    #         # 'CARTOSAT-2A': [{'PAN (Cartosat-2A/2B)': {'Land surface topography': [0.95]}    }], \
    #         # 'CARTOSAT-2': [{'PAN (Cartosat-2)': {'Land surface topography': [0.5]}    }], \
    #         # 'Metop-A': [{'MHS': {'Cloud type': [0.95]}}, {'IASI': {'Land surface temperature': [0.95]}}], \
    #         }

    team2 = {'GOES-17': [{'ABI': {'Cloud type': [0.84130652]} }], \
    'GOES-16': [{'ABI': {'Fire temperature': [0.99999966], 'Cloud type': [0.84130652]} }], \
    'Landsat 8':[{'TIRS': {'Land surface topography': [1.]} }], \
    'KOMPSAT-3A':[{'AEISS-A': {'Land surface topography': [1.]} }], \
    'Jason-3': [{'POSEIDON-3B Altimeter': {'Land surface topography': [1.]} }], \
    'Elektro-L N3': [{'DCS': {'Land surface temperature': [0.99899652]} }], \
    }


    # # # ---- benchmark team ----

    # team_bench = {'Aqua':[{'AIRS': {'Land surface temperature': [0.99899652]}}, {'MODIS': {'Land surface temperature': [0.99899652], 'Fire temperature': [0.99999966]}}, {'AMSU-A':{'Land surface temperature': [0.99899652], 'Cloud type': [0.84130652]}} ], \
    #         'Terra':[{'ASTER': {'Land surface topography': [1.], 'Land surface temperature': [0.99899652], 'Cloud type': [0.99899652]}}, {'MODIS': {'Land surface temperature': [0.99899652], 'Fire temperature': [0.99999966]}}], \
    #         'Sentinel-1 A': [{'C-Band SAR': {'Land surface topography': [0.99899652]}}], \
    #         'Sentinel-1 B': [{'C-Band SAR': {'Land surface topography': [0.99899652]}}], \
    #         # 'Sentinel-5 precursor': [{'UVNS (Sentinel-5 precursor)__1': {'Atmospheric Chemistry - SO2 (column/profile)': [0.91160418]}}]
    #         }
    # ------------------------
    main(team2)







