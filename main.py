#!/usr/bin/env python

# main file to run verification step
import os
import random
from pathlib import Path

<<<<<<< HEAD
from Verification import encodeMission, parseADV
from Verification.extractJSON import *
from Verification.generate_MDP_pruned import *
=======
import encodeMission
from extractJSON import *
from generate_MDP_pruned import *
import parseADV
>>>>>>> master


def callPRISM(mdp_path, property_path, output_path, prism_path: Path):
    ''' run PRISM in terminal from PRISMpath (/Applications/prism-4.5-osx64/bin)
    save output log in outputPath
    '''
<<<<<<< HEAD
    os.chdir(prism_path)
    prism_exec = prism_path / 'prism'
    command = f'"{prism_exec}" -cuddmaxmem 16g -javamaxmem 4g {mdp_path} {property_path} > {output_path}'
=======
    os.chdir(PRISMpath)
    command = './prism ' + '-cuddmaxmem 4g ' + MDPpath + ' ' + propertyPath + ' > ' + outputPath
>>>>>>> master
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
        # print(resultLine)
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

<<<<<<< HEAD

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
=======
def checkTime(team,teamTimeID, m_list, pathToDict, s_prefix, m_prefix):
    '''
    which measurements are free during what time intervals given a team
    output dictionary of {m: time intervals}
    '''
    # from extractJSON

    # reconstruct teamTime ID so that it's only {sensor: [time interval]}
    newTimeDict = {}
    for a in teamTimeID.keys():
        for s in teamTimeID[a]:
            newTimeDict[s] = teamTimeID[a][s]

    check = {}
    for m in m_list:
        check[m] = []

    sDict = create_smDict(team, pathToDict, s_prefix, m_prefix) # {s1: [[m1, P1]], s2: [[m2, P2]]], ...}}
    for s in sDict.keys():
        for mp in sDict[s]:
            meas = mp[0]
            a= newTimeDict[s]
            check[meas]= sorted(check[meas] + a, key=lambda x: x[0])
    # print(check)


def main(team):
   
    # data from knowledge graph 
    pathMissionJSON = 'mission.json'
    pathTimeJSON = 'accesses.json'
    pathToDict = '../KG_examples/outputs_KGMLN_1/output.dict'
    ## FOR MOUNT YASUR MISSION
    # pathTimeJSON = 'test_antoni/MountYasur.json'
    # pathToDict = 'test_antoni/output.dict'
    # bin directory of PRISM application
    PRISMpath = '/Applications/prism-4.6/prism/bin'      

    # name of files for PRISM (saved to current directory)
    missionFile = "prop1.txt"             # specification
    mdpFile = "KG_MDP1.txt"                   # MDP
    outputFile = "output1.txt"            # output log
>>>>>>> master

    # res1 = [random.randrange(0, 1000)/1000. for i in range(168)] 
    # res2 =     [random.randrange(0, 1000)/1000. for i in range(168)] 

    # team = {'GOES-17': [{'ABI': {'Cloud type': res1}    }], \
    #     'Metop-A': [{'IASI': {'Land surface temperature': res2}}]}

    constructTeam(team)
<<<<<<< HEAD
    target = findTarget(path_mission_json)
    team_time = findTimeBounds(team, location, path_time_json)
    a_prefix, s_prefix, m_prefix = 'a', 's', 'm'
    team_time_id = generate_teamTimeID(path_to_dict, team_time, a_prefix, s_prefix)
    a_list, s_list, m_list = generateASMlists(team, path_to_dict, a_prefix, s_prefix, m_prefix)
    num_a, num_s, num_m = len(a_list), len(s_list), len(m_list)
    num_s = len(s_list)
=======
    target = findTarget(pathMissionJSON)
    teamTime = findTimeBounds(team, target, pathTimeJSON)
    
    prefixList = ['a', 's', 'm']
    a_prefix, s_prefix, m_prefix = prefixList
    teamTimeID = generate_teamTimeID(pathToDict, teamTime, a_prefix, s_prefix)
    
    a_list, s_list, m_list = generateASMlists(team, pathToDict, a_prefix, s_prefix, m_prefix)
    numASM = [len(a_list), len(s_list), len(m_list)]
    num_a, num_s, num_m = numASM

    rewardList = ['numAgents']
    print('# of agents, sensors, meas: ',numASM)

    checkTime(team, teamTimeID, m_list, pathToDict, s_prefix, m_prefix)
>>>>>>> master

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
    allStates = allStates_as(num_a, num_s, relation_as, a_list, s_list, teamTimeID)
    num_states = len(allStates)    # total number of states

    allStates_dict = allStates_asm(numASM, relation_as,relation_ms_no, allStates, probDict)
    actions, timeDict = action2str(num_a, num_s, teamTime, allStates, a_prefix, s_prefix, a_list, s_list, pathToDict)

    KG_module = constructKGModule(actions, timeDict, allStates_dict, numASM, prefixList, a_list, s_list, teamTime, relation_as, relation_ms,probDict,pathToDict,missionLength)

    rewardsName = rewardList[0]    # criteria we care about
    rewards_module1 = constructNumAgentsCost(num_a, num_s, teamTime, allStates, a_prefix, s_prefix, a_list, s_list, m_list, pathToDict, rewardsName)
    # rewards_module2 = constructEachPModule(num_a, num_s, num_m,a_list, s_list,teamTime, teamTimeID, relation_as, relation_ms_no,a_prefix, s_prefix, m_prefix, probDict, pathToDict)
    KG_module, rewards_module1 = replaceIdx(a_list, s_list, m_list, KG_module, rewards_module1)

    modules = [KG_module, rewards_module1]
    saveMDPfile(modules, mdpFile)

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


