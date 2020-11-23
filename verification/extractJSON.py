#!/usr/bin/env python

import json
import math
import re
import numpy as np
import copy


def findTarget(pathMissionJSON):
    with open(pathMissionJSON) as file:
        data = json.load(file)
        return data['locations'][0]['name']       # assuming there's only one location in mission


def find_time_bounds(team, target, access_intervals):
    '''
    given a team and target to monitor, extract time bounds of sensor visibility from the JSON file
    input:
        team 		[{'name': 'agent1', 'sensors': [{sensor1: {obs1: P1}, {sensor2: {obs2: P2}}}], agent2: [{sensor3: {obs3: P3} }] }]
                    for example: {'Meteor-M N2-2': [{'BRLK': {'Land cover': P1}}, {'MSU-MR': {'Sea-ice cover': P2}    }], \
                                  'TerraSAR-X': [{'X-Band SAR': {'Sea-ice cover': P3}}]}

        target 		location to monitor, type string

    output:
        newTeam 	{agent1: {sensor1__1: [[t1 t2], [t3 t4], ...]}, agentname: {sensor2__1: ...}}
    '''
    sensor_times = {}
    new_team = []
    for agent in team:
        instrument = access_intervals["output"][agent["name"]]
        sensor_times = {}
        for sensor in agent["sensors"]:       # for each sensor of an agent
            full_sensor_name = sensor["name"]
            sensor_name, _ = full_sensor_name.split('__')
            sensor_times = []
            location = instrument[sensor_name]
            time_array = location[target]
            started = 0
            duration = []

            if time_array['timeArray'] == []:    # if empty
                raise ValueError ('location is never visible to sensor ' + sensor_name + ' on platform ' + agent["name"])

            for d in time_array['timeArray']: 	# for each dict within timeArray
                if d['isRise']:      			# isRise: True
                    t_init = math.floor(d['time']/(3600.*24)) 		# rounding times down: anytime within 0-1 day => seen in day 0
                    duration.append(t_init)
                    started = 1
                else:
                    if started:
                        t_final = math.ceil(d['time']/(3600.*24)) # rounding times up: anytime within 0-1 day => seen in day 0
                        duration.append(t_final)
                        sensor_times.append(duration)
                        duration = []
                        started = 0
            sensor["times"] = sensor_times
        new_team.append(agent)
    return new_team


def generate_team_time_id(entity_dict, team_time, a_prefix, s_prefix):
    ''' convert team_time agent names and sensor names into 'aID' and 'sID'
    '''
    team_time_id = copy.deepcopy(team_time)
    for idx, agent in enumerate(team_time):
        agent_id = find_id(agent["name"], entity_dict, a_prefix)
        team_time_id[idx]["name"] = agent_id
        # print(teamTimeID)
        for idx_s, sensor in enumerate(agent["sensors"]):       # for each sensor of an agent
            sensor_id = find_id(sensor["name"], entity_dict, s_prefix, sensor=True)
            team_time_id[idx]["sensors"][idx_s]["name"] = sensor_id

    return team_time_id


def load_entity_dict(path_to_dict):
    # Load entity dictionary from disk
    with path_to_dict.open('r',  encoding='latin-1') as entity_dict_file:
        entity_dict = {}
        inv_entity_dict = {}
        for line in entity_dict_file:
            ent_id, name = line.split(': ')
            entity_dict[name[:-1]] = ent_id
            inv_entity_dict[ent_id] = name[:-1]
    return entity_dict, inv_entity_dict


def line_with_string(string, fp):
    ''' find line that contains a substring at the end of line (assumes the substring only appears once)
    '''
    for line in fp:
        if line.endswith(string+'\n'):
            return line


def line_with_string2(string, fp):
    ''' find line that contains a substring (assumes the substring only appears once)
    '''
    for line in fp:
        if string in line:
            return line


def find_id(name, entity_dict, col_prefix, sensor = False):
    ''' given a sensor name, convert name to sensor ID from output.dict 
    if sensor = True, we have '__num' at the end of each name
    example: 'BRLK__1' -> 'Sensor1512' -> 's1512' -> 's1512__1'
    '''
    # print(sensorName.split('~'))
    if sensor:
        name, sensor_idx = name.split('__')

    ent_id = entity_dict[name]

    # 'Sensor1512' -> 's1512'
    idx = 0
    new_id = ''
    for char in ent_id:
        idx += 1
        if char.isdigit():
            new_id += char
    new_id = col_prefix + new_id
    new_id = new_id.rstrip()

    if sensor:
        new_id += '__' + sensor_idx
    
    return new_id


def find_name(ent_id, inv_entity_dict, col_name):
    ''' given a sensor ID, convert ID to sensor name from output.dict 
    example: 's1512' -> 'Sensor1512' -> 'BRLK'
    '''
    # 's1512' -> 'Sensor1512'
    idx = 0
    new_id = ''
    for char in ent_id:
        idx +=1
        if char.isdigit():
            new_id += char
    new_id = col_name + new_id

    return inv_entity_dict[new_id]



# -------- these three functions are used to sort strings with numbers at the end -------- 
def tryint(s):
    try:
        return int(s)
    except ValueError:
        return s


def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    return [ tryint(c) for c in re.split('([0-9]+)', s) ]


def sort_nicely(l):
    """ Sort the given list: [a1, a3, a15]
    """
    l.sort(key=alphanum_key)
# ----------------------------------------------------------------------------------------


def generate_a_list(team, entity_dict, prefix):
    a_list = []
    for agent in team:
        agent_id = find_id(agent["name"], entity_dict, prefix)
        a_list.append(agent_id)
    sort_nicely(a_list)
    return a_list


