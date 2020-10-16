# postgrestables to make

###############
# server side #
###############

# overiew_projects_set_ups_samples table
# generic_data_table

### needed for fast searches
	# project table
	# set up table
	# project_set_up table
	# project setup sample table

###############
# client side #
###############


# local general table (fallback table) -- field synced -- create index
# overiew_projects_set_ups_samples table local (fallback table)

# project setup sample tables that have been generated locally

#########################
# irritating scenario's #
#########################

# two systems are writing to the same table locally, both tables get out of sync
	# --> measurement ID's of one of the two systems have to be adjusted in order for the tables to be able to merge.

import time
from uuid import getnode as get_mac

def generate_uuid():
	ms_time = int(time.time()*1000)*1000000
	return ms_time + get_mac()%99999999

print(generate_uuid())
