#!/usr/bin/env python

# PARSE SYNTHESIZED PATH GENERATED FROM PRISM

from extractJSON import find_name
import numpy as np
import glob
import main
import matplotlib.pyplot as plt 
import itertools
import os
import random
import pareto

def line_w_string(string, fp):
    ''' find all lines that start with a substring and outputs as list
    '''
    newstring = []
    for line in fp:
        if line.startswith(string):
            newstring.append(line.rstrip())
    return newstring

def find_maxP(lineList):
    ''' given list of lines, find maximum probability and corresponding action
    '''
    maxP = 0
    action = 'N/A'
    for v in lineList:
        col = v.split(' ')
        if float(col[3]) > maxP:
            maxP = float(col[3])
            nextState = int(col[2])
            if len(col) > 4:
                action = col[4]
            else:
                action = 'N/A'
    return maxP, action, nextState    

def generate_path(adv_file_path, sta_file_path): 
    ''' 
    given an adversary file, output:
        pathStates         the adversary {timestep: [set of agents 'a_ID']}
        actions         actions taken in adversary
        allP              list of probabilities at each timestep (len(allP) = # of timesteps)
    '''

    # extract states from adv.tra file
    with open(adv_file_path) as file:
        # assuming 0 is the initial state
        lines = file.readlines()
        path = [0]
        idx = 0
        action = ''
        totalP = 1
        allP = []         
        actions = []
        # find path of states 
        while action != 'N/A':
            lineList = line_w_string(str(path[idx]) + ' 0 ', lines)
            maxP, action, nextState = find_maxP(lineList)
            if action != 'N/A':
                path.append(nextState)
                actions.append(action)
            idx += 1
            totalP *= maxP
            allP.append(maxP)
        path.pop(0)
    # convert states in adv.tra into agents at each time step
    pathStates = {}
    with open(sta_file_path) as file:
        lines = file.readlines()
        stateList = lines[0].split(',')
        stateList = [ x for x in stateList if x[0] == 'a' ]    # only care about agent-sensor states 
        
        for stateIdx in path:
            lineState = line_w_string(str(stateIdx)+ ':', lines)[0]
            as_states = lineState.split(':')[1][3:(3+2*len(stateList)-1)]   # only care about agent-sensor states
            t = int(lineState.split(':')[1][-2])
            as_states = as_states.split(',')

            # for each timestep, determine which agents are being used
            eachTime = set()
            for s in range(len(as_states)):
                if as_states[s] != '0':
                    # agent = stateList[s].split('_')[0]
                    if len(stateList) != 0:
                        agent = stateList[s]
                        eachTime.add(agent)

            pathStates[t] = eachTime
    return pathStates, actions, allP

def convert_agents(actions, inv_entity_dict, pathStates):
    '''
    convert actions in pathStates dictionary into agent names 
    '''
    # t = 1
    for act in actions:
        agents = set()
        act1 = act.split('_')
        act_new = []
        for a in act1:
            if a != '':
                if a[0] == 'A':
                    new = a.split('S')
                    new = [idx for idx in new if idx[0] == 'A']
                    # print(new)
                    agent = find_name(new[0][1:], inv_entity_dict, 'Platform')
                    # print(agent)
                    # act_new += new
                    agents.add(agent)
        pathStates = agents
        # t += 1
    return pathStates

def numA(action):
    ''' determine number of agents used in an action.

    input: TO_A472S1606__2_A652S1126__1
    output: 2
    '''
    if action == 'NOAGENTS':
        num = 0
    else:
        alist = set()
        sensors = action.split('_')
        for a in sensors:
            if a != '':
                if a[0] == 'A':
                    agent = a.split('S')[0]
                    alist.add(agent)
        num = len(alist)
    return num

def calculate_reward(actions, allP):
    ''' calculate expected reward given series of actions
    '''
    V = 0
    Pprev =allP[0]
    # for act in range(len(allP)):
    for act in range(len(actions)):
        R = numA(actions[act])
        # R=actions[act]
        Pprev = np.prod(allP[0:act])
        V = V + R*Pprev
        Pprev = allP[act]
    return V

def calculate_reward2(actions, allP):
    ''' calculate expected reward given series of rewards
    '''
    V = 0
    Pprev =allP[0]
    for act in range(len(allP)):
        R=actions[act]
        Pprev = np.prod(allP[0:act])
        V = V + R*Pprev
        Pprev = allP[act]
    return V

