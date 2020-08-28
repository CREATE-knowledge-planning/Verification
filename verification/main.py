#!/usr/bin/env python

# main file to run verification step
import os
import random
from pathlib import Path
import subprocess

import verification.encodeMission
from verification.extractJSON import *
from verification.generate_MDP_pruned import *
import verification.parseADV


def call_prism(mdp_path: Path, property_path: Path, output_path: Path, prism_path: Path, wsl=False):
    ''' run PRISM in terminal from PRISMpath (/Applications/prism-4.5-osx64/bin)
    save output log in outputPath
    '''
    current_path = Path(".").resolve()
    os.chdir(prism_path)
    prism_bin = prism_path / 'prism'
    arguments = []
    if wsl:
        # First, turn all relevant paths into wsl paths
        prism_wsl_path = subprocess.run(['wsl', 'wslpath', prism_bin.as_posix()], capture_output=True, encoding='utf-8').stdout[:-1]
        mdp_wsl_path = subprocess.run(['wsl', 'wslpath', mdp_path.as_posix()], capture_output=True, encoding='utf-8').stdout[:-1]
        property_wsl_path = subprocess.run(['wsl', 'wslpath', property_path.as_posix()], capture_output=True, encoding='utf-8').stdout[:-1]
        output_wsl_path = subprocess.run(['wsl', 'wslpath', output_path.as_posix()], capture_output=True, encoding='utf-8').stdout[:-1]
        arguments = ['wsl', prism_wsl_path, '-cuddmaxmem', '4g', mdp_wsl_path, property_wsl_path, ">", output_wsl_path]
    else:
        arguments = [str(prism_bin), '-cuddmaxmem', '4g', str(mdp_path), str(property_path), '>', str(output_path)]
    popen = subprocess.run(arguments, universal_newlines=True, encoding='utf-8', capture_output=True)
    print(popen.stdout)
    os.chdir(current_path)


def output_adv(mdp_path: Path, property_path: Path, prism_path: Path, simulation_path: Path, wsl=False):
    # save adversary files
    current_path = Path(".").resolve()
    prism_bin = prism_path / 'prism'
    adv_file = simulation_path / 'adv.tra'
    adv_file = adv_file.resolve()
    prod_file = simulation_path / 'prod.sta'
    prod_file = prod_file.resolve()
    os.chdir(prism_path)
    arguments = []

    if wsl:
        # First, turn all relevant paths into wsl paths
        prism_wsl_path = subprocess.run(['wsl', 'wslpath', prism_bin.as_posix()], capture_output=True, encoding='utf-8').stdout[:-1]
        mdp_wsl_path = subprocess.run(['wsl', 'wslpath', mdp_path.as_posix()], capture_output=True, encoding='utf-8').stdout[:-1]
        property_wsl_path = subprocess.run(['wsl', 'wslpath', property_path.as_posix()], capture_output=True, encoding='utf-8').stdout[:-1]
        adv_file_wsl_path = subprocess.run(['wsl', 'wslpath', adv_file.as_posix()], capture_output=True, encoding='utf-8').stdout[:-1]
        prod_file_wsl_path = subprocess.run(['wsl', 'wslpath', prod_file.as_posix()], capture_output=True, encoding='utf-8').stdout[:-1]
        arguments = ['wsl', prism_wsl_path, mdp_wsl_path, property_wsl_path, '-exportadvmdp', adv_file_wsl_path, '-exportprodstates', prod_file_wsl_path]
    else:
        arguments = [str(prism_bin), str(mdp_path), str(property_path), '-exportadvmdp', str(adv_file), '-exportprodstates', str(prod_file)]
    popen = subprocess.run(arguments, universal_newlines=True, encoding='utf-8', capture_output=True)
    print(popen.stdout)
    os.chdir(current_path)


def output_result(output_path):
    with open(output_path) as file:
        result_line = line_with_string2('Result: ', file)
    try:
        result_list = result_line.split(' ')
        # print(resultLine)
    except:
        raise ValueError('Error occurred when running PRISM. See ' + str(output_path) + ' for details.')
        return
    # return float(resultList[1])
    return result_line


def construct_team(team: dict):
    ''' add unique IDs to sensors in a team '__<num>'
    '''
    allsensors = []
    for a in list(team.keys()):
        for i in range(len(team[a])):
            s = list(team[a][i].keys())[0]    # sensor
            num = allsensors.count(s)+1
            team[a][i][s+'__'+str(num)] = team[a][i].pop(s)     # replace sensor with sensor__num
            allsensors.append(s)
        

def construct_team_from_list(satellite_list):
    ''' add unique IDs to sensors in a team '__<num>'
    '''
    allsensors = []
    new_satellite_list = []
    for satellite in satellite_list:
        satellite["sensors"] = [sensor for sensor in satellite["sensors"] if sensor["characteristics"]]
        new_satellite = copy.deepcopy(satellite)
        for idx, sensor in enumerate(satellite["sensors"]):
            sensor_name = sensor["name"]   # sensor
            num = allsensors.count(sensor_name) + 1
            new_satellite["sensors"][idx]["name"] = sensor_name + '__' + str(num)
            allsensors.append(sensor_name)
        new_satellite_list.append(new_satellite)
    return new_satellite_list


