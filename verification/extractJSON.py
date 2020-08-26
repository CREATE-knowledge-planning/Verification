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

def findTimeBounds(team, target, pathTimeJSON):
    '''
    given a team and target to monitor, extract time bounds of sensor visibility from the JSON file
    input:
        team 		{agent1: [{sensor1: {obs1: P1}, {sensor2: {obs2: P2}}}], agent2: [{sensor3: {obs3: P3} }] }
                    for example: {'Meteor-M N2-2': [{'BRLK': {'Land cover': P1}}, {'MSU-MR': {'Sea-ice cover': P2}    }], \
                                  'TerraSAR-X': [{'X-Band SAR': {'Sea-ice cover': P3}}]}

        target 		location to monitor, type string

    output:
        newTeam 	{agent1: {sensor1__1: [[t1 t2], [t3 t4], ...]}, agentname: {sensor2__1: ...}}
    '''
    sensorTimes = {}
    newTeam = {}
    with open(pathTimeJSON) as time_file:
        dataTime = json.load(time_file)
        for a in team.keys():
            instrument = dataTime["output"][a]
            sensorTimes = {}
            for i in range(len(team[a])):       # for each sensor of an agent
                S = list(team[a][i].keys())[0]
                s, sIdx = S.split('__')
                sensorTimes[S] = []
                location = instrument[s]
                timeArray = location[target]
                started = 0
                duration = []

                if timeArray['timeArray'] == []:    # if empty
                    raise ValueError ('location is never visible to sensor ' + s + ' on platform ' + a)

                for d in timeArray['timeArray']: 	# for each dict within timeArray
                    if d['isRise']:      			# isRise: True
                        t_init = math.floor(d['time']/(3600.*24)) 		# rounding times down: anytime within 0-1 day => seen in day 0
                        duration.append(t_init)
                        started = 1
                    else:
                        if started:
                            t_final = math.ceil(d['time']/(3600.*24)) # rounding times up: anytime within 0-1 day => seen in day 0
                            duration.append(t_final)
                            sensorTimes[S].append(duration)
                            duration = []
                            started = 0
                newTeam[a] = sensorTimes
    return newTeam

def generate_teamTimeID(pathToDict, teamTime, a_prefix, s_prefix):
    ''' convert teamTime agent names and sensor names into 'aID' and 'sID'
    '''
    teamTimeID = copy.deepcopy(teamTime)
    for a in teamTime.keys():
        aID = findID(a, pathToDict, a_prefix)
        teamTimeID[aID] = teamTimeID.pop(a)
        # print(teamTimeID)
        for s in teamTime[a].keys():       # for each sensor of an agent
            sID = findID(s, pathToDict, s_prefix, sensor = True)
            teamTimeID[aID][sID] = teamTimeID[aID].pop(s)

    return teamTimeID

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

def findID(name, pathToDict, col_prefix, sensor = False):
    ''' given a sensor name, convert name to sensor ID from output.dict 
    if sensor = True, we have '__num' at the end of each name
    example: 'BRLK__1' -> 'Sensor1512' -> 's1512' -> 's1512__1'
    '''
    # print(sensorName.split('~'))
    if sensor:
        name, sensorIdx = name.split('__')

    with open(pathToDict, 'r',  encoding='latin-1') as file:
        # matched_lines = [line for line in file.split('\n') if sensor in line]
        matched_lines = line_with_string(name, file)      # 'sensorID: sensor name'
        ID = matched_lines.split(':')[0]                    # 'BRLK' -> 'Sensor1512'

    # 'Sensor1512' -> 's1512'
    idx = 0
    newID = ''
    for char in ID:
        idx +=1
        if char.isdigit():
            newID += char
    newID = col_prefix + newID
    newID = newID.rstrip()

    if sensor:
        newID += '__' + sensorIdx
    return newID

def findName(ID, pathToDict, col_name):
    ''' given a sensor ID, convert ID to sensor name from output.dict 
    example: 's1512' -> 'Sensor1512' -> 'BRLK'
    '''
    # 's1512' -> 'Sensor1512'
    idx = 0
    newID = ''
    for char in ID:
        idx +=1
        if char.isdigit():
            newID += char
    newID = col_name + newID

    with open(pathToDict, 'r',  encoding='latin-1') as file:
        # matched_lines = [line for line in file.split('\n') if sensor in line]
        matched_lines = line_with_string2(newID, file)      # 'sensorID: sensor name'
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

def generateAlist(team, pathToDict, prefix):
    a_list = []
    for a in list(team.keys()):
        aID = findID(a, pathToDict, prefix)
        a_list.append(aID)
    sort_nicely(a_list)
    return a_list

