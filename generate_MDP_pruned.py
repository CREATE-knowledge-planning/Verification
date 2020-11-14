 #!/usr/bin/env python

from bidict import bidict
import numpy as np
import itertools
from extractJSON import find_name, find_id, find_time_bounds
import time # to debug inefficiencies

'''
GENERATE FORMULAS FOR PROBABILITIES AS STRINGS INSTEAD OF DOUBLES TO PASS INTO PRISM

WE ASSUME THAT:
- AGENTS CAN CHOOSE IF SENSORS ARE ON OR OFF
- PROBABILITIES ARE STATIC WITHIN VISIBILITY WINDOW, 0 OTHERWISE

MDP HAS BEEN PRUNED TO REDUCE THE NUMBER OF STATES (AGENTS WITH NO OVERLAPPING VISIBILITY WINDOWS CANNOT BE USED TOGETHER)
'''

 ###############################################################
 ####### FUNCTIONS FOR GENERATING STATES & PROBABILITIES #######
 ###############################################################
def getOverlap(a, b):
    ''' check for overlap between two intervals, 0 if no overlap
    '''
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))

def visibilityOverlap(range1, range2):
    ''' given two sensors visibilty ranges (ex:  [[0, 1], [4, 5]] and  [[2, 3], [3, 4], [5, 6], [6, 7]]),
    check if they overlap at all
    '''
    for w1 in range1:
        for w2 in range2:
            if getOverlap(w1,w2) != 0:
                return True
    return False

def all_states_as(num_a, num_s, relation_as, a_list, s_list, teamTimeID):
    '''generates all possible a_s matrix states ASSUMING AGENTS CAN CHOOSE WHICH OF ITS SENSORS ARE ON OR OFF'''
    # states_array = [np.zeros((num_a, num_s))]   # include "no agent" state
    # a_list = ['a355', 'a368', 'a390', 'a471', 'a472', 'a560']
    # s_list = ['s742__1', 's935__1', 's1452__1', 's1588__1', 's1606__1', 's1606__2']
    # teamTimeID = {'a471': {'s1606__1': [[0, 7]]}, 'a472': {'s1606__2': [[0, 7]]}, 'a355': {'s742__1': [[1, 2]]}, 'a368': {'s1588__1': [[0, 1], [4, 5]]}, 'a390': {'s935__1': [[2, 3], [3, 4], [5, 6], [6, 7]]}, 'a560': {'s1452__1': [[0, 7]]}}

    states_array = [np.zeros((num_a, num_s))]
    lst_a = []

    # assemble list of indices of which rows and cols are 1
    rows, cols = np.where(relation_as == 1)    

    for i in range(len(rows)):
        lst_a.append([rows[i],cols[i]])

    # combination of all the indices
    combs = []
    lst = range(len(lst_a))
    for i in range(1, len(lst_a)+1):
        els = [list(x) for x in itertools.combinations(lst_a, i)]
        combs.extend(els)

    # for each combination, set indices in that combination to be 1
    for c in range(len(combs)):

        # print('c',combs[c])
        state = np.zeros((num_a, num_s))
        check = []
        for j in range(len(combs[c])):
            # print('idx',combs[c][j])
            agent = a_list[combs[c][j][0]]
            sensor = s_list[combs[c][j][1]]
            check.append([agent,sensor])
            state[combs[c][j][0]][combs[c][j][1]] = 1
        vis = True
        if len(check) == 1:
            states_array.append(state)
        else:
            
            for s1 in range(len(check)):
                for s2 in range(len(check)):
                    if s1 != s2:
                        range1 = teamTimeID[check[s1][0]][check[s1][1]]
                        range2 = teamTimeID[check[s2][0]][check[s2][1]]
                        vis = visibilityOverlap(range1, range2)
                        # print(check[s1], range1, check[s2], range2, vis)
                        if not vis:
                            break
                else:
                    continue 
                break
        if vis:
            states_array.append(state)

    # print('# of states: ',len(states_array))
    return states_array

def all_states_as2(num_a, num_s, relation_as):
    '''generates all possible a_s matrix states ASSUMING AGENTS CANNOT CHOOSE WHICH OF ITS SENSORS ARE ON OR OFF'''
    states_array = [np.zeros((num_a, num_s))]
    # generate all combos of a (for num_a = 2: [0 0]', [0,1]', [1,0]', [1,1]'')
    allcombos_a = [np.reshape(np.array(i), (1, num_a)) for i in itertools.product([0, 1], repeat = 1*num_a)]

    # for each combination, set indices in that combination to be 1
    for c in range(len(allcombos_a)):
        state = np.multiply(relation_as,np.transpose(allcombos_a[c]))
        states_array.append(state)
    return states_array


def sensors_on(num_s, current_as):
    '''generates list of which sensors are currently on.
        1 x num_s, each element is 1 or 0'''
    sensorsOn_array = []
    for col in range(num_s):
        if any(current_as[:,col]):      # if sensor is on
            sensorsOn_array.append(1)
        else:
            sensorsOn_array.append(0)
    return sensorsOn_array

