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
        team         {agent1: [{sensor1: {obs1: P1}, {sensor2: {obs2: P2}}}], agent2: [{sensor3: {obs3: P3} }] }
                    for example: {'Meteor-M N2-2': [{'BRLK': {'Land cover': P1}}, {'MSU-MR': {'Sea-ice cover': P2}    }], \
                                  'TerraSAR-X': [{'X-Band SAR': {'Sea-ice cover': P3}}]}

        target         location to monitor, type string

    output:
        new_team     {agent1: {sensor1__1: [[t1 t2], [t3 t4], ...]}, agentname: {sensor2__1: ...}}
    '''
    sensor_times = {}      
    new_team = {}
    with open(access_intervals) as time_file:
        dataTime = json.load(time_file) 
        for a in team.keys():
            instrument = dataTime["output"][a]
            sensor_times = {}
            for i in range(len(team[a])):       # for each sensor of an agent
                S = list(team[a][i].keys())[0]
                s, sIdx = S.split('__')
                sensor_times[S] = []
                location = instrument[s]
                time_array = location[target]
                started = 0
                duration = []

                if time_array['timeArray'] == []:    # if empty
                    # raise ValueError ('location is never visible to sensor ' + s + ' on platform ' + a)
                    print('location is never visible to sensor ' + s + ' on platform ' + a)

                for d in time_array['timeArray']:     # for each dict within time_array
                    if d['isRise']:                  # isRise: True
                        t_init = math.floor(d['time']/(3600.*24))         # rounding times down: anytime within 0-1 day => seen in day 0
                        duration.append(t_init)
                        started = 1
                    else:
                        if started:
                            t_final = math.ceil(d['time']/(3600.*24)) # rounding times up: anytime within 0-1 day => seen in day 0
                            duration.append(t_final)
                            sensor_times[S].append(duration)
                            duration = []
                            started = 0
                new_team[a] = sensor_times
    return new_team

def generate_team_time_id(entity_dict, team_time, a_prefix, s_prefix):
    ''' convert team_time agent names and sensor names into 'aID' and 'sID'
    '''
    team_time_id = copy.deepcopy(team_time)
    for a in team_time.keys():
        aID = find_id(a, entity_dict, a_prefix)
        team_time_id[aID] = team_time_id.pop(a)
        # print(team_time_id)
        for s in team_time[a].keys():       # for each sensor of an agent
            sID = find_id(s, entity_dict, s_prefix, sensor = True)
            team_time_id[aID][sID] = team_time_id[aID].pop(s)
    
    return team_time_id

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
        name, sensorIdx = name.split('__')

    with  open(entity_dict, 'r',  encoding='latin-1') as file:
        # matched_lines = [line for line in file.split('\n') if sensor in line]
        matched_lines = line_with_string(name, file)      # 'sensorID: sensor name'
        ID = matched_lines.split(':')[0]                    # 'BRLK' -> 'Sensor1512'

    # 'Sensor1512' -> 's1512'
    idx = 0
    new_id = ''
    for char in ID:
        idx +=1
        if char.isdigit():
            new_id += char
    new_id = col_prefix + new_id
    new_id = new_id.rstrip()

    if sensor:
        new_id += '__' + sensorIdx
    return new_id

def find_name(ent_id, entity_dict, col_name):
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

    with open(entity_dict, 'r',  encoding='latin-1') as file:
        # matched_lines = [line for line in file.split('\n') if sensor in line]
        matched_lines = line_with_string2(new_id, file)      # 'sensorID: sensor name'
        name = matched_lines.split(':')[1]                    # 'Sensor1512' -> 'BRLK'
    name = name[1:].rstrip()

    return name


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
    for a in list(team.keys()):
        agent_id = find_id(a, entity_dict, prefix)
        a_list.append(agent_id)
    sort_nicely(a_list)
    return a_list


def generate_s_list(team, entity_dict, prefix):
    s_list = set()
    # s_list = []
    for a in team.keys():
        for i in range(len(team[a])):       # for each sensor of an agent
            s = list(team[a][i].keys())[0]
            sensor_id = find_id(s, entity_dict, prefix, sensor = True)
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
    for a in list(team.keys()):
        sensor_ids = []
        for i in range(len(team[a])):       # for each sensor of an agent
            s = list(team[a][i].keys())[0]
            sensor_ids.append(find_id(s, entity_dict, s_prefix, sensor = True))
        sort_nicely(sensor_ids)
        agent_id = find_id(a, entity_dict, a_prefix)
        as_dict[agent_id] = sensor_ids
    return as_dict


def create_sm_dict(team, entity_dict, s_prefix, m_prefix):
    ''' convert team to only have sensor and measurement IDs
    {s1: [[m1, P1]], s2: [[m2, P2]]], ...}}
    '''
    sm_dict = {}
    for a in team.keys():
        for i in range(len(team[a])):       # for each sensor of an agent
            measurement_ids = []
            s = list(team[a][i].keys())[0]
            for m in list(team[a][i][s].keys()):
                measurement_ids.append([find_id(m, entity_dict, m_prefix), team[a][i][s][m]])
            # sort_nicely(mIDs)
            sensor_id = find_id(s, entity_dict, s_prefix, sensor = True)
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
            mat[idx][n] = s[1][0]
    return mat


def not_meas_mat(team, entity_dict, relation_ms, num_m, num_s, m_prefix, s_prefix, m_list, s_list):
    # which sensors DO NOT take what measurements with what probability

    # sm_dict = create_smDict(team, entity_dict, s_prefix, m_prefix)       # {s1: [[m1, P1]], s2: [[m2, P2]]], ...}}

    sm_dict = {}           # {s1: {m1: [P1], m2: [P2]}, s2: {m1: [P1]}, ...}}
    for a in team.keys():
        for i in range(len(team[a])):       # for each sensor of an agent
            mIDs = []
            m_dict = {}
            s = list(team[a][i].keys())[0]
            for m in list(team[a][i][s].keys()):
                mID = find_id (m, entity_dict, m_prefix)
                m_dict[mID] = team[a][i][s][m]
            sID = find_id (s, entity_dict, s_prefix, sensor = True)
            sm_dict[sID] = m_dict


    probDict = {}            # {'P1': [0.7, 0.6], 'P2': [0.8, 0.9]} 
    # probSensorDict = {}       # {'s1': {'P1': [0.7, 0.6]}, 's2': {'P2': [0.8, 0.9]}}
    relation_ms_no_str = np.chararray((num_m, num_s),itemsize=10)
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
                probDict['P'+str(idx)] = sm_dict[s_list[c]][m_list[r]]
                temp = sm_dict[s_list[c]]
                # remove measurement to keep track of which measurements we've already assigned strings to
                # temp.pop(0)
                sm_dict[s_list[c]] = temp
                    # tempDict['P'+str(idx)] = sm_dict[s_list[c]][0][1]
                sensor = s_list[c]
                # probSensorDict['s'+str(s_list.index(sensor)+1)] = tempDict
    relation_ms_no_str = relation_ms_no_str.decode("utf-8")     # convert byte to string
    return relation_ms_no_str, probDict