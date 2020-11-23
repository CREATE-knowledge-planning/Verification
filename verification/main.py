#!/usr/bin/env python

# main file to run verification step
import os
import ast
import random
from pathlib import Path
import shutil
import subprocess
import multiprocessing as mp
import copy # temporary

from verification.encodeMission import find_mission_length, generate_mission_multi
from verification.extractJSON import *
from verification.generate_MDP_pruned import *
from verification.parseADV import pareto_plot_all, parse_adv_main


def call_prism(mdp_path: Path, mission_str, output_path: Path, prism_path: Path, timestep_path: Path, wsl=False):
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
        timestep_wsl_path = subprocess.run(['wsl', 'wslpath', timestep_path.as_posix()], capture_output=True, encoding='utf-8').stdout[:-1]
        arguments = ['wsl', prism_wsl_path, '-cuddmaxmem', '4g', '-javamaxmem', '4g', str(mdp_wsl_path), '-pctl', f"{mission_str}", '-exportadvmdp', timestep_wsl_path + "/adv.tra", '-exportprodstates', timestep_wsl_path + "/prod.sta"]
    else:
        arguments = [str(prism_bin), '-cuddmaxmem', '4g', '-javamaxmem', '4g', str(mdp_path), '-pctl', f"{mission_str}", '-exportadvmdp', str(timestep_path / "adv.tra"), '-exportprodstates', str(timestep_path / "prod.sta")]
    popen = subprocess.run(arguments, text=True, encoding='utf-8', capture_output=True)
    #print(popen.stdout)
    with output_path.open("w", encoding="utf-8") as output_file:
        output_file.write(popen.stdout)
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
    result_line = result_line.split(':')[1]
    result_line = result_line.split(']')[0][2:]
    result_line = ast.literal_eval("[" + result_line + "]")

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
    return check
    # print(check)


# create function that finds possible team for given timestep
def team_per_timestep(team, team_time, t):
    '''
    Inputs
    team        original team [{'name': 'agent1', 'sensors': [{sensor1: {obs1: P1}, {sensor2: {obs2: P2}}}], agent2: [{sensor3: {obs3: P3} }] }]
    teamTime    dictionary of agents, sensors, and visiblity windows
    t           specified timestep

    Outputs
    teamAtTimestep     possible team at t, same format as team
    '''
    team_at_timestep = []
    for a_idx, agent in enumerate(team_time):
        team_at_timestep.append({"name": agent["name"], "sensors": []})
        for s_idx, sensor in enumerate(agent["sensors"]):
            for interval in sensor["times"]:
                if t in range(interval[0], interval[1]):
                    team_at_timestep[-1]["sensors"].append(team[a_idx]["sensors"][s_idx])
        if team_at_timestep[-1]["sensors"] == []:   # if agent is not visible at t
            del team_at_timestep[-1]
    return team_at_timestep


