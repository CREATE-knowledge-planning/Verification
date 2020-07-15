#!/usr/bin/env python

# main file to run verification step
import os

from . import encodeMission
from .extractJSON import *
from .generate_MDP_time import constructKGModule, constructActionsModule, replaceIdx, saveMDPfile

def callPRISM(MDPpath, propertyPath, outputPath, PRISMpath):
	''' run PRISM in terminal from PRISMpath (/Applications/prism-4.5-osx64/bin)
	save output log in outputPath
	'''
	os.chdir(PRISMpath)
	command = './prism ' + MDPpath + ' ' + propertyPath + ' > ' + outputPath 
	print(command)
	os.system(command)

def main():
	# data from knowledge graph (from Antoni)
	pathTimeJSON = 'accesses.json'
	pathMissionJSON = 'mission.json'
	pathToDict = '../KG_examples/outputs_KGMLN_1/output.dict'
	# bin directory of PRISM application
	PRISMpath = '/Applications/prism-4.5-osx64/bin'      

	# name of files for PRISM (saved to current directory)
	missionFile = "prop_test.txt" 			# specification
	mdpFile = "KG_test.txt" 				# MDP
	outputFile = "testFile2.txt" 			# output log

	# potential team to verify (from Zhaoliang)
	# {agent1: [{sensor1: {obs1: P1}, {sensor2: {obs2: P2}}}], agent2: [{sensor3: {obs3: P3} }] }
	team = {'GOES-17': [{'ABI': {'Cloud type': 0.8}    }], \
			'Metop-A': [{'MHS': {'Cloud type': 0.7}}, {'IASI': {'Land surface temperature': 0.7}}]}
	target = findTarget(pathMissionJSON)
	teamTime = findTimeBounds(team, target, pathTimeJSON)

	a_prefix, s_prefix, m_prefix = 'a', 's', 'm'
	a_list, s_list, m_list = generateASMlists(team, pathToDict, a_prefix, s_prefix, m_prefix)
	num_a, num_s, num_m = len(a_list), len(s_list), len(m_list)

	# mission for PRISM
	missionPCTL = encodeMission.generateMissionPCTL(pathMissionJSON, m_list, missionFile, saveFile = True)
	missionLength = encodeMission.findMissionLength(pathMissionJSON)

	# relationship matrices
	relation_as = construct_asMatrix(team, pathToDict, num_a, num_s, a_prefix, s_prefix, a_list, s_list)
	relation_ms = construct_msMatrix(team, pathToDict, num_m, num_s, m_prefix, s_prefix, m_list, s_list)
	relation_ms_no, probDict = notMeasMat(team, pathToDict, relation_ms, num_m, num_s, s_prefix, m_prefix, s_list)

	# modules for PRISM MDP
	KG_module = constructKGModule(num_a, num_s, num_m, a_prefix, s_prefix,m_prefix,a_list, s_list,teamTime, relation_as, relation_ms,relation_ms_no, probDict,pathToDict,missionLength)
	actions_module = constructActionsModule(num_a, num_s, teamTime, relation_as, a_prefix, s_prefix, a_list, s_list, pathToDict)
	KG_module, actions_module = replaceIdx(a_list, s_list, m_list, KG_module, actions_module)

	saveMDPfile(KG_module, actions_module, mdpFile)

	# save PRISM files to current directory
	current_dir = str(os.getcwd())
	MDPpath = current_dir + '/' + mdpFile
	propertyPath = current_dir + '/' + missionFile
	outputPath = current_dir + '/' + outputFile	

	callPRISM(MDPpath, propertyPath, outputPath, PRISMpath)


if __name__== "__main__":
	main()