def fill_in_rewards(time_dict):
    # add rewards if that reward point doesn't exist
    new_dict = {}
    for i in range(len(time_dict.keys())):
        # print(list(result[i]))
        # print(round(list(result[i]),5))
        adv_list = []
        for pt in range(len(time_dict[i])):
            if not np.any(time_dict[i][pt]) or time_dict[i][pt][1] == -0.0:   # if result[i] = (0.0,0.0)
                adv_list = [(0.0, 0.0)]
            else:

                adv_list = sorted(list(time_dict[i]),key=lambda x:x[1])    # sorted by rewards

                adv_list = [(num[0],round(num[1], 5)) for num in adv_list]
                # modify so that if one unit of reward is missing in a timestep, add missing numA and keep probability same as numA-1
                r = int(round(adv_list[0][1], 5))
                idx = 1

                while r < adv_list[-1][1]:
                    prev_reward = adv_list[idx-1][1]
                    if adv_list[idx][1] != prev_reward+1:    # missing reward values
                        prev_prob = adv_list[idx-1][0]
                        adv_list.insert(idx, (prev_prob,prev_reward+1))
                    else:
                        r+=1
                        idx +=1
                adv_list.insert(0, (0.0,0.0))
        new_dict[i] = adv_list         
    return new_dict


def parse_adv_main(inv_entity_dict, timestep_path):
    teams = {}

    num = len(glob.glob1(timestep_path,"*.tra"))     # number of adversary files
    for i in range(num):
        # print('\nadv' + str(i+1) + '.tra')
        adv_file_path = timestep_path + '/adv' + str(i+1)+'.tra'
        sta_file_path = timestep_path + '/prod.sta'
        pathStates, actions, allP = (generate_path(adv_file_path,sta_file_path))
        pathStates = list(convert_agents(actions, inv_entity_dict, pathStates))
        # print('Path: ',convert_agents(actions, inv_entity_dict, pathStates))
        prob = np.prod(allP)
        R = calculate_reward(actions, allP)
        # print('Probability, Reward: ', np.prod(allP), calculate_reward(actions, allP),'\n')

        # don't include duplicate adversaries
        if (prob, R) not in teams.keys():
            # teams[(prob, R)] = {'adv' + str(i+1) + '.tra' : pathStates}
            teams[(prob, R)] = pathStates
    return teams

def find_optimal_teams(PRsorted_r, PRtot_team):
        ''' given all possible coordinates, find the optimal coordinates and corresponding team
        outputs:
        allptsP         probabilities (y-coord)
        allptsR         rewards       (x-coord)
        optimal_teams   dictionary of teams {timestep: [satellites]}
        '''
        allptsP = []
        allptsR = []
        optimal_teams = {}
        # find optimal points
        for pt in PRsorted_r:
            xcoord = round(pt[1],5)
            ycoord = pt[0]

            if len(allptsP)== 0 or xcoord != allptsR[-1]:     # if point's reward val is not already included
                allptsP.append(ycoord)
                allptsR.append(xcoord)
                # generate corresponding team
                if pt[0] != 0.0:
    
                    optimal_teams[(ycoord,xcoord)] = PRtot_team[(ycoord,xcoord)]
            else:
                # if len(allptsP)!= 0:
                if xcoord == allptsR[-1] and ycoord >= allptsP[-1]:    # if new point with same reward has higher probability
                    optimal_teams.pop((allptsP[-1], allptsR[-1]), None)
                    allptsP.pop()
                    allptsR.pop()

                    allptsR.append(xcoord)
                    allptsP.append(ycoord)
                    optimal_teams[(ycoord,xcoord)] = PRtot_team[(ycoord,xcoord)]

        # find pareto (set prob = prev prob if prob < prev prob)
        pareto_P = allptsP.copy()
        pareto_R = allptsR.copy()

        for p in range(1,len(allptsP)):
            if allptsP[p] < pareto_P[p-1]:   # set current prob to prev prob
                optimal_teams[(pareto_P[p-1], allptsR[p])] = PRtot_team[(allptsP[p-1], allptsR[p-1])]
                if (allptsP[p], allptsR[p]) in optimal_teams.keys():
                    optimal_teams.pop((allptsP[p], allptsR[p]))

                pareto_P[p] = pareto_P[p-1]
                pareto_R[p] = pareto_R[p]



        return pareto_P, pareto_R, optimal_teams