def generateSlist(team, pathToDict, prefix):
    s_list = set()
    # s_list = []
    for a in team.keys():
        for i in range(len(team[a])):       # for each sensor of an agent
            s = list(team[a][i].keys())[0]
            sID = findID(s, pathToDict, prefix, sensor = True)
            # s_list.add(sID+ "~"+s[:-1])
            s_list.add(sID)
    s_list = list(s_list)
    sort_nicely(s_list)
    return s_list

def generateMlist(team, pathToDict, prefix):
    m_list = set()
    for a in team.keys():
        for i in range(len(team[a])):       # for each sensor of an agent
            s = list(team[a][i].keys())[0]
            for m in list(team[a][i][s].keys()):
                mID = findID(m, pathToDict, prefix)
                m_list.add(mID)
    m_list = list(m_list)
    sort_nicely(m_list)
    return m_list

def generateASMlists(team, pathToDict, a_prefix, s_prefix, m_prefix):
    a_list = generateAlist(team, pathToDict, a_prefix)
    s_list = generateSlist(team, pathToDict, s_prefix)
    m_list = generateMlist(team, pathToDict, m_prefix)
    return a_list, s_list, m_list

def create_asDict(team, pathToDict, a_prefix, s_prefix):
    ''' convert team to only have agent and sensor IDs
    {a1: [s1, s2], a2: [s1, s3, s4], ...}}
    '''
    asDict = {}
    for a in list(team.keys()):
        sIDs = []
        for i in range(len(team[a])):       # for each sensor of an agent
            s = list(team[a][i].keys())[0]
            sIDs.append(findID(s, pathToDict, s_prefix, sensor = True))
        sort_nicely(sIDs)
        aID = findID(a, pathToDict, a_prefix)
        asDict[aID] = sIDs
    return asDict

def create_smDict(team, pathToDict, s_prefix, m_prefix):
    ''' convert team to only have sensor and measurement IDs
    {s1: [[m1, P1]], s2: [[m2, P2]]], ...}}
    '''
    smDict = {}
    for a in team.keys():
        for i in range(len(team[a])):       # for each sensor of an agent
            mIDs = []
            s = list(team[a][i].keys())[0]
            for m in list(team[a][i][s].keys()):
                mIDs.append([findID(m, pathToDict, m_prefix), team[a][i][s][m]])
            # sort_nicely(mIDs)
            sID = findID(s, pathToDict, s_prefix, sensor = True)
            smDict[sID] = mIDs
    # print('smDict', smDict)
    return smDict

def construct_asMatrix(team, pathToDict, num_row, num_col, a_prefix, s_prefix, a_list, s_list):
    as_dict = create_asDict(team, pathToDict, a_prefix, s_prefix)
    mat = np.zeros((num_row,num_col))
    for n in range(num_row):
        for s in as_dict[a_prefix+ a_list[n][1:]]:
            idx = s_list.index(s)
            mat[n][idx] = 1
    return mat

def construct_msMatrix(team, pathToDict, num_row, num_col, m_prefix, s_prefix, m_list, s_list):
    ''' each element in matrix is probability of sensor observing measurement
    '''
    sm_dict = create_smDict(team, pathToDict, s_prefix, m_prefix)
    mat = np.zeros((num_row,num_col))
    for n in range(num_col):
        for s in sm_dict[s_prefix + s_list[n][1:]]:
            idx = m_list.index(s[0])
            mat[idx][n] = s[1][0]
    return mat

def notMeasMat(team, pathToDict, relation_ms, num_m, num_s, m_prefix, s_prefix, m_list, s_list):
    # which sensors DO NOT take what measurements with what probability

    # sm_dict = create_smDict(team, pathToDict, s_prefix, m_prefix)       # {s1: [[m1, P1]], s2: [[m2, P2]]], ...}}

    sm_dict = {}   		# {s1: {m1: [P1], m2: [P2]}, s2: {m1: [P1]}, ...}}
    for a in team.keys():
        for i in range(len(team[a])):       # for each sensor of an agent
            mIDs = []
            m_dict = {}
            s = list(team[a][i].keys())[0]
            for m in list(team[a][i][s].keys()):
                mID = findID(m, pathToDict, m_prefix)
                m_dict[mID] = team[a][i][s][m]
            sID = findID(s, pathToDict, s_prefix, sensor = True)
            sm_dict[sID] = m_dict


    probDict = {}    		# {'P1': [0.7, 0.6], 'P2': [0.8, 0.9]}
    # probSensorDict = {}   	# {'s1': {'P1': [0.7, 0.6]}, 's2': {'P2': [0.8, 0.9]}}
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
    relation_ms_no_str = relation_ms_no_str.decode("utf-8") 	# convert byte to string
    return relation_ms_no_str, probDict
