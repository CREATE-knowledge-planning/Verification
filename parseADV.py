#!/usr/bin/env python

# PARSE SYNTHESIZED PATH GENERATED FROM PRISM

from extractJSON import findName
import numpy as np
import glob
import main
import ast
import matplotlib.pyplot as plt 

def line_with_string2(string, fp):
    ''' find all lines that start with a substring and outputs as list
    '''
    newstring = []
    for line in fp:
        if line.startswith(string):
        	newstring.append(line.rstrip())
    return newstring

def findMaxP(lineList):
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

def generatePath(ADVfile, STAfile): 
	''' 
	given an adversary file, output:
		pathStates 		the adversary {timestep: [set of agents 'a_ID']}
		actions 		actions taken in adversary
		allP  			list of probabilities at each timestep (len(allP) = # of timesteps)
	'''

	# extract states from adv.tra file
	with open(ADVfile) as file:
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
			lineList = line_with_string2(str(path[idx]) + ' 0 ', lines)
			maxP, action, nextState = findMaxP(lineList)
			if action != 'N/A':
				path.append(nextState)
				actions.append(action)
			idx += 1
			totalP *= maxP
			allP.append(maxP)
		path.pop(0)
	# convert states in adv.tra into agents at each time step
	pathStates = {}
	with open(STAfile) as file:
		lines = file.readlines()
		stateList = lines[0].split(',')
		stateList = [ x for x in stateList if x[0] == 'a' ]    # only care about agent-sensor states 
		
		# print(stateList)
		for stateIdx in path:
			lineState = line_with_string2(str(stateIdx)+ ':', lines)[0]
			as_states = lineState.split(':')[1][3:(3+2*len(stateList)-1)]   # only care about agent-sensor states
			t = int(lineState.split(':')[1][-2])
			as_states = as_states.split(',')

			# for each timestep, determine which agents are being used
			eachTime = set()
			for s in range(len(as_states)):
				if as_states[s] != '0':
					# agent = stateList[s].split('_')[0]
					agent = stateList[s]
					eachTime.add(agent)

			pathStates[t] = eachTime
	return pathStates, actions, allP

def convertAgents(actions, pathToDict, pathStates):
	'''
	convert actions in pathStates dictionary into agent names 
	'''
	t = 1
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
					agent = findName(new[0][1:], pathToDict, 'Platform')
					# print(agent)
					# act_new += new
					agents.add(agent)
		pathStates[t] = agents
		t += 1
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

def calculateReward(actions, allP):
	''' calculate expected reward given series of actions
	'''
	V = 0
	Pprev =allP[0]
	for act in range(len(actions)):
		R = numA(actions[act])
		Pprev = np.prod(allP[0:act])
		V = V + R*Pprev
		Pprev = allP[act]
	return V

def parseADVmain(pathToDict, PRISMpath):
	teams = {}

	num = len(glob.glob1(PRISMpath,"*.tra"))     # number of adversary files
	for i in range(num):
		# print('\nadv' + str(i+1) + '.tra')
		ADVfile = PRISMpath + '/adv' + str(i+1)+'.tra'
		STAfile = PRISMpath + '/prod.sta'
		pathStates, actions, allP = (generatePath(ADVfile,STAfile))
		pathStates = convertAgents(actions, pathToDict, pathStates)
		# print('Path: ',convertAgents(actions, pathToDict, pathStates))
		prob = np.prod(allP)
		print(num, allP)
		R = calculateReward(actions, allP)
		# print('Probability, Reward: ', np.prod(allP), calculateReward(actions, allP))

		# don't include duplicate adversaries
		if (prob, R) not in teams.keys():
			teams[(prob, R)] = {'adv' + str(i+1) + '.tra' : pathStates}

	for team in teams.keys():
		print('\n', list(teams[team].keys())[0])
		print('Probability, Reward: ', team)
		print(list(teams[team].values())[0])

def paretoPlot(outputPath):
	''' plot Pareto front
	'''
	resultLine = main.outputResult(outputPath)
	resultLine = resultLine.split(':')[1]
	resultLine = resultLine.split(']')[0][2:]
	paretoPts = ast.literal_eval(resultLine)
	paretoPts = sorted(paretoPts, key=lambda x:x[0])
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

	# function to show the plot 
	plt.show() 

if __name__== "__main__":
	pathToDict = '../KG_examples/outputs_KGMLN_1/output.dict'
	PRISMpath = '/Applications/prism-4.6/prism/bin'
	outputPath = "output1.txt"

	parseADVmain(pathToDict, PRISMpath)
	print('\n')
	paretoPlot(outputPath)




