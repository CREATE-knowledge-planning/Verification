#!/usr/bin/env python

# main file to run verification step
import os
import ast
import shutil
import encodeMission
import extractJSON
import generate_MDP_pruned as genMDP
import parseADV
import random
import multiprocessing as mp

def call_prism(mdp_file, mission_str, output_path, prism_path, timestep_path):
    ''' run PRISM in terminal from prism_path (/Applications/prism-4.5-osx64/bin)
    save output log in output_path
    '''
    os.chdir(prism_path)
    command = './prism ' + '-cuddmaxmem 4g ' + '-javamaxmem 4g ' + mdp_file + " -pctl '" + mission_str + "' > " + output_path
    command += ' -exportadvmdp ' + timestep_path + '/adv.tra -exportprodstates ' + timestep_path + '/prod.sta'
    print(command)
    os.system(command)

def output_result(output_path):
    with open(output_path) as file:
        result_line = extractJSON.line_with_string2('Result: ', file)
    try:
        result_list = result_line.split(' ')
    except:
        raise ValueError('Error occurred when running PRISM. See ' + output_path + ' for details.')
        return
    result_line = result_line.split(':')[1]
    result_line = result_line.split(']')[0][2:]
    result_line = ast.literal_eval(result_line)

    return result_line

def construct_team(team):
    ''' add unique IDs to sensors in a team '__<num>'
    '''
    allsensors = []
    for a in list(team.keys()):
        for i in range(len(team[a])):
            s = list(team[a][i].keys())[0]    # sensor
            num = allsensors.count(s)+1
            team[a][i][s+'__'+str(num)] = team[a][i].pop(s)     # replace sensor with sensor__num
            allsensors.append(s)

def check_time(team,teamTimeID, m_list, pathToDict, s_prefix, m_prefix):
    '''
    which measurements are free during what time intervals given a team
    output dictionary of {m: time intervals}
    '''

    # reconstruct teamTime ID so that it's only {sensor: [time interval]}
    newTimeDict = {}
    for a in teamTimeID.keys():
        for s in teamTimeID[a]:
            newTimeDict[s] = teamTimeID[a][s]

    check = {}
    for m in m_list:
        check[m] = []

    sDict = extractJSON.create_sm_dict(team, pathToDict, s_prefix, m_prefix) # {s1: [[m1, P1]], s2: [[m2, P2]]], ...}}
    for s in sDict.keys():
        for mp in sDict[s]:
            meas = mp[0]
            a= newTimeDict[s]
            check[meas]= sorted(check[meas] + a, key=lambda x: x[0])
    return check
    # print(check)

# create function that finds possible team for given timestep
def team_per_timestep(team, teamTime, t):
    '''
    Inputs
    team        original team {a: {s: P}}
    teamTime    dictionary of agents, sensors, and visiblity windows
    t           specified timestep

    Outputs
    teamAtTimestep     possible team at t, same format as team
    '''
    teamAtTimestep = {}
    for a in teamTime.keys():
        teamAtTimestep[a] = []
        counter = -1
        for s in teamTime[a]:
            counter += 1
            for interval in teamTime[a][s]:
                if t in range(interval[0], interval[1]):
                    newdict = {}
                    newdict[s] = team[a][counter][s]
                    teamAtTimestep[a].append(newdict)
        if teamAtTimestep[a] == []:   # if agent is not visible at t
            teamAtTimestep.pop(a)
    return teamAtTimestep 