def main_parallelized(entity_dict, inv_entity_dict, mission_file, mdp_filename, output_filename, simulation_path, prism_path, team, m_list, prefix_list, t, prism_wsl):
    team_time = copy.deepcopy(team)
    for a_idx, agent_info in enumerate(team_time):
        for s_idx, _ in enumerate(agent_info["sensors"]):
            team_time[a_idx]["sensors"][s_idx]["times"] = [[t, t+1]]

    a_prefix, s_prefix, m_prefix = prefix_list
    teamTimeID = generate_team_time_id(entity_dict, team_time, a_prefix, s_prefix)
    
    a_list, s_list = generate_as_lists(team, entity_dict, a_prefix, s_prefix)
    numASM = [len(a_list), len(s_list), len(m_list)]
    num_a, num_s, num_m = numASM

    rewardList = ['numAgents']
    # print('# of agents, sensors, meas: ',numASM)

    check_time(team, teamTimeID, m_list, entity_dict, s_prefix, m_prefix)

    # mission for PRISM
    missionLength = t+1
    # mission_file = encodeMission.generatemission_file(path_mission_json, m_list, missionFile, saveFile = True)
    mission_str = generate_mission_multi(m_list, mission_file, rewardList)
    
    # relationship matrices
    relation_as = construct_as_matrix(team, entity_dict, num_a, num_s, a_prefix, s_prefix, a_list, s_list)
    relation_ms = construct_ms_matrix(team, entity_dict, num_m, num_s, m_prefix, s_prefix, m_list, s_list)
    
    relation_ms_no, probDict = not_meas_mat(team, entity_dict, relation_ms, num_m, num_s,  m_prefix, s_prefix, m_list, s_list)

    # modules for PRISM MDP
    allStates = all_states_as(num_a, num_s, relation_as, a_list, s_list, teamTimeID)
    allStates, allStates_dict = all_states_asm(numASM, relation_as, relation_ms_no, allStates, probDict)
    
    actions, timeDict = action2str(num_a, num_s, team_time, allStates, a_prefix, s_prefix, a_list, s_list, inv_entity_dict)

    kg_module = construct_kg_module(actions, timeDict, allStates_dict, numASM, prefix_list, a_list, s_list, team_time, relation_as, relation_ms, probDict, entity_dict, missionLength, t)

    rewardsName = rewardList[0]    # criteria we care about
    rewards_module1 = construct_num_agents_cost(num_a, num_s, team_time, allStates, a_prefix, s_prefix, a_list, s_list, m_list, inv_entity_dict, rewardsName)
    # rewards_module2 = constructEachPModule(num_a, num_s, num_m,a_list, s_list,teamTime, teamTimeID, relation_as, relation_ms_no,a_prefix, s_prefix, m_prefix, probDict, pathToDict)
    kg_module, rewards_module1 = replace_idx(a_list, s_list, m_list, kg_module, rewards_module1)

    # save adv files to Verification folder
    current_dir = simulation_path
    timestep_path = current_dir / f't{t}'
    timestep_path.mkdir(exist_ok=True)

    # save PRISM files to current directory
    mdp_file = timestep_path / mdp_filename
    output_path = timestep_path / output_filename 
    
    modules = [kg_module, rewards_module1]
    save_mdp_file(modules, mdp_file)
  
    call_prism(mdp_file, mission_str, output_path, prism_path, timestep_path, prism_wsl)
 
    # change directory back
    os.chdir(current_dir)
    result = output_result(output_path)
    
    teams = parse_adv_main(inv_entity_dict, timestep_path)
    
    # delete directory
    shutil.rmtree(timestep_path, ignore_errors=True)

    return result, teams, {t: list(teams.keys())}

def main(team, path_mission_json):
    prefixList = ['a', 's', 'm']
    m_list = generate_m_list(team, simulation_file, pathToDict, prefixList[2])

    mission_length = find_mission_length(path_mission_json)

    target = findTarget(path_mission_json)
    construct_team(team)
    teamTime1 = find_time_bounds(team, target, path_time_json)

    def parallelize(i, q):
        teamUpd = team_per_timestep(team, teamTime1, i)
        q.put(main_parallelized(target, teamUpd, m_list, prefixList, i))

    qout = mp.Queue()
    processes = [mp.Process(target=parallelize, args=(i, qout)) for i in range(mission_length)]
    for p in processes:
        p.start()

    for p in processes:
        p.join()

    result = []
    teaming = []
    times = []
    for p in processes:
        result_p, teaming_p, time_dict = qout.get()
        result.append(result_p)
        teaming.append(teaming_p)
        times.append(time_dict)


    # merge all teaming dictionaries into one
    teams = {k: v for d in teaming for k, v in d.items()}
    timestep_dict = {k: v for d in times for k, v in d.items()}

    optimal_teaming = pareto_plot_all(result, teams, timestep_dict)
    print('\n ===================== OPTIMAL TEAM ===================== ')
    print(optimal_teaming)
    print(result)


    return optimal_teaming