def prob_measZero(current_as, relation_ms_no, num_m, num_s, probDict):
    '''probability that all measurements = 0 given the current a_s state
    [p_m1 = 0, p_m2 = 0]
    returns probability as a string
    relation_ms_no is a string if we want P1, P2, etc. rather than the actual values'''

    sensorsOn_array = sensors_on(num_s, current_as)
    prob_array = np.chararray((num_m, num_s),itemsize=10)     #itemsize may need to increase depending on # of P's
    # current probability that m_i = 0 for each sensor 
    for row in range(num_m):
        for col in range(num_s):
            if sensorsOn_array[col]:   # if sensor is on
                prob_array[row][col] = relation_ms_no[row][col]
            else:
                prob_array[row][col] = '0'
    # print('prob array', prob_array)

    # prob_array = relation_ms_no * sensorsOn_array # 
    # multiply the non-zero probabilities in prob_array together 
    # to get total probability for each m_i
    for p in list(probDict.keys()):
        exec(p + '=' + str(probDict[p][0]))

    prob_m00 = []      
    for m in range(num_m):
        total_prob = ''
        for s in range(num_s):
            prob = (prob_array[m][s]).decode("utf-8")   # convert byte to string
            if prob != '0' and prob != '1':    # if prob = 1, we can ignore (no need to multiply it)
                total_prob += '('+prob + ')'+'*'
        if total_prob == '':
            total_prob = '1*'
        
                # simplify expression
        if eval(total_prob[:-1]) == 0:
            total_prob = '0*'
        elif eval(total_prob[:-1]) == 1:
            total_prob = '1*'
        prob_m00.append(total_prob[:-1])      # don't include last '*'
    return prob_m00

def measZero_all(numASM, relation_ms_no, allStates, probDict):
    '''Generates probabilities of m_i = 0 for all possible states, and
        creates a dictionary of {states_as:probabilities each m_i = 0}. states_as is 
        flattened to be a list.'''

    # prob_m00_array = []

    num_a, num_s, num_m = numASM
    prob_m00_dict = {}
    # allStates = all_states_as(num_a, num_s, relation_as, a_list, s_list, teamTimeID)
    for state in allStates:
        #state.setflags(write = False)
        # flatten state and make it a tuple
        prob_m00 = prob_measZero(state, relation_ms_no, num_m, num_s, probDict)
        # prob_m00_array.append((state, prob_m00))
        state_flat = tuple(state.flatten())
        prob_m00_dict[state_flat] = prob_m00

    return prob_m00_dict


def mProb_all(numASM, relation_as, current_as, measZero_dict, probDict):
    ''' find the probability each possible [m1, m2] given the current state. 
        Returns mProb_dict, a dictionary {(m1, m2): probability}'''
    
    num_a, num_s, num_m = numASM
    for p in list(probDict.keys()):
        exec(p + '=' + str(probDict[p][0]))
    # generate all combos of m (for num_m = 2: [0 0], [0,1], [1,0], [1,1])
    allcombos_m = [np.reshape(np.array(i), (1, num_m)) for i in itertools.product([0, 1], repeat = 1*num_m)]
    # measZero_dict = measZero_all(num_a, num_s, relation_as)
    # print('zero', measZero_dict)
    current_flat = tuple(current_as.flatten())
    # print(current_flat, measZero_dict[current_flat])

    mProb_dict = {}
    for c in range(len(allcombos_m)):
        # P = 1
        P = ''
        combo = allcombos_m[c][0]

        for m in range(num_m):
            if not combo[m]:    # if m_i = 0 and the prob isn't 1
                p_m = '(' + measZero_dict[current_flat][m] +')'
            else:
                # p_m = 1-measZero_dict[current_flat][m]
                p_m = '(1-'+measZero_dict[current_flat][m] + ')'

            if p_m == '(0)':         # if one probability is zero, then the product is also zero
                P = '0'
                break
            if p_m != '(1)':        # no need to concatenate if mutiplying by 1
                P += '*'+p_m
        # mProb_dict[tuple(combo)] = round(P,10)

        # simplify expression

        if P == '':
            P = '*1'
        elif P == '0':
            P = '*0'
        elif eval(P[1:]) == 0:
            P = '*0'
        elif eval(P[1:]) == 1:
            P = '*1'
        if eval(P[1:]) != 0:
            mProb_dict[tuple(combo)] = eval(P[1:])      # don't include the first '*'
    return mProb_dict

def all_states_asm(numASM, relation_as,relation_ms_no, allStates, probDict):
    '''given all a_s states and m states, generate a nested dictionary {state a_s:{state m: probability}}'''
    num_a, num_s, num_m = numASM
    allStates_dict = {}
    measZero_dict = measZero_all(numASM, relation_ms_no, allStates, probDict)
    # allStates = all_states_as(num_a, num_s, relation_as, a_list, s_list, teamTimeID)

    # for state in allStates:
    #     mProb_dict = mProb_all(numASM, relation_as, state, measZero_dict, probDict)
    #     state_as = tuple(state.flatten())
    #     allStates_dict[state_as] = mProb_dict
    # print(probDict)

    # for p in list(probDict.keys()):
    #     exec(p + '=' + str(probDict[p][0]))

    allStates_new = []
    for state in allStates:
        mProb_dict = mProb_all(numASM, relation_as, state, measZero_dict, probDict)
        state_as = tuple(state.flatten())
        # for val in mProb_dict.values():
        # #     print(val, type(val), eval(val))

        if (1,)*num_m in mProb_dict:
        #     # if mProb_dict[(1,)*num_m] > 0.65:
            allStates_dict[state_as] = mProb_dict
            allStates_new.append(state)
        # allStates_dict[state_as] = mProb_dict
        # allStates_new.append(state)
    return allStates_new, allStates_dict

 ###############################################################
 ################## FUNCTIONS FOR PRISM SYNTAX ################# 
 ###############################################################

