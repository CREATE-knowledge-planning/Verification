#!/usr/bin/env python

# main file to run verification step
import os
import random
from pathlib import Path

from Verification import encodeMission, parseADV
from Verification.extractJSON import *
from Verification.generate_MDP_pruned import *


def callPRISM(mdp_path, property_path, output_path, prism_path: Path):
    ''' run PRISM in terminal from PRISMpath (/Applications/prism-4.5-osx64/bin)
    save output log in outputPath
    '''
    os.chdir(prism_path)
    prism_exec = prism_path / 'prism'
    command = f'"{prism_exec}" -cuddmaxmem 16g -javamaxmem 4g {mdp_path} {property_path} > {output_path}'
    print(command)
    os.system(command)


def outputADV(MDPpath, propertyPath, prism_path: Path, int_path):
    # save adversary files
    os.chdir(prism_path)
    prism_exec = prism_path / 'prism'
    adv_file = os.path.join(int_path, 'adv.tra')
    prod_file = os.path.join(int_path, 'prod.sta')
    command = f'"{prism_exec}" {MDPpath} {propertyPath} -exportadvmdp {adv_file} -exportprodstates {prod_file}'
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


def main(team, location):
    # data from knowledge graph
    int_path = os.path.join(os.getcwd(), "int_files")
    path_time_json = os.path.join(int_path, 'accesses', location + '.json')
    path_mission_json = os.path.join(int_path, 'mission.json')
    path_to_dict = os.path.join(int_path, 'output.dict')
    # bin directory of PRISM application
    prism_path = Path('/mnt/d/Dropbox/darpa_grant/prism/prism/bin')

    # name of files for PRISM (saved to current directory)
    mission_file = os.path.join(int_path, "prop.txt")             # specification
    mdp_file = os.path.join(int_path, "KG_MDP.txt")                   # MDP
    output_file = os.path.join(int_path, "output.txt")            # output log

    # res1 = [random.randrange(0, 1000)/1000. for i in range(168)] 
    # res2 =     [random.randrange(0, 1000)/1000. for i in range(168)] 

    # team = {'GOES-17': [{'ABI': {'Cloud type': res1}    }], \
    #     'Metop-A': [{'IASI': {'Land surface temperature': res2}}]}

    constructTeam(team)
    target = findTarget(path_mission_json)
    team_time = findTimeBounds(team, location, path_time_json)
    a_prefix, s_prefix, m_prefix = 'a', 's', 'm'
    team_time_id = generate_teamTimeID(path_to_dict, team_time, a_prefix, s_prefix)
    a_list, s_list, m_list = generateASMlists(team, path_to_dict, a_prefix, s_prefix, m_prefix)
    num_a, num_s, num_m = len(a_list), len(s_list), len(m_list)
    num_s = len(s_list)

    # mission for PRISM
    rewardList = ['numAgents']
    missionLength = encodeMission.findMissionLength(path_mission_json)
    # missionPCTL = encodeMission.generateMissionPCTL(path_mission_json, m_list, mission_file, saveFile = True)
    missionPCTL = encodeMission.generateMissionMulti(m_list, mission_file, rewardList, saveFile = True)
    
    # relationship matrices
    relation_as = construct_asMatrix(team, path_to_dict, num_a, num_s, a_prefix, s_prefix, a_list, s_list)
    relation_ms = construct_msMatrix(team, path_to_dict, num_m, num_s, m_prefix, s_prefix, m_list, s_list)
    
    relation_ms_no, probDict = notMeasMat(team, path_to_dict, relation_ms, num_m, num_s,  m_prefix, s_prefix, m_list, s_list)

    # modules for PRISM MDP
    KG_module = constructKGModule(num_a, num_s, num_m, a_prefix, s_prefix,m_prefix,a_list, s_list,team_time, team_time_id, relation_as, relation_ms,relation_ms_no, probDict,path_to_dict,missionLength)

    rewardsName = 'numAgents'   # criteria we care about
    rewards_module = constructNumAgentsCost(num_a, num_s, team_time, team_time_id, relation_as, a_prefix, s_prefix, a_list, s_list, m_list, path_to_dict, rewardsName)
    KG_module, rewards_module = replaceIdx(a_list, s_list, m_list, KG_module, rewards_module)

    modules = [KG_module, rewards_module]
    saveMDPfile(modules, mdp_file)

    # save PRISM files to current directory
    current_dir = str(os.getcwd())
    callPRISM(mdp_file, mission_file, output_file, prism_path)
    # change directory back
    os.chdir(current_dir)
    result = outputResult(output_file)
    
    outputADV(mdp_file, mission_file, prism_path, int_path)
    # change directory back
    os.chdir(current_dir)

    print('\n ===================== PARETO FRONT POINTS ===================== ')
    print(result)
    print('\n ===================== POSSIBLE TEAMS ===================== ')
    return parseADV.parseADVmain(path_to_dict, int_path)


if __name__ == "__main__":
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

    team2 = {
        'GOES-17': [{'ABI': {'Cloud type': [0.84130652]} }],
        'GOES-16': [{'ABI': {'Fire temperature': [0.99999966], 'Cloud type': [0.84130652]} }],
        'Landsat 8':[{'TIRS': {'Land surface topography': [1.], 'Land surface temperature': [0.99899652]} }],
        'KOMPSAT-3A':[{'AEISS-A': {'Land surface topography': [1.]} }],
        'Jason-3': [{'POSEIDON-3B Altimeter': {'Land surface topography': [1.]} }],
        'Kanopus-V-IR': [{'MSU-IK-SR': {'Land surface temperature': [0.99899652]} }],
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

