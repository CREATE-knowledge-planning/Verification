#!/usr/bin/env python

# PARSE SYNTHESIZED PATH GENERATED FROM PRISM

from extractJSON import findName
import numpy as np
import glob

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
	''' output adversary that PRISM provides as dictionary 
	{timestep: [set of agents 'a_ID']}
	'''

	# extract states from adv.tra file
	with open(ADVfile) as file:
		# assume 0 is the initial state
		lines = file.readlines()
		path = [0]
		idx = 0
		action = ''
		totalP = 1
		testP = []
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
			testP.append(maxP)
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
	return pathStates, totalP, actions, testP

# print('t',totalP, actions)


# convert actions into agent names
def convertAgents(actions, pathToDict, pathStates):
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
	# TO_A472S1606__2_A652S1126__1
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


def calculateReward(actions, testP):
	V = 0
	Pprev =testP[0]

	for act in range(len(actions)):
		# V = sum(P*(R+V))
		R = numA(actions[act])
		# V += testP[act]*(R)
		Pprev = np.prod(testP[0:act])
		V = V + R*Pprev
		Pprev = testP[act]
	return V

def parseADVmain(pathToDict, PRISMpath):

	num = len(glob.glob1(PRISMpath,"*.tra"))     # number of adversary files

	for i in range(num):
		print('\nadv' + str(i+1) + '.tra')
		ADVfile = PRISMpath + '/adv' + str(i+1)+'.tra'
		STAfile = PRISMpath + '/prod.sta'
		pathStates, totalP, actions, testP = (generatePath(ADVfile,STAfile))
		print('Path: ',convertAgents(actions, pathToDict, pathStates))
		# print('(probability, reward): (', totalP, calculateReward(actions, testP),')')
		print('Probability: ', totalP)

if __name__== "__main__":
	pathToDict = '../KG_examples/outputs_KGMLN_1/output.dict'
	PRISMpath = '/Applications/prism-4.5-osx64/bin'
	parseADVmain(pathToDict, PRISMpath)