def names_as(numASM, row_prefix, col_prefix, relation_as): 
    '''outputs list of all agent and sensor state names'''
    num_a, num_s, num_m = numASM
    allStates = [] 
    for i in range(num_a): 
        for j in range(num_s): 
            if relation_as[i][j]:
                state = row_prefix + str(i+1) + "_" + col_prefix + str(j+1) 
                allStates.append(state)
            else:
                allStates.append('NaN') 
    return allStates 

def names_m(num_m, m_prefix): 
    '''outputs list of all measurement names'''
    allStates = [] 
    for i in range(num_m): 
        state = m_prefix + str(i+1)
        allStates.append(state)          
    return allStates 

def init_states(numASM, prefixList, relation_as, a_list, s_list, teamTime, pathToDict, t):
    ''' string of initialized states, assuming we always initialize with everything = 0 (all m_i = 1)'''

    # find which sensors are initially visible
    num_a, num_s, num_m = numASM
    row_prefix, col_prefix, m_prefix = prefixList

    vis_list = []
    for a in list(teamTime.keys()):
        for s in list(teamTime[a].keys()):
            if teamTime[a][s][0][0] == 0:      # if first element of time bounds = 0 (visible at beginning)
                vis = find_id(s, pathToDict, col_prefix, sensor = True)
                visIdx = s_list.index(vis)+1
                agent = find_id(a, pathToDict, row_prefix)
                agentIdx = a_list.index(agent)+1
                vis_list.append(row_prefix + str(agentIdx) + '_'+col_prefix + str(visIdx))

    states_as = names_as(numASM, row_prefix, col_prefix,relation_as)
    states_as = list(filter(lambda a: a != 'NaN', states_as))
    states_m = names_m(num_m, m_prefix)

    init_str = ""

    # set everything other than states with all visible sensors to 0
    for s in range(len(states_as)):
        if states_as[s] not in vis_list:
            initval = 0
        else:
            initval = 0 # 1

        init_str += states_as[s] + ": [0..1] init " + str(initval) + "; \n" 

    for m in range(len(states_m)):
        init_str += states_m[m] + ": [0..1] init 1; \n"    # assuming we always start with measurements = 1
    init_str += 't: ['+str(t)+'..finalTime] init ' + str(t) + '; \n'
    # init_str += 'numA: [0..'+ str(num_a) + '] init 0; \n'
    return init_str

def current2str_as(num_a, num_s, current_as, row_prefix, col_prefix, relation_as):
    '''returns a current a_s states in syntax suitable for PRISM
    Example: ((a1_s1 = 1) & (a1_s2 = 0) & (a1_s3 = 0) & (a2_s1 = 0) & (a2_s2 = 0) & (a2_s3 = 0))
    NOT SURE IF I NEED THIS FUNCTION (CAN I JUST HAVE "TRUE"?)'''
    num_a, num_s, num_m = numASM
    all_str = ""
    for a in range(num_a):
        for s in range(num_s):
            val = str(current_as[a][s])
            states = names_as(numASM, row_prefix, col_prefix, relation_as)
            states = np.reshape(states, (num_a, num_s))
            if states[a][s] != 'NaN':
                assignment = "(" + states[a][s] + " = " + val + ")"
                all_str +=assignment

            if a == (num_a-1) and s == (num_s-1):
                break
            else:
                all_str += " & "
    all_str = "(" + all_str + ")"
    return all_str

def allCurrent2str_as(num_a, num_s, current_as, row_prefix, col_prefix,relation_as):
    '''returns all current a_s states in syntax suitable for PRISM
    Example: ((a1_s1 = 1) & (a1_s2 = 0) & (a1_s3 = 0) & (a2_s1 = 0) & (a2_s2 = 0) & (a2_s3 = 0))
             | ((a1_s1 = 1) & (a1_s2 = 0) & (a1_s3 = 0) & (a2_s1 = 0) & (a2_s2 = 0) & (a2_s3 = 1)) 
             | ...
    NOT SURE IF I NEED THIS FUNCTION (CAN I JUST HAVE "TRUE"?)'''
    allStates = all_states_as(num_a, num_s, relation_as, a_list, s_list, teamTimeID)
    state_str = ""
    for state in range(len(allStates)):
        assignment = current2str_as(num_a, num_s, allStates[state], row_prefix, col_prefix)
        state_str += assignment
        if state == len(allStates)-1:
            break
        else:
            state_str += "\n | "
    return state_str

def next2str_as(numASM, current_as, row_prefix, col_prefix, relation_as):
    '''returns the next a_s states in syntax suitable for PRISM
       (same as current2str_as but add apostrophes to each state)'''
    num_a, num_s, num_m = numASM
    all_str = ""
    for a in range(num_a):
        for s in range(num_s):
            val = str(int(current_as[a][s]))
            states = names_as(numASM, row_prefix, col_prefix, relation_as)
            states = np.reshape(states, (num_a, num_s))
            if states[a][s] != 'NaN':
                assignment = "(" + states[a][s] + "' = " + val + ")"
                all_str += assignment
                all_str += " & "
    return all_str[:-3]    # remove last ' & '