def generate_s_list(team, entity_dict, prefix):
    s_list = set()
    # s_list = []
    for agent in team:
        for sensor in agent["sensors"]:       # for each sensor of an agent
            sensor_name = sensor["name"]
            sensor_id = find_id(sensor_name, entity_dict, prefix, sensor=True)
            # s_list.add(sID+ "~"+s[:-1])
            s_list.add(sensor_id)
    s_list = list(s_list)
    sort_nicely(s_list)
    return s_list


def generate_m_list(team, simulation_file, entity_dict, prefix):
    m_list = []
    with open(simulation_file) as file:
        data = json.load(file)
        measurements = data["observable_properties"]

    for m in measurements:
        measurement_id = find_id(m, entity_dict, prefix)
        m_list.append(measurement_id)
    return m_list

def generate_as_lists(team, entity_dict, a_prefix, s_prefix):
    a_list = generate_a_list(team, entity_dict, a_prefix)
    s_list = generate_s_list(team, entity_dict, s_prefix)
    # m_list = generate_m_list(team, entity_dict, m_prefix)
    return a_list, s_list


def create_as_dict(team, entity_dict, a_prefix, s_prefix):
    ''' convert team to only have agent and sensor IDs
    {a1: [s1, s2], a2: [s1, s3, s4], ...}}
    '''
    as_dict = {}
    for agent in team:
        sensor_ids = []
        for sensor in agent["sensors"]:       # for each sensor of an agent
            sensor_name = sensor["name"]
            sensor_ids.append(find_id(sensor_name, entity_dict, s_prefix, sensor=True))
        sort_nicely(sensor_ids)
        agent_id = find_id(agent["name"], entity_dict, a_prefix)
        as_dict[agent_id] = sensor_ids
    return as_dict


def create_sm_dict(team, entity_dict, s_prefix, m_prefix):
    ''' convert team to only have sensor and measurement IDs
    {s1: [[m1, P1]], s2: [[m2, P2]]], ...}}
    '''
    sm_dict = {}
    for agent in team:
        for sensor in agent["sensors"]:       # for each sensor of an agent
            measurement_ids = []
            sensor_name = sensor["name"]
            for measurement in sensor["characteristics"].keys():
                measurement_ids.append([find_id(measurement, entity_dict, m_prefix), sensor["probabilities"][measurement]["p_tp"]])
            # sort_nicely(mIDs)
            sensor_id = find_id(sensor_name, entity_dict, s_prefix, sensor=True)
            sm_dict[sensor_id] = measurement_ids
    # print('smDict', smDict)
    return sm_dict


def construct_as_matrix(team, entity_dict, num_row, num_col, a_prefix, s_prefix, a_list, s_list):
    as_dict = create_as_dict(team, entity_dict, a_prefix, s_prefix)
    mat = np.zeros( (num_row, num_col) )
    for n in range(num_row):
        for s in as_dict[a_prefix + a_list[n][1:]]:
            idx = s_list.index(s)
            mat[n][idx] = 1
    return mat


def construct_ms_matrix(team, entity_dict, num_row, num_col, m_prefix, s_prefix, m_list, s_list):
    ''' each element in matrix is probability of sensor observing measurement
    '''
    sm_dict = create_sm_dict(team, entity_dict, s_prefix, m_prefix)
    mat = np.zeros((num_row,num_col))
    for n in range(num_col):
        for s in sm_dict[s_prefix + s_list[n][1:]]:
            idx = m_list.index(s[0])
            mat[idx][n] = s[1]
    return mat


def not_meas_mat(team, entity_dict, relation_ms, num_m, num_s, m_prefix, s_prefix, m_list, s_list):
    # which sensors DO NOT take what measurements with what probability

    # sm_dict = create_smDict(team, pathToDict, s_prefix, m_prefix)       # {s1: [[m1, P1]], s2: [[m2, P2]]], ...}}

    sm_list = create_sm_dict(team, entity_dict, s_prefix, m_prefix)	
    sm_dict = {}	                                                      # {s1: {m1: [P1], m2: [P2]}, s2: {m1: [P1]}, ...}}
    for sensor_name, sensor_measurements in sm_list.items():
        sensor_info = {}
        for measurement_pair in sensor_measurements:
            sensor_info[measurement_pair[0]] = [measurement_pair[1]]
        sm_dict[sensor_name] = sensor_info

    prob_dict = {}    		# {'P1': [0.7, 0.6], 'P2': [0.8, 0.9]}
    # probSensorDict = {}   	# {'s1': {'P1': [0.7, 0.6]}, 's2': {'P2': [0.8, 0.9]}}
    relation_ms_no_str = np.chararray((num_m, num_s), itemsize=10)
    idx = 0
    # relation_ms_no = 1-relation_ms
    for r in range(num_m):
        for c in range(num_s):
            if relation_ms[r][c] == 0:
                relation_ms_no_str[r][c] = '1'
            else:
                # tempDict = {}
                idx += 1
                decimals = 3
                relation_ms_no_str[r][c] = '1-P' + str(idx) #+ '/' + str(10**decimals)
                # print(sm_dict[s_list[c]])
                # print(sm_dict[s_list[c]][m_list[r]])
                prob_dict['P'+str(idx)] = sm_dict[s_list[c]][m_list[r]]
                temp = sm_dict[s_list[c]]
                # remove measurement to keep track of which measurements we've already assigned strings to
                # temp.pop(0)
                sm_dict[s_list[c]] = temp
                # tempDict['P'+str(idx)] = sm_dict[s_list[c]][0][1]
                sensor = s_list[c]
            # probSensorDict['s'+str(s_list.index(sensor)+1)] = tempDict
    relation_ms_no_str = relation_ms_no_str.decode("utf-8") 	# convert byte to string
    return relation_ms_no_str, prob_dict
