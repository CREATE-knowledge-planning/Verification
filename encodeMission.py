#!/usr/bin/env python

import json
import datetime as dt
from dateutil.relativedelta import relativedelta
import math
import extractJSON

def findMissionLength(pathMissionJSON):
	'''finding mission length, assuming any and all observation durations = mission duration
	units of mission length are in seconds (decimals are rounded)'''
	with  open(pathMissionJSON, 'r',  encoding='latin-1') as file:
		missionData = json.load(file) 
		t_init = missionData['observations'][0]['startDate'].split('.')[0]     # ignore fractional part of seconds for now
		t_final = missionData['observations'][0]['endDate'].split('.')[0]

		date_format = "%Y-%m-%dT%H:%M:%S"
		date_init = dt.datetime.strptime(t_init, date_format)
		date_final = dt.datetime.strptime(t_final, date_format)
		
		deltaT = date_final - date_init
		deltaSec = deltaT.total_seconds()

		# include fractional part of seconds
		deltaSubSec = 1e-9*(int(missionData['observations'][0]['endDate'].split('.')[1]) - int(missionData['observations'][0]['startDate'].split('.')[1]))
		
		deltaSec += round(deltaSubSec)
		
		return math.ceil(deltaSec/(3600.*24))     # rounding up, dividing to discretize timesteps into days

def generateMissionPCTL(pathMissionJSON, m_list, missionFile, saveFile = False):
	'''Pmax=?[(true U <= 10 ((m1=1) & (m2=1)))]'''
	missionLength = findMissionLength(pathMissionJSON)
	spec = "Pmax=?[!(true U <= " + str(missionLength) + ' !('

	for m in m_list:
		spec += m + '=1 & '
	spec = spec[:-3]    # remove extra ' & '
	spec += '))]'

	if saveFile:
		# save mission spec as file
		text_file = open(missionFile, "w")
		text_file.write(spec)
		text_file.close()
	return spec

def generateMissionMulti(m_list, missionFile, rewardList, saveFile = False):
	'''multi(Pmax=? [G (m1=1 & m2=1)], R{reward1}min=? [ C ])'''

	spec = 'multi(Pmax=? [G ('

	for m in m_list:
		spec += m + '=1 & '
	spec = spec[:-3]    # remove extra ' & '
	spec += ')], '

	for r in rewardList:
		spec += 'R'+ '{"'+r+'"}'+'min=? [ C ], '
	spec = spec[:-2] + ')'   # remove extra ', '


	if saveFile:
		# save mission spec as file
		text_file = open(missionFile, "w")
		text_file.write(spec)
		text_file.close()
	return spec