def pareto_plot_all(result, teams, timestep_dict, showplot = False):
    ''' plot pareto front given parallelized teaming plans
    '''
    # round rewards
    # print(teams)
    for team in teams.keys():
        teams[(team[0], round(team[1], 5))] = teams.pop(team)

    dict_temp = fill_in_rewards(timestep_dict)
    
    # ------ USING VALUES OF RESULTS -------
    # combos = []
    # for i in range(iterations):
    #     combo = []
    #     for j in range(len(result)):
    #         num_pts = len(result[j])-1
    #         idx = random.randint(0, num_pts)
    #         # prob_reward = dict_temp[j][idx]
    #         prob_reward = result[j][idx]
    #         combo.append(prob_reward)
    #     combos.append(combo)
    
    # P = 1
    # V = 0
    # Plist = []
    # Rlist = []
    # for c in range(len(combos)):
    #     for tstep in range(len(combos[c])):
    #         R = combos[c][tstep][1]
    #         V = V + R*P
    #         P *= combos[c][tstep][0]
            
    #     Plist.append(P)
    #     Rlist.append(V)
    # # print(Rlist, Plist)
    # print(len(Rlist))
    # plt.plot(Rlist, Plist, '.',color = 'gray', zorder = 1) 
    # plt.show()


    iterations = 10**5
    combos = []
    for i in range(iterations):
        combo = []
        for j in range(len(result)):
            num_pts = len(dict_temp[j])-1
            idx = random.randint(0, num_pts)
            prob_reward = dict_temp[j][idx]
            combo.append(prob_reward)
        combos.append(combo)
    # with open('combo','w') as file:
    #     file.write(str(combos))

    
    # find all possible (probability, reward) points and corresponding teams
    PRtot = []
    RPtot = []
    rsum=0
    PRtot_team= {}
    for c in range(len(combos)):
        Plist = []
        Rlist = []
        acts = {}
        for n in range(len(combos[c])):    # should equal number of timesteps
            PR_tuple = combos[c][n]
            Plist.append(PR_tuple[0])
            Rlist.append(PR_tuple[1])
            combo_round = tuple(map(lambda x: isinstance(x, float) and round(x, 6) or x, PR_tuple))
            
            if combo_round in teams.keys():     # check if combo_round != a tuple that we added earlier to cover all reward values
                acts[n+1] = teams[combo_round]
            elif combo_round[0] == 0.0:
                acts[n+1] = 'n/a'
            else:
                for next_r in range(int(combo_round[1]), -1, -1):    # find next largest reward with same probability
                    if (combo_round[0], next_r) in teams.keys():
                        acts[n+1] = teams[(combo_round[0], next_r)]
                        break

        r = calculate_reward2(Rlist, Plist)
        r = sum(Rlist)
        p = np.prod(Plist)


        r = round(r,5)
        PRtot.append((p,r))
        RPtot.append((r,p))
        PRtot_team[(p,r)] = acts
    PRsorted = sorted(PRtot, key=lambda x:x[0])

    x = []
    y = []
    for pt in range(len(PRsorted)):
        y.append(PRsorted[pt][0])
        x.append(PRsorted[pt][1])

    plt.plot(x, y, 'o', color = 'gray', label = 'Possible Teams from Pareto Fronts' )


    PRsorted_r = sorted(PRtot, key=lambda x:round(x[1],5))
    allptsP, allptsR, optimal_teams = find_optimal_teams(PRsorted_r, PRtot_team)  

    if showplot:     # generate the pareto front plot
        plt.plot(allptsR,allptsP, 'r.', label = 'Optimal Teams' ,)
        plt.grid(linestyle=':')
        plt.yticks(np.arange(0,1.1, 0.1))
        plt.xticks(np.arange(0,PRsorted_r[-1][1]+1, 2))
        plt.xlabel('Cumulative Number of Satellites') 
        plt.ylabel('Maximum Probability of Mission Success') 
        plt.title('Maximize Probability, Minimize # of Satellites')
        plt.legend()
        plt.legend(loc='upper left', bbox_to_anchor=(0,1))
        plt.show()

    return optimal_teams