def main_parallelized(target, team,t):

    teamTime = extractJSON.find_time_bounds(team, target, path_time_json)
    for k in teamTime.keys():
        for s in teamTime[k].keys():
            teamTime[k][s] = [[t, t+1]]

    prefixList = ['a', 's', 'm']
    a_prefix, s_prefix, m_prefix = prefixList
    teamTimeID = extractJSON.generate_team_time_id(pathToDict, teamTime, a_prefix, s_prefix)
    
    a_list, s_list, m_list = extractJSON.generate_asm_lists(team, pathToDict, a_prefix, s_prefix, m_prefix)
    numASM = [len(a_list), len(s_list), len(m_list)]
    num_a, num_s, num_m = numASM

    rewardList = ['numAgents']
    # print('# of agents, sensors, meas: ',numASM)

    check_time(team, teamTimeID, m_list, pathToDict, s_prefix, m_prefix)

    # mission for PRISM
    missionLength = t+1
    # mission_file = encodeMission.generatemission_file(path_mission_json, m_list, missionFile, saveFile = True)
    mission_str = encodeMission.generateMissionMulti(m_list, missionFile, rewardList)
    
    # relationship matrices
    relation_as = extractJSON.construct_as_matrix(team, pathToDict, num_a, num_s, a_prefix, s_prefix, a_list, s_list)
    relation_ms = extractJSON.construct_ms_matrix(team, pathToDict, num_m, num_s, m_prefix, s_prefix, m_list, s_list)
    
    relation_ms_no, probDict = extractJSON.not_meas_mat(team, pathToDict, relation_ms, num_m, num_s,  m_prefix, s_prefix, m_list, s_list)

    # modules for PRISM MDP
    allStates = genMDP.all_states_as(num_a, num_s, relation_as, a_list, s_list, teamTimeID)
    allStates, allStates_dict = genMDP.all_states_asm(numASM, relation_as,relation_ms_no, allStates, probDict)
    
    actions, timeDict = genMDP.action2str(num_a, num_s, teamTime, allStates, a_prefix, s_prefix, a_list, s_list, pathToDict)

    kg_module = genMDP.construct_kg_module(actions, timeDict, allStates_dict, numASM, prefixList, a_list, s_list, teamTime, relation_as, relation_ms,probDict,pathToDict,missionLength, t)

    rewardsName = rewardList[0]    # criteria we care about
    rewards_module1 = genMDP.construct_num_agents_cost(num_a, num_s, teamTime, allStates, a_prefix, s_prefix, a_list, s_list, m_list, pathToDict, rewardsName)
    # rewards_module2 = constructEachPModule(num_a, num_s, num_m,a_list, s_list,teamTime, teamTimeID, relation_as, relation_ms_no,a_prefix, s_prefix, m_prefix, probDict, pathToDict)
    kg_module, rewards_module1 = genMDP.replace_idx(a_list, s_list, m_list, kg_module, rewards_module1)

        # save adv files to Verification folder
    current_dir = str(os.getcwd())
    timestep_path = current_dir+'/t'+str(t)
    os.mkdir(timestep_path)

    # save PRISM files to current directory
    mdp_file = timestep_path + '/' + mdpFile
    output_path = timestep_path + '/' + outputFile 
    
    modules = [kg_module, rewards_module1]
    genMDP.save_mdp_file(modules, mdp_file)
  
    call_prism(mdp_file, mission_str, output_path, prism_path, timestep_path)
 
    # change directory back
    os.chdir(current_dir)
    result = output_result(output_path)
    
    teams = parseADV.parse_adv_main(pathToDict, timestep_path)
    
    # print('time for timestep: ', time.time()-t0)
    # delete directory
    shutil.rmtree(timestep_path)

    return result, teams

def main(team, path_mission_json):
    mission_length = encodeMission.findMissionLength(path_mission_json)

    target = extractJSON.findTarget(path_mission_json)
    construct_team(team)
    teamTime1 = extractJSON.find_time_bounds(team, target, path_time_json)

    def parallelize(i, q):
        teamUpd = team_per_timestep(team, teamTime1, i)
        q.put(main_parallelized(target, teamUpd, i))

    qout = mp.Queue()
    processes = [mp.Process(target=parallelize, args=(i, qout)) for i in range(mission_length)]
    for p in processes:
        p.start()

    for p in processes:
        p.join()

    result = []
    teaming = []
    for p in processes:
        result_p, teaming_p = qout.get()
        result.append(result_p)
        teaming.append(teaming_p)

    # merge all teaming dictionaries into one
    teams = {k: v for d in teaming for k, v in d.items()}

    optimal_teaming = parseADV.pareto_plot_all(result, teams)
    print('\n ===================== OPTIMAL TEAM ===================== ')
    print(optimal_teaming)

    return optimal_teaming


if __name__== "__main__":
    # data from knowledge graph 
    path_mission_json = 'mission.json'
    path_time_json = 'accesses.json'
    pathToDict = '../KG_examples/outputs_KGMLN_1/output.dict'
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

    team2 = {'GOES-17': [{'ABI': {'Cloud type': [0.84130652]} }], \
    'GOES-16': [{'ABI': {'Fire temperature': [0.99999966], 'Cloud type': [0.84130652]} }], \
    'Landsat 8':[{'TIRS': {'Land surface topography': [1.]} }], \
    'KOMPSAT-3A':[{'AEISS-A': {'Land surface topography': [1.]} }], \
    'Jason-3': [{'POSEIDON-3B Altimeter': {'Land surface topography': [1.]} }], \
    'Elektro-L N3': [{'DCS': {'Land surface temperature': [0.99899652]} }], \
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


    team = team_bench
    main(team, path_mission_json)
    

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
    