if __name__== "__main__":
    # data from knowledge graph 
    path_mission_json = 'mission.json'
    path_time_json = 'accesses.json'
    # path_time_json = 'Stromboli.json'
    pathToDict = '../KG_examples/outputs_KGMLN_1/output.dict'
    simulation_file = '../KG_examples/outputs_KGMLN_1/simulation_information.json'
    prism_path = '/Applications/prism-4.6/prism/bin' 

    # name of files for PRISM (saved to current directory)
    missionFile = "prop1.txt"             # specification
    mdpFile = "KG_MDP1.txt"                   # MDP
    outputFile = "output1.txt"            # output log

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

    team_bench = {'Aqua':[{'AIRS': {'Land surface temperature': [0.99899652]}}, \
    {'MODIS': {'Land surface temperature': [0.99899652], 'Fire temperature': [0.99999966]}}, \
    {'AMSU-A':{'Land surface temperature': [0.99899652], 'Cloud type': [0.84130652]}} ], \
    'Terra':[{'ASTER': {'Land surface topography': [1.], 'Land surface temperature': [0.99899652], 'Cloud type': [0.99899652]}}, \
    {'MODIS': {'Land surface temperature': [0.99899652], 'Fire temperature': [0.99999966]}}], \
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
    # team_bench.update(team2)

    team_test = {"DMSP F-16":{"OLS__1":{"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137}}},"KOMPSAT-5":{"COSI__1":{"Land surface topography":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847}}},"GCOM-C":{"SGLI__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017},"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137}}},"Suomi NPP":{"ATMS__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}},"VIIRS__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017},"Fire temperature":{"p_tp":0.9419513894749454,"p_fp":0.058047396826726216,"p_tn":0.05804861052505461,"p_fn":0.9419526031732738},"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137}}},"MEGHA-TROPIQUES":{"MADRAS__1":{"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137}},"ScaRaB__1":{"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137}}},"FY-3B":{"IRAS__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}},"MWRI__1":{"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137},"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}},"MWTS-1__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}},"VIRR__1":{"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137},"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}}},"INSAT-3DR":{"Imager (INSAT 3D)__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}}},"Metop-C":{"AMSU-A__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017},"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137}},"AVHRR/3__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}},"IASI__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}},"MHS__1":{"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137}}}}

    team_test2 = {"CloudSat": {"CPR (CloudSat)__1": {"Cloud type": {"p_tp": 0.9719224509828137, "p_fp": 0.028077549017186287, "p_tn": 0.028077549017186287, "p_fn": 0.9719224509828137}}}, "Suomi NPP": {"ATMS__1": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}}, "VIIRS__1": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}, "Fire temperature": {"p_tp": 0.9419513894749454, "p_fp": 0.058047396826726216, "p_tn": 0.05804861052505461, "p_fn": 0.9419526031732738}, "Cloud type": {"p_tp": 0.9719224509828137, "p_fp": 0.028077549017186287, "p_tn": 0.028077549017186287, "p_fn": 0.9719224509828137}}}, "GOES-17": {"ABI__1": {"Cloud type": {"p_tp": 0.9719224509828137, "p_fp": 0.028077549017186287, "p_tn": 0.028077549017186287, "p_fn": 0.9719224509828137}, "Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}, "Fire temperature": {"p_tp": 0.9419513894749454, "p_fp": 0.058047396826726216, "p_tn": 0.05804861052505461, "p_fn": 0.9419526031732738}}}, "NOAA-19": {"AMSU-A__1": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}, "Cloud type": {"p_tp": 0.9719224509828137, "p_fp": 0.028077549017186287, "p_tn": 0.028077549017186287, "p_fn": 0.9719224509828137}}, "AVHRR/3__1": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}}, "HIRS/4__1": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}}, "MHS__1": {"Cloud type": {"p_tp": 0.9719224509828137, "p_fp": 0.028077549017186287, "p_tn": 0.028077549017186287, "p_fn": 0.9719224509828137}}}, "JPSS-1": {"ATMS__2": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}}, "VIIRS__2": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}, "Fire temperature": {"p_tp": 0.9419513894749454, "p_fp": 0.058047396826726216, "p_tn": 0.05804861052505461, "p_fn": 0.9419526031732738}, "Cloud type": {"p_tp": 0.9719224509828137, "p_fp": 0.028077549017186287, "p_tn": 0.028077549017186287, "p_fn": 0.9719224509828137}}}, "Resurs-PN1": {"Geoton-L1 (2)__1": {"Land surface topography": {"p_tp": 0.8357643166606845, "p_fp": 0.16423568333931526, "p_tn": 0.16423568333931549, "p_fn": 0.8357643166606847}}}, "Metop-A": {"AMSU-A__2": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}, "Cloud type": {"p_tp": 0.9719224509828137, "p_fp": 0.028077549017186287, "p_tn": 0.028077549017186287, "p_fn": 0.9719224509828137}}, "AVHRR/3__2": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}}, "HIRS/4__2": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}}, "IASI__1": {"Land surface temperature": {"p_tp": 0.8993548852327783, "p_fp": 0.08354129530159826, "p_tn": 0.10064511476722171, "p_fn": 0.9164587046984017}}, "MHS__2": {"Cloud type": {"p_tp": 0.9719224509828137, "p_fp": 0.028077549017186287, "p_tn": 0.028077549017186287, "p_fn": 0.9719224509828137}}}}
    
    team_bench.update(team2)
    # team = team_bench

    team_paper = {"Sentinel-1 A":{"C-Band SAR__1":{"Land surface topography":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847}}},"Sentinel-1 B":{"C-Band SAR__2":{"Land surface topography":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847}}},"GOES-13":{"GOES Comms__1":{"Cloud type":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847},"Fire temperature":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847},"Land surface temperature":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847}}},"GOES-14":{"GOES Comms__2":{"Cloud type":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847},"Fire temperature":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847},"Land surface temperature":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847}}},"GOES-15":{"GOES Comms__3":{"Cloud type":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847},"Fire temperature":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847},"Land surface temperature":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847}}},"Aqua":{"AIRS__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}},"AMSU-A__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017},"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137}},"MODIS__1":{"Fire temperature":{"p_tp":0.9419513894749454,"p_fp":0.058047396826726216,"p_tn":0.05804861052505461,"p_fn":0.9419526031732738},"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}}},"Terra":{"ASTER__1":{"Land surface topography":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847},"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137},"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}},"MODIS__2":{"Fire temperature":{"p_tp":0.9419513894749454,"p_fp":0.058047396826726216,"p_tn":0.05804861052505461,"p_fn":0.9419526031732738},"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}}}}
    # team = team_paper
    def convert_team(team):
        ''' ***** TEMPORARY FOR TESTING.*****
        '''
        new_team = copy.deepcopy(team)
        for a in list(team.keys()):
            new_team[a] = []
            new_dict1 = {}
            for s in list(team[a].keys()):
                new_dict = {}
                for m in list(team[a][s].keys()):
                    # print(team[a][s][m])
                    new_dict[m] = [team[a][s][m]["p_tp"]]
                
                new_dict1[s] = new_dict
                new_team[a].append(new_dict1)
                # print(new_dict)

        return new_team

    team_fail ={'Metop-B': {'AMSU-A__1': {'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}, 'Cloud type': {'p_tp': 0.9719224509828137, 'p_fp': 0.028077549017186287, 'p_tn': 0.028077549017186287, 'p_fn': 0.9719224509828137}}, 'AVHRR/3__1': {'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}}, 'HIRS/4__1': {'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}}, 'IASI__1': {'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}}, 'MHS__1': {'Cloud type': {'p_tp': 0.9719224509828137, 'p_fp': 0.028077549017186287, 'p_tn': 0.028077549017186287, 'p_fn': 0.9719224509828137}}}, 'CloudSat': {'CPR (CloudSat)__1': {'Cloud type': {'p_tp': 0.9719224509828137, 'p_fp': 0.028077549017186287, 'p_tn': 0.028077549017186287, 'p_fn': 0.9719224509828137}}}, 'KOMPSAT-3A': {'AEISS-A__1': {'Land surface topography': {'p_tp': 0.8357643166606845, 'p_fp': 0.16423568333931526, 'p_tn': 0.16423568333931549, 'p_fn': 0.8357643166606847}}}, 'GCOM-C': {'SGLI__1': {'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}, 'Cloud type': {'p_tp': 0.9719224509828137, 'p_fp': 0.028077549017186287, 'p_tn': 0.028077549017186287, 'p_fn': 0.9719224509828137}}}, 'Resurs-P N3': {'Geoton-L1 (2)__1': {'Land surface topography': {'p_tp': 0.8357643166606845, 'p_fp': 0.16423568333931526, 'p_tn': 0.16423568333931549, 'p_fn': 0.8357643166606847}}}, 'Meteosat-11': {'SEVIRI__1': {'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}, 'Cloud type': {'p_tp': 0.9719224509828137, 'p_fp': 0.028077549017186287, 'p_tn': 0.028077549017186287, 'p_fn': 0.9719224509828137}}}, 'GF-3': {'C-SAR__1': {'Land surface topography': {'p_tp': 0.8357643166606845, 'p_fp': 0.16423568333931526, 'p_tn': 0.16423568333931549, 'p_fn': 0.8357643166606847}}}}
    team_paper2 = {'Sentinel-1 A': {'C-Band SAR__1': {'Land surface topography': {'p_tp': 0.8357643166606845, 'p_fp': 0.16423568333931526, 'p_tn': 0.16423568333931549, 'p_fn': 0.8357643166606847}}}, 'Sentinel-1 B': {'C-Band SAR__2': {'Land surface topography': {'p_tp': 0.8357643166606845, 'p_fp': 0.16423568333931526, 'p_tn': 0.16423568333931549, 'p_fn': 0.8357643166606847}}}, 'GOES-13': {'Imager__1': {'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}, 'Fire temperature': {'p_tp': 0.9419513894749454, 'p_fp': 0.058047396826726216, 'p_tn': 0.05804861052505461, 'p_fn': 0.9419526031732738}}, 'Sounder__1': {'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}}}, 'Aqua': {'AIRS__1': {'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}}, 'AMSU-A__1': {'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}, 'Cloud type': {'p_tp': 0.9719224509828137, 'p_fp': 0.028077549017186287, 'p_tn': 0.028077549017186287, 'p_fn': 0.9719224509828137}}, 'MODIS__1': {'Fire temperature': {'p_tp': 0.9419513894749454, 'p_fp': 0.058047396826726216, 'p_tn': 0.05804861052505461, 'p_fn': 0.9419526031732738}, 'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}}}, 'Terra': {'ASTER__1': {'Land surface topography': {'p_tp': 0.8357643166606845, 'p_fp': 0.16423568333931526, 'p_tn': 0.16423568333931549, 'p_fn': 0.8357643166606847}, 'Cloud type': {'p_tp': 0.9719224509828137, 'p_fp': 0.028077549017186287, 'p_tn': 0.028077549017186287, 'p_fn': 0.9719224509828137}, 'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}}, 'MODIS__2': {'Fire temperature': {'p_tp': 0.9419513894749454, 'p_fp': 0.058047396826726216, 'p_tn': 0.05804861052505461, 'p_fn': 0.9419526031732738}, 'Land surface temperature': {'p_tp': 0.8993548852327783, 'p_fp': 0.08354129530159826, 'p_tn': 0.10064511476722171, 'p_fn': 0.9164587046984017}}}}

    team_paper3 = {"Sentinel-1 A":{"C-Band SAR__1":{"Land surface topography":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847}}},"Sentinel-1 B":{"C-Band SAR__2":{"Land surface topography":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847}}},"GOES-13":{"Imager1__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017},"Fire temperature":{"p_tp":0.9419513894749454,"p_fp":0.058047396826726216,"p_tn":0.05804861052505461,"p_fn":0.9419526031732738}},"Sounder__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}}},"Aqua":{"AIRS__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}},"AMSU-A__1":{"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017},"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137}},"MODIS__1":{"Fire temperature":{"p_tp":0.9419513894749454,"p_fp":0.058047396826726216,"p_tn":0.05804861052505461,"p_fn":0.9419526031732738},"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}}},"Terra":{"ASTER__1":{"Land surface topography":{"p_tp":0.8357643166606845,"p_fp":0.16423568333931526,"p_tn":0.16423568333931549,"p_fn":0.8357643166606847},"Cloud type":{"p_tp":0.9719224509828137,"p_fp":0.028077549017186287,"p_tn":0.028077549017186287,"p_fn":0.9719224509828137},"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}},"MODIS__2":{"Fire temperature":{"p_tp":0.9419513894749454,"p_fp":0.058047396826726216,"p_tn":0.05804861052505461,"p_fn":0.9419526031732738},"Land surface temperature":{"p_tp":0.8993548852327783,"p_fp":0.08354129530159826,"p_tn":0.10064511476722171,"p_fn":0.9164587046984017}}}}


    # team = convert_team(team_paper3)
    # team = {"Sentinel-1 A":[{"C-Band SAR":{"Land surface topography":[0.8357643166606845]}}],"Sentinel-1 B":[{"C-Band SAR__2":{"Land surface topography":[0.8357643166606845]}}],"GOES-13":[{"Imager":{"Land surface temperature":[0.8993548852327783],"Fire temperature":[0.9419513894749454]},"Sounder":{"Land surface temperature":[0.8993548852327783]}}],"Aqua":[{"AIRS":{"Land surface temperature":[0.8993548852327783]},"AMSU-A":{"Land surface temperature":[0.8993548852327783],"Cloud type":[0.9719224509828137]},"MODIS":{"Fire temperature":[0.9419513894749454],"Land surface temperature":[0.8993548852327783]}}],"Terra":[{"ASTER":{"Land surface topography":[0.8357643166606845],"Cloud type":[0.9719224509828137],"Land surface temperature":[0.8993548852327783]},"MODIS__2":{"Fire temperature":[0.9419513894749454],"Land surface temperature":[0.8993548852327783]}}]}
    # print(team)
    
    main(team_bench, path_mission_json)
    

    # t=4
    # for t in range(7):
    #     teamUpd = team_per_timestep(team, teamTime1, t)
    #     print('\n ********* \n timestep: ',t)
    #     main(teamUpd, result, t)
    # print('------------------\n')
    # print(result)

    # q = multiprocessing.Queue()
    # num_cores = multiprocessing.cpu_count()
    # inputs = range(7)
    # processed_list = Parallel(n_jobs=num_cores)(delayed(main_test)(i) for i in inputs)


    # t_tot = time.time()
    # elapsed = t_tot - t_init
    # print('total time elapsed: ', elapsed)