def paretoPlot(outputPath):
    ''' plot and save Pareto front
    '''
    paretoPts = main.output_result(outputPath)
    print(paretoPts)
    if len(paretoPts) > 2:    # more than one coordinate
        paretoPts = sorted(paretoPts, key=lambda x:x[0])
    else:
        paretoPts = [paretoPts]
    x = []
    y = []
    for pt in range(len(paretoPts)):
        y.append(paretoPts[pt][0])
        x.append(paretoPts[pt][1])

    # plotting the points 
    plt.plot(x, y, color = 'gray', zorder = 1)  
    plt.scatter(x, y, marker = '.', color = 'blue',label = 'Possible Team Assignments' , zorder = 2) 
    
    plt.xlabel('Cumulative Number of Satellites') 
    plt.ylabel('Maximum Probability of Mission Success') 
    plt.yticks(np.arange(0,1.1, 0.1))
    plt.grid(linestyle=':')
    plt.legend()
    plt.legend(loc='lower right', bbox_to_anchor=(1, 0))

    # function to save the plot 
    # plt.show() 
    plt.savefig('pareto.png')
    plt.close()
    f= open("paretoData.txt","a")
    f.write(str(paretoPts)+'\n')

if __name__== "__main__":
    inv_entity_dict = '../KG_examples/outputs_KGMLN_1/output.dict'
    # PRISMpath = '/Applications/prism-4.6/prism/bin'
    # outputPath = "output1.txt"
    PRISMpath = "../Verification/adv_t1/"
    outputPath = "../Verification/adv_t1/output1.txt"

    # parse_adv_main(inv_entity_dict, PRISMpath, outputPath)
    print('\n')

    result = [((0.9989951743798913, 0.9999999999999998), (0.9998397474548197, 1.9999999999999996), (0.9999747277298394, 4.0)), ((0.8413062331056631, 1.9999999999999996), (0.974816378420348, 2.9999999999999987), (0.9960035226023043, 3.9999999999999982)), ((0.8404619999761332, 2.999999999999999), (0.9738378395601057, 4.0)), ((0.8413062331056631, 1.9999999999999996), (0.974816378420348, 2.9999999999999987), (0.9960035226023043, 3.999999999999997)), ((0.8404619999761332, 2.999999999999999), (0.9738378395601057, 4.0)), ((0.8404619999761332, 2.999999999999999), (0.9738378395601057, 4.0)), ((0.8404619999761332, 2.999999999999999), (0.9738378395601057, 4.0))]
    team = {(0.973838, 4.0): ['GOES-16', 'Elektro-L N3', 'GOES-17', 'Jason-3'], (0.841306, 1.0): ['Aqua'], (0.841306, 2.0): ['Landsat 8', 'Aqua'], (0.973838, 5.0): ['GOES-16', 'Sentinel-1 B', 'GOES-17', 'Jason-3', 'Elektro-L N3'], (0.998995, 1.0): ['Terra'], (0.999975, 5.0): ['GOES-16', 'KOMPSAT-3A', 'GOES-17', 'Terra', 'Elektro-L N3'], (0.996004, 5.0): ['GOES-16', 'GOES-17', 'Elektro-L N3', 'Aqua', 'Landsat 8'], (0.974815, 4.0): ['GOES-16', 'Sentinel-1 A', 'Sentinel-1 B', 'Aqua'], (0.996004, 7.0): ['GOES-16', 'Sentinel-1 B', 'GOES-17', 'Jason-3', 'Elektro-L N3', 'Sentinel-1 A', 'Aqua']}
    time_dict = {5: [(0.973838, 4.0), (0.841306, 1.0), (0.841306, 2.0)], 6: [(0.973838, 4.0), (0.841306, 1.0), (0.841306, 2.0)], 4: [(0.973838, 4.0), (0.973838, 5.0), (0.841306, 1.0), (0.841306, 2.0)], 2: [(0.973838, 4.0), (0.973838, 5.0), (0.841306, 1.0), (0.841306, 2.0)], 0: [(0.998995, 1.0), (0.999975, 5.0)], 1: [(0.841306, 2.0), (0.996004, 5.0), (0.841306, 1.0)], 3: [(0.974815, 4.0), (0.996004, 7.0), (0.841306, 1.0)]}

    pareto_plot_all(result, team, time_dict, showplot = True)





