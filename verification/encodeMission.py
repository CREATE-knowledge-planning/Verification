#!/usr/bin/env python

import datetime as dt
import dateutil
import math


def find_mission_length(mission_info):
	'''finding mission length, assuming any and all observation durations = mission duration
	units of mission length are in seconds (decimals are rounded)'''
	date_init = dateutil.parser.isoparse(mission_info['observations'][0]['startDate'].iso_format())    # ignore fractional part of seconds for now
	date_final = dateutil.parser.isoparse(mission_info['observations'][0]['endDate'].iso_format())
	
	delta_t = date_final - date_init
	delta_sec = delta_t.total_seconds()

	# include fractional part of seconds
	delta_subsec = 1e-6*delta_t.microseconds
	
	delta_sec += round(delta_subsec)
	
	return math.ceil(delta_sec/(3600.*24))     # rounding up, dividing to discretize timesteps into days


def generateMissionPCTL(pathMissionJSON, m_list, missionFile, saveFile = False):
	'''single objectve, ex: Pmax=?[(true U <= 10 ((m1=1) & (m2=1)))]'''
	missionLength = find_mission_length(pathMissionJSON)
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

def generate_mission_multi(m_list, mission_file, reward_list, save_file=False):
	'''mult-objective, ex: multi(Pmax=? [G (m1=1 & m2=1)], R{reward1}min=? [ C ])'''

	spec = 'multi(Pmax=? [G (allM '

	# for m in m_list:
	# 	spec += m + '=1 & '
	# spec = spec[:-3]    # remove extra ' & '
	spec += ')], '

	for r in reward_list:
		spec += 'R'+ '{"'+r+'"}'+'min=? [ C ], '
	spec = spec[:-2] + ')'   # remove extra ', '


	if save_file:
		# save mission spec as file
		with mission_file.open('w') as text_file:
			text_file.write(spec)
	return spec