def next2str_m(num_m, m_prefix):
    '''returns a list of the current m states in syntax suitable for PRISM
       output: {(0,0): '(m1' = 0) & (m2' = 0)'}
    '''
    allcombos_m = [np.reshape(np.array(i), (1, num_m)) for i in itertools.product([0, 1], repeat = 1*num_m)]
    names = names_m(num_m, m_prefix)
    m_string = ""
    m_dict = {}

    for c in range(len(allcombos_m)):
        m_string = ""
        for m in range(num_m):
            m_string += "("
            if allcombos_m[c][0][m]:
                m_string += str(names[m]) + "' = " + str(1)
            else:
                m_string += str(names[m]) + "' = " + str(0)
            
            if m == (num_m-1):
                m_string += ")"
            else:
                m_string += ") & "
        m_dict[tuple(allcombos_m[c][0])] = m_string
                     
    return m_dict


def allStates_next2str(numASM, a_list, s_list, relation_as,relation_ms_no, row_prefix, col_prefix, teamTimeID, probDict):
    ''' Generates entire string for next states (the stuff after the arrow ->)
    Example: 
    0.3: (a1_s1' = 0) & (a1_s2' = 0) & (a1_s3' = 0) & (a2_s1' = 0) & (a2_s2' = 0) & (a2_s3' = 1) & (m1' = 0) & (m2' = 0)
  + 0.0: (a1_s1' = 0) & (a1_s2' = 0) & (a1_s3' = 0) & (a2_s1' = 0) & (a2_s2' = 0) & (a2_s3' = 1) & (m1' = 0) & (m2' = 1)
    . . .

    '''
    num_a, num_s, num_m = numASM
    allStates_dict = all_states_asm(numASM, a_list, s_list, relation_as,relation_ms_no, teamTimeID, probDict)
    # {state a_s:{state m: probability}}

    m_array = next2str_m (num_m, m_prefix)
    count = 0 # sanity check
    prob_count = 0 # sanity check
    all_str = ""
    for state in allStates_dict.keys():
        next_as = next2str_as(numASM, np.reshape(state, (num_a, num_s)), row_prefix, col_prefix, relation_as)
        for m in allStates_dict[state].keys():
            #print('here', m)
            prob = allStates_dict[state][m]
            str_state = str(prob)+ ": " + next_as + " & " + str(m_array[m])
            all_str += str_state 

            count +=1
            if count == len(allStates_dict.keys()) * num_m**2:  # if reached the last state
                all_str += ";"
            else:
                all_str += "\n + "
            prob_count +=prob # should equal 16 BUT IT REALLY SHOULD EQUAL TO ONE ??
                    #-> need probability of transitioning a_s matrices (probability of an agent turning on a sensor)
    return count, prob_count, all_str

def init_actions(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, pathToDict):
    '''string of initialized action states, which are "A1S1" or "A1S1_A2S2", etc.'''
    actionStr, timeDict = action2str(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, pathToDict, action = False)
    init_str = ""
    for a in actionStr:
        init_str += a + ": [0..1] init 0; \n" 
    init_str += 't: [0..finalTime] init 0; \n'
    return init_str + '\n' 

def line_with_string(string, fp):
    ''' find line that contains a substring (assumes the substring only appears once)
    '''
    for line in fp:
        if string in line:
            return line

def sensorTimeBounds(teamTime, agent, sensor):
    ''' for each agent's sensor, construct visibility time constraints in PRISM syntax
    example:
    (((t >= 1) & t <= 5)) | ((t >= 10) & t <= 20))) & t < totalTime
    '''
    timeStr = ''
    # for s in team[agent].keys():
    for bounds in teamTime[agent][sensor]:      # for each time bound
        timeStr += '((t >= ' + str(bounds[0]) + ') & (t < ' + str(bounds[1]) + ')) | '


    timeStr = timeStr[:-3]    # remove extra ' | '
    return timeStr

# def sensorTimeBounds_single(teamTime, agent, sensor):
#     ''' for each agent's sensor, construct visibility time constraints in PRISM syntax
#     example:
#     (((t >= 1) & t <= 5)) | ((t >= 10) & t <= 20))) & t < totalTime

#     for parallelized method, we only need t >= timestep & t < totalTime
#     '''
#     timeStr = ''
#     # for s in team[agent].keys():
#     for bounds in teamTime[agent][sensor]:      # for each time bound
#         if bounds[0] == t:
#             timeStr += '(t>= '
#             break
#     #     timeStr += '((t >= ' + str(bounds[0]) + ') & (t < ' + str(bounds[1]) + ')) | '


#     # timeStr = timeStr[:-3]    # remove extra ' | '
#     return timeStr