def check_time(team, team_time_id, m_list, entity_dict, s_prefix, m_prefix):
    '''
    which measurements are free during what time intervals given a team
    output dictionary of {m: time intervals}
    '''
    # from extractJSON

    # reconstruct teamTime ID so that it's only {sensor: [time interval]}
    new_time_dict = {}
    for agent in team_time_id:
        for sensor in agent["sensors"]:
            new_time_dict[sensor["name"]] = sensor

    check = {}
    for measurement in m_list:
        check[measurement] = []

    sensor_dict = create_sm_dict(team, entity_dict, s_prefix, m_prefix) # {s1: [[m1, P1]], s2: [[m2, P2]]], ...}}
    for sensor_name in sensor_dict.keys():
        for measurement_info in sensor_dict[sensor_name]:
            measurement_name = measurement_info[0]
            sensor = new_time_dict[sensor_name]
            check[measurement_name] = sorted(check[measurement_name] + sensor["times"], key=lambda x: x[0])
    # print(check)


def main(team):
    # data from knowledge graph 
    path_mission_json = 'mission.json'
    path_time_json = 'accesses.json'
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

    # res1 = [random.randrange(0, 1000)/1000. for i in range(168)] 
    # res2 =     [random.randrange(0, 1000)/1000. for i in range(168)] 

    # team = {'GOES-17': [{'ABI': {'Cloud type': res1}    }], \
    #     'Metop-A': [{'IASI': {'Land surface temperature': res2}}]}

    construct_team(team)
    target = findTarget(path_mission_json)
    teamTime = find_time_bounds(team, target, path_time_json)
    
    prefixList = ['a', 's', 'm']
    a_prefix, s_prefix, m_prefix = prefixList
    teamTimeID = generate_team_time_id(pathToDict, teamTime, a_prefix, s_prefix)
    
    a_list, s_list, m_list = generate_asm_lists(team, pathToDict, a_prefix, s_prefix, m_prefix)
    numASM = [len(a_list), len(s_list), len(m_list)]
    num_a, num_s, num_m = numASM

    rewardList = ['numAgents']
    print('# of agents, sensors, meas: ',numASM)

    check_time(team, teamTimeID, m_list, pathToDict, s_prefix, m_prefix)

    # mission for PRISM
    rewardList = ['numAgents']
    missionLength = encodeMission.findMissionLength(path_mission_json)
    # missionPCTL = encodeMission.generateMissionPCTL(path_mission_json, m_list, mission_file, saveFile = True)
    missionPCTL = encodeMission.generateMissionMulti(m_list, mission_file, rewardList, saveFile = True)
    
    # relationship matrices
    relation_as = construct_as_matrix(team, path_to_dict, num_a, num_s, a_prefix, s_prefix, a_list, s_list)
    relation_ms = construct_ms_matrix(team, path_to_dict, num_m, num_s, m_prefix, s_prefix, m_list, s_list)
    
    relation_ms_no, probDict = not_meas_mat(team, path_to_dict, relation_ms, num_m, num_s,  m_prefix, s_prefix, m_list, s_list)

    # modules for PRISM MDP
    allStates = all_states_as(num_a, num_s, relation_as, a_list, s_list, teamTimeID)
    num_states = len(allStates)    # total number of states

    allStates_dict = all_states_asm(numASM, relation_as,relation_ms_no, allStates, probDict)
    actions, timeDict = action2str(num_a, num_s, teamTime, allStates, a_prefix, s_prefix, a_list, s_list, pathToDict)

    KG_module = construct_kg_module(actions, timeDict, allStates_dict, numASM, prefixList, a_list, s_list, teamTime, relation_as, relation_ms,probDict,pathToDict,missionLength)

    rewardsName = rewardList[0]    # criteria we care about
    rewards_module1 = construct_num_agents_cost(num_a, num_s, teamTime, allStates, a_prefix, s_prefix, a_list, s_list, m_list, pathToDict, rewardsName)
    # rewards_module2 = constructEachPModule(num_a, num_s, num_m,a_list, s_list,teamTime, teamTimeID, relation_as, relation_ms_no,a_prefix, s_prefix, m_prefix, probDict, pathToDict)
    KG_module, rewards_module1 = replace_idx(a_list, s_list, m_list, KG_module, rewards_module1)

    modules = [KG_module, rewards_module1]
    save_mdp_file(modules, mdpFile)

    # save PRISM files to current directory
    current_dir = str(os.getcwd())
    call_prism(mdp_file, mission_file, output_file, prism_path)
    # change directory back
    os.chdir(current_dir)
    result = output_result(output_file)
    
    output_adv(mdp_file, mission_file, prism_path, int_path)
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