if __name__== "__main__":
    team1 =  {'GOES-17': [{'ABI': {'Cloud type': [0.84130652]} }], \
            'GOES-16': [{'ABI': {'Fire temperature': [0.99999966], 'Cloud type': [0.84130652]} }], \
            'CARTOSAT-2B': [{'PAN (Cartosat-2A/2B)': {'Land surface topography': [0.95]} }], \
            'ZY-3-01': [{'CCD (ZY-1-02C and ZY-3)': {'Land surface topography': [1.]} }], \
            'Jason-3': [{'POSEIDON-3B Altimeter': {'Land surface topography': [1.]} }], \
            'Sentinel-3 B': [{'SLSTR': {'Land surface temperature': [0.99899652]}}], \
            'NOAA-19': [{'AMSU-A': {'Land surface temperature': [0.99899652]}}], \
            'Terra':[{'ASTER': {'Land surface topography': [1.], 'Land surface temperature': [0.99899652], 'Cloud type': [0.84130652]}}, {'MODIS': {'Land surface temperature': [0.99899652], 'Fire temperature': [0.99999966]}}], \
            # 'CARTOSAT-2A': [{'PAN (Cartosat-2A/2B)': {'Land surface topography': [0.95]}    }], \
            # 'CARTOSAT-2': [{'PAN (Cartosat-2)': {'Land surface topography': [0.5]}    }], \
            # 'Metop-A': [{'MHS': {'Cloud type': [0.95]}}, {'IASI': {'Land surface temperature': [0.95]}}], \
            }

    team2 = {
        'GOES-17': [{'ABI': {'Cloud type': [0.84130652]} }],
        'GOES-16': [{'ABI': {'Fire temperature': [0.99999966], 'Cloud type': [0.84130652]} }],
        'Landsat 8':[{'TIRS': {'Land surface topography': [1.], 'Land surface temperature': [0.99899652]} }],
        'KOMPSAT-3A':[{'AEISS-A': {'Land surface topography': [1.]} }],
        'Jason-3': [{'POSEIDON-3B Altimeter': {'Land surface topography': [1.]} }],
        'Kanopus-V-IR': [{'MSU-IK-SR': {'Land surface temperature': [0.99899652]} }],
    }

    # # # ---- benchmark team ----

    team_bench = {'Aqua':[{'AIRS': {'Land surface temperature': [0.99899652]}}, {'MODIS': {'Land surface temperature': [0.99899652], 'Fire temperature': [0.99999966]}}, {'AMSU-A':{'Land surface temperature': [0.99899652], 'Cloud type': [0.84130652]}} ], \
    'Terra':[{'ASTER': {'Land surface topography': [1.], 'Land surface temperature': [0.99899652], 'Cloud type': [0.99899652]}}, {'MODIS': {'Land surface temperature': [0.99899652], 'Fire temperature': [0.99999966]}}], \
    'Sentinel-1 A': [{'C-Band SAR': {'Land surface topography': [0.99899652]}}], \
    'Sentinel-1 B': [{'C-Band SAR': {'Land surface topography': [0.99899652]}}], \
    # 'Sentinel-5 precursor': [{'UVNS (Sentinel-5 precursor)__1': {'Atmospheric Chemistry - SO2 (column/profile)': [0.91160418]}}]
    }
    # ------------------------

    teama = { \
        'GOES-17': [{'ABI': {'Cloud type': [0.84130652]} }],\
        'GOES-16': [{'ABI': {'Fire temperature': [0.99999966], 'Cloud type': [0.84130652]} }],\
        'Landsat 8':[{'TIRS': {'Land surface topography': [1.], 'Land surface temperature': [0.99899652]} }],\
        'KOMPSAT-3A':[{'AEISS-A': {'Land surface topography': [1.]} }],\
        'Jason-3': [{'POSEIDON-3B Altimeter': {'Land surface topography': [1.]} }],\
        'Kanopus-V-IR': [{'MSU-IK-SR': {'Land surface temperature': [0.99899652]} }],\
        }
    newteam = {'DMSP F-16': [{'OLS': {'Cloud type': [0.8847111997185332]}}], 'Pleiades 1B': [{'HiRI': {'Land surface topography': [1.0]}}], 'COSMO-SkyMed 4': [{'SAR 2000': {'Land surface topography': [1.0]}}], 'KOMPSAT-3A': [{'AEISS-A': {'Land surface topography': [0.6852636304815738]}}], 'NOAA-18': [{'AMSU-A': {'Land surface temperature': [0.630040185701942], 'Cloud type': [1.0]}}, {'AVHRR/3': {'Land surface temperature': [1.0]}}, {'HIRS/4': {'Land surface temperature': [0.9750801108493535]}}, {'MHS': {'Cloud type': [1.0]}}], 'Metop-A': [{'AMSU-A': {'Land surface temperature': [1.0], 'Cloud type': [1.0]}}, {'AVHRR/3': {'Land surface temperature': [0.8881435443393207]}}, {'HIRS/4': {'Land surface temperature': [1.0]}}, {'MHS': {'Cloud type': [0.850511996278507]}}, {'IASI': {'Land surface temperature': [0.7791364271353445]}}], 'Sentinel-1 A': [{'C-Band SAR': {'Land surface topography': [0.9458354523040686]}}], 'CloudSat': [{'CPR (CloudSat)': {'Cloud type': [0.9476501928289525]}}], 'CSG-1': [{'CSG SAR': {'Land surface topography': [1.0]}}], 'GOES-17': [{'ABI': {'Fire temperature': [0.6532319622825102], 'Cloud type': [1.0], 'Land surface temperature': [1.0]}}]}    
    team_bench.update(team2)
    t_tot = time.time()
    main(team_bench)
    elapsed = time.time() - t_tot
    print('total time elapsed: ', elapsed)