def action2str(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, pathToDict, action = True, stateDict = False):
    ''' write actions for each transition to a state. returns a list: ['TO_<STATE1>', 'TO_STATE2']
    where <state1> could be something like "A1S1" for [[1 0 0 ], [0 0 0]] or "A1S1_A2S2" for [[1 0 0 ], [0 1 0]]
    If action = false, then we remove the "TO_" from each state
    If time = True, then we output the time bounds for each state: {'A1S1': '(((t >= 1) & t <= 5)) | ((t >= 10) & t <= 20)))'}
    '''
    # allStates = all_states_as(num_a, num_s, relation_as, a_list, s_list, teamTimeID)
    actions = []
    timeDict = {}
    act2matDict = {}

    # print(allStates)
    for state in allStates:
        act = ""
        if not np.count_nonzero(state) and not action:     # if states all = 0
            act += "NOAGENTS"
            timeDict[act] = ''
        elif not np.count_nonzero(state) and action:
            act += "[TO_NOAGENTS]"
            timeDict[act] = ''
        else:
            timeStr= ''
            for row in range(num_a):
                for col in range(num_s):
                    if state[row][col]:
                        agent = str(row+1)
                        sensor = str(col+1)
                        stateStr = (row_prefix + agent).capitalize() + (col_prefix + sensor).capitalize()
                        if act == "":           # if first element
                            if action:          # if we want actions 
                                act += "[TO_" + stateStr
                            else:
                                act += stateStr
                        else:
                            act += "_" + stateStr

                        # convert a1 -> a1512
                        agentID = a_list[int(agent)-1]
                        sensorID = s_list[int(sensor)-1]
                        sID, sIdx = sensorID.split('__')
                        # convert ids to agent and sensor names
                        # pathToDict = '../KG_examples/outputs_KGMLN_1/output.dict'
                        agent = find_name(agentID, pathToDict, 'Platform')
                        sensor = find_name(sID, pathToDict, 'Sensor') + '__'+ sIdx

                        if timeStr == '':
                             timeStr += sensorTimeBounds(teamTime, agent, sensor)
                        # find time bounds (need for unparallelized version)
                        # timeStr += '(' + sensorTimeBounds(teamTime, agent, sensor) + ') & '
            if action:
                act = act + ']'
            # timeDict[act] = timeStr[:-3] # remove last ' & ' (need for unparallelized version)
            timeDict[act] = timeStr
            act2matDict[tuple(state.flatten())] = act

        actions.append(act)

    if stateDict:
        return act2matDict

    return actions, timeDict
    # if time:
    #     return timeDict
    # else:
    #     return actions


def init_vis(num_a, num_s, teamTime,relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict):
    ''' find all states that can possibily be 1 at initial state
    '''
    initStates = []
    # find which sensors are initially visible
    vis_list = []
    for a in list(teamTime.keys()):
        for s in list(teamTime[a].keys()):
            if teamTime[a][s][0][0] == 0:      # if first element of time bounds = 0 (visible at beginning)
                vis = find_id(s, pathToDict, col_prefix, sensor = True)
                visIdx = s_list.index(vis)+1
                agent = find_id(a, pathToDict, row_prefix)
                agentIdx = a_list.index(agent)+1
                vis_list.append(row_prefix + str(agentIdx) + '_'+col_prefix + str(visIdx))

    states_as = names_as(num_a, num_s, row_prefix, col_prefix,relation_as)
    states_as = list(filter(lambda a: a != 'NaN', states_as))

    init_str = ""

    # set everything other than states with all visible sensors to 0
    for s in range(len(states_as)):
        if states_as[s] in vis_list:
            initStates.append(states_as[s])

        # init_str += states_as[s] + ": [0..1] init " + str(initval) + "; \n" 
    # print(initStates)
 
    if initStates == []:
        raise ValueError ("The team fails at the initial timestep.")
    return initStates

def init_allStates(num_a, num_s, teamTime,teamTimeID,relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict):
    '''
    find all possible combinations for initial timestep
    returns list of as_matrix arrays
    '''
    # actionDict = action2str(num_a, num_s, teamTime,teamTimeID,relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict, action = False, stateDict = True)
    init_states = init_vis(num_a, num_s, teamTime,relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict)
    
    states_array = []
    init_statesMat = []
    lst_a = []

    # find matrices for each init_states 
    for i in init_states:
        action = i.replace('_','').upper()
        actionMat = action2state(num_a, num_s, row_prefix, col_prefix, action)
        init_statesMat.append(actionMat)

    # sum all these matrices (essentially the same as relation_as but only for initial timestep)
    allOn = sum(init_statesMat)

    # assemble list of indices of which rows and cols are 1
    rows, cols = np.where(allOn == 1)    

    for i in range(len(rows)):
        lst_a.append([rows[i],cols[i]])

    # combination of all the indices
    combs = []
    lst = range(len(lst_a))
    for i in range(1, len(lst_a)+1):
        els = [list(x) for x in itertools.combinations(lst_a, i)]
        combs.extend(els)

    # for each combination, set indices in that combination to be 1
    for c in range(len(combs)):
        state = np.zeros((num_a, num_s))
        for j in range(len(combs[c])):
            # print('idx',combs[c][j])
            state[combs[c][j][0]][combs[c][j][1]] = 1
        states_array.append(state)
    # print(len(states_array))
    return states_array

def initTransition(numASM, teamTime,teamTimeID, allStates, allStates_dict, relation_as, prefixList, a_list, s_list, probDict, pathToDict):
    '''
    [initial]    t = 0 -> p1: (a1_s1 = 1) & (a2_s1 = 1) & (t' = t+1)
                   + ...
    '''
    num_a, num_s, num_m = numASM
    row_prefix, col_prefix, m_prefix = prefixList

    states = init_allStates(num_a, num_s, teamTime,teamTimeID,relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict)
    actionDict = action2str(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, pathToDict, action = False, stateDict = True)

    mDict= next2str_m(num_m, m_prefix)
    mkey = tuple(1 for i in range(num_m))     # all m's are on
    mStr = mDict[mkey]

    beforeArrow = '[initial]    t = 0 -> \n'
    afterArrow = ' '*8

    # allStatesDict = all_states_asm(numASM, a_list, s_list, relation_as,relation_ms_no, teamTimeID, probDict)
    
    # calculate sum of all probabilites to divide existing probablities by (ensures probs sum to 1)
    probDen = '( '
    for state in states:
        prob = allStates_dict[tuple(state.flatten())][mkey]
        if prob != '0':
            probDen+= prob + ' + '
    probDen = probDen[:-2] + ')'
    numAgents = {}
    # construct afterArrow string
    for state in states:
        prob = allStates_dict[tuple(state.flatten())][mkey]
        if prob != '0':
            next_as = next2str_as(numASM, state, row_prefix, col_prefix, relation_as)
            action = actionDict[tuple(state.flatten())]

            # calculate number of agents for each state
            num = len(np.where(state.any(axis=1))[0])

            afterArrow += '( ' + prob + ' ) / ' + probDen + ': ' + next_as + ' & '+ mStr +" & (numA' = "+ str(num) +')' + " & (t' = t+1)" +  ' \n'+' '*8 + '+ '

            numAgents['[TO_'+action+']'] = num
    afterArrow = afterArrow[:-3] + ';'

    return beforeArrow + afterArrow

def constructAction(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, pathToDict): 
    '''example:      [
     [up]    (((t >= 1) & t <= 5)) | ((t >= 10) & t <= 20))) & t < totalTime       -> 1:(u'=1) & (t' = t+1);
     [up]    d=1 & (((t >= 1) & t <= 5)) | ((t >= 10) & t <= 20))) & t < totalTime -> 1:(d'=0) & (t' = t+1);
     [up]    l=1 " "                                                               -> 1:(l'=0) & (t' = t+1);
     [up]    r=1 " "                                                               -> 1:(r'=0) & (t' = t+1);'''
    
    all_actionStr = ""
    actions, statesDict = action2str(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, pathToDict)
    # statesDict = action2str(num_a, num_s, teamTime, relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict, action = False, time = True)
    states = list(statesDict.keys())
    nextT = " & (t' = t+1); \n"
    for a in range(len(actions)):
        for nota in range(len(actions)):
            if actions[a] == actions[nota]:
                if actions[a] == '[TO_NOAGENTS]':
                    finalT = "t < finalTime "      
                else:
                    finalT = " & t < finalTime "
                all_actionStr += actions[a] + "    " + statesDict[states[a]] + finalT + \
                                 "\n" + " "*len(actions[a]) + " -> 1: (" + states[nota]+"' = 1)" + nextT
            else:
                if actions[a] == '[TO_NOAGENTS]':
                   finalT = "t < finalTime "  
                else:
                    finalT = " & t < finalTime "
                all_actionStr += actions[a] + "    " + states[nota] + " = 1 & " + statesDict[states[a]] + finalT + \
                                "\n" + " "*len(actions[a]) + " -> 1: (" + states[nota]+"' = 0)"  + nextT
        all_actionStr += "\n"
    return all_actionStr

def action2state(num_a, num_s, row_prefix, col_prefix, action):
    ''' given an action, generate corresponding state
        Ex: input = "A1S1_A2S2", output = np.array([[1, 0, 0], [0,1,0]])'''
    
    # step 1: convert "A1S1_A2S2" into [[1, 1], [2, 2]]
    elem_list = []
    act = ""
    state_list = []
    idx = 0
    if action == "[TO_NOAGENTS]" or action == "[NOAGENTS]":
        return np.zeros((num_a, num_s))

    action = action.lower()

    for char in action:
        idx +=1
        if char.isdigit():
            act += char
        if char == col_prefix:   # if got all the digits of agent
            if row_prefix == "":       # if there are no agents (e.g. just 'S1_S2')
                elem_list.append(1)
            else:
                elem_list.append(int(act))
            act = ""
        if char == "_" or idx == len(action):    # if at the end of one state (got all the digits of sensor)
            elem_list.append(int(act))
            state_list.append(elem_list)

            elem_list = []
            act = ""
    
    # step 2: take each list within the list and use them as indices for where to place ones

    state = np.zeros((num_a, num_s))
    for s in state_list:
        state[s[0]-1][s[1]-1] = 1

    return state
        
def nextStatesFromAction(actions, timeDict, allStates_dict, numASM, relation_as, prefixList, probDict, pathToDict):
    '''based on the action given, generate transition probabilities (aka generate everything after the "->" 
    outputs {["TO_<STATE>"]}: "<P:states>"}

    INPUTS: 
    actions, timeDict (from function action2str)
    allStates_dict (from function all_states_asm)

    '''
    # allStates_dict = all_states_asm(numASM, a_list, s_list, relation_as,relation_ms_no, teamTimeID, probDict)
    # actions, timeDict = action2str(num_a, num_s, teamTime, teamTimeID,relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict)
    # # actionStates = action2str(num_a, num_s, teamTime, relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict, action = False)
    # print('HERE1')
    num_a, num_s, num_m = numASM
    row_prefix, col_prefix, m_prefix = prefixList

    actionStates = [s.replace('TO_','') for s in actions] 
    t = time.time()
    # {state a_s:{state m: probability}}
    m_array = next2str_m (num_m, m_prefix)
    count = 0
    trans_dict = {}
    for act in range(len(actions)):
        trans_str = ""
        state = action2state(num_a, num_s, row_prefix, col_prefix, actionStates[act])
        next_as = next2str_as(numASM, state, row_prefix, col_prefix, relation_as)
        for m in allStates_dict[tuple(state.flatten())].keys():
            prob = allStates_dict[tuple(state.flatten())][m] 
            # if count != 0:
            #     trans_str += "\n        + "
            if prob != '0':      # ignore 0 probability transitions
                str_state = str(prob)+ ": " + next_as + " & " + str(m_array[m]) + " &  (t'= t+1) \n"
                trans_str += str_state + "        + "
                count += 1
        trans_dict[actions[act]] = trans_str[:-11] + ';' + '\n'
        # print(actions[act])
        count = 0
    elapsed = time.time() - t
    # print('HERE2')
    return trans_dict

def entireLine4state(actions, timeDict, allStates_dict, numASM,prefixList, a_list, s_list, relation_as, probDict, pathToDict):     # needs a better name
    ''' outputs entire line of agent transition: 
    (a1_s1 = 0 & ...) | (a1_s1 = 1 & ...) | ... -> (a1_s1' = 0 & ...) ...
    '''
    # beforeArrow = allCurrent2str_as(num_a, num_s, current_as, row_prefix, col_prefix,relation_as)

    # actions, timeDict = action2str(num_a, num_s, teamTime,teamTimeID,relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict, action = True)
    num_a, num_s, num_m = numASM
    row_prefix, col_prefix, m_prefix = prefixList

    trans_dict = nextStatesFromAction(actions, timeDict, allStates_dict, numASM, relation_as, prefixList, probDict, pathToDict)

    all_str =""

    for action in trans_dict.keys():
        beforeArrow = timeDict[action]
        if beforeArrow == '':
            finalT = "t < finalTime "      
        else:
            finalT = " & t < finalTime "
        beforeArrow +=finalT

        all_str += "\n"+action + "   " + beforeArrow + " -> \n        " + trans_dict[action]

    return all_str

def probConstants(probDict):
    '''  create string that looks like:
    const double P1 = 0.9;
    const double P2 = 0.8;
    const double P3 = 0.7;

    '''
    probStr = ''
    for p in list(probDict.keys()):
        probStr += 'const double ' + p + ' = ' + str(probDict[p][0]) + '; \n'
    return probStr

def timeConstants(missionLength):
    ''' create string that looks like:
    const int finalTime = 30;
    '''
    return 'const int finalTime = ' + str(missionLength) + '; \n'

def findNumAgents(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, pathToDict):
    ''' for a given action ('A1S1_A1S2_A2S2'), determine number of agents
    outputs dictionary {action: <num of sats>}
    '''
    allActions, timeDict = action2str(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, pathToDict, action = False)
    # allStates = all_states_as(num_a, num_s, relation_as)

    numAgents = {}
    for action in allActions:
        if action == 'NOAGENTS':
            num = 0
        else:
            alist = set()
            sensors = action.split('_')
            for a in sensors:
                agent = a.split('S')[0]
                alist.add(agent)
            num = len(alist)
        numAgents['[TO_'+action+']'] = num
    return numAgents

def initialCost(num_a, num_s, teamTime,teamTimeID,relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict):
    ''' rewards for initial timestep
    '''
    rewardStr = ''
    states = init_allStates(num_a, num_s, teamTime,teamTimeID,relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict)
    for state in states:
        # calculate number of agents for each state
        num = len(np.where(state.any(axis=1))[0])
        rewardStr += '[initial]    numA = ' + str(num) + ' : numA; \n'
    return rewardStr

def construct_num_agents_cost(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, m_list, pathToDict, moduleName):
    ''' create rewards module for minimizing number of satellites
    ex:
    [TO_A1S1]    allM : 1;
    '''
    # costModule = '\n formula allM = ('
    # for m in m_list:
    #     costModule += m + '=1 & '
    # costModule = costModule[:-3] + '); \n '

    costModule = '\n\n rewards "'+moduleName+'" \n'
    # costModule += initialCost(num_a, num_s, teamTime,teamTimeID,relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict)

    acts, statesDict = action2str(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, pathToDict, action = False)
    numAgentsDict = findNumAgents(num_a, num_s, teamTime, allStates, row_prefix, col_prefix, a_list, s_list, pathToDict)
    actions = list(statesDict.keys())

    for act in actions:
        if statesDict[act] == '':
            time = "t < finalTime "
        else:
            time = statesDict[act] + " | t < finalTime "
        time = ''
        # costModule += '[TO_'+act+']' + '    ' +'allM' + '\n        : 1' + '; \n'
        costModule += '[TO_'+act+']' + '    ' + 'true '+time+'' + ': ' + str(numAgentsDict['[TO_'+act+']']) + '; \n'
    return costModule + 'endrewards \n \n'

def construct_kg_module(actions, timeDict, allStates_dict, numASM, prefixList, a_list, s_list, teamTime, relation_as, relation_ms,probDict,pathToDict,missionLength, t):
    num_a, num_s, num_m = numASM
    row_prefix, col_prefix, m_prefix = prefixList

    # add comment about relationship matrices
    comments = "// agent-sensor relationship matrix: " + str(relation_as.tolist()) + "\n// measurement-sensor matrix: " + str(relation_ms.tolist()) +"\n \n"
    const = probConstants(probDict) + timeConstants(missionLength)
    states0 = init_states(numASM, prefixList,relation_as, a_list, s_list, teamTime, pathToDict, t)

    # initTrans = initTransition(numASM, teamTime,teamTimeID,relation_as, relation_ms_no, prefixList, a_list, s_list, probDict, pathToDict)
    kg_module = comments + "mdp \n \n " + const + "\n module KG \n\n" + states0 + "\n" + entireLine4state(actions, timeDict, allStates_dict, numASM, prefixList, a_list, s_list, relation_as, probDict, pathToDict) + '\n endmodule'
    return kg_module + '\n'

def constructActionsModule(num_a, num_s, teamTime, teamTimeID, relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict):
    actions0 = init_actions(num_a, num_s, teamTime, teamTimeID, relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict)
    actions_module = "\n module actions \n \n" + actions0 + constructAction(num_a, num_s, teamTime, teamTimeID, relation_as, row_prefix, col_prefix, a_list, s_list, pathToDict) + '\n endmodule'
    return actions_module 

def constructEachPModule(numASM,a_list, s_list,teamTime, teamTimeID, relation_as, relation_ms_no,prefixList, probDict, pathToDict):
    ''' each transition should be > 0.9
    '''
    trans_dict = nextStatesFromAction(actions, timeDict, allStates_dict, numASM, relation_as, prefixList, probDict, pathToDict)
    timeR = 'rewards "eachP"'
    for action in trans_dict.keys():
        # if c ==30:
        subs = "(m1' = 1) & (m2' = 1) & (m3' = 1) & (m4' = 1)"
        res = [i for i in trans_dict[action].split("&  (t'= t+1)") if subs in i] 
        if res != []:
            res2 = res[0].split(':')[0]
            idx = res2.find('(')
            res2 = res2[idx:]
            timeR += '\n' + action + '    allM & ' + res2 + ' > 0.9: 1;'
            # print(trans_dict[action].split("&  (t'= t+1)"))
    timeR += '\n endrewards \n \n'
    return timeR

def replace_idx(a_list, s_list, m_list, kg_module, reward_module):
    # FIGURE OUT HOW TO REPLACE INDICES WITH A LIST OF REWARD MODULES *****
    # replace indices with indices from KG (ex: a1 -> a980)
    for i in range(len(a_list)):
        kg_module = kg_module.replace("a" + str(i+1) +"_", a_list[i]+"_")
        kg_module = kg_module.replace("A" + str(i+1) + "S", "A" + a_list[i][1:] + "S")
        reward_module = reward_module.replace("A" + str(i+1) + "S", "A" + a_list[i][1:] + "S")

    for i in range(len(s_list)):
        kg_module = kg_module.replace("s" + str(i+1) +"'", s_list[i]+"'")
        kg_module = kg_module.replace("s" + str(i+1) +":", s_list[i]+":")
        kg_module = kg_module.replace("S" + str(i+1) +"_", "S" + s_list[i][1:] + "_")
        kg_module = kg_module.replace("S" + str(i+1) +"]", "S" + s_list[i][1:] + "]")

        reward_module = reward_module.replace("S" + str(i+1) +"_", "S" + s_list[i][1:] + "_")
        reward_module = reward_module.replace("S" + str(i+1) + " =", "S" + s_list[i][1:] + " =")
        reward_module = reward_module.replace("S" + str(i+1) +":", "S" + s_list[i][1:] + ":")
        reward_module = reward_module.replace("S" + str(i+1) +"'", "S" + s_list[i][1:] + "'")
        reward_module = reward_module.replace("S" + str(i+1) +"]", "S" + s_list[i][1:] + "]")
        
    for i in range(len(m_list)):
        kg_module = kg_module.replace("m" + str(i+1) + ":", m_list[i] + ":")
        kg_module = kg_module.replace("m" + str(i+1) + "'", m_list[i] + "'")

    allM = '\n formula allM = ('
    for m in m_list:
        allM += m + '=1 & '
    allM = allM[:-3] + '); \n '

    kg_module = allM + kg_module
    return kg_module, reward_module

def save_mdp_file(modules, mdp_file):
    with open(mdp_file,'w') as out:
        for m in modules:
            out.writelines(m)

    # text_file = open(mdpFile, "w")
    # text_file.write(' '.join(modules))
    # text_file.close()


