#ifndef DATA_CLASSES_H
#define DATA_CLASSES_H


#include <string>
#include <vector>

// todo, check time -- unix time -- windows time - do all automatically match well
// todo add snapshop and metadata (JSON data)
// todo put upload in a seperate thread with a private connection (= dynamic updates)
// to check -- on serverside, how many concurrent uploads/downdload can be handled
// todo update max packet size to 1GB

// FEAT :: update measurement data?

struct data_item
{
	long param_id;

	// proporties describing the relation betweeen all the data
	int nth_set;
	long param_id_m_param;
	bool setpoint;
	bool setpoint_local;
	std::string name_gobal;

	// properties describing the data
	std::string name;
	std::string label;
	std::string unit;
	std::string dependency; //JSON
	std::string shape; //JSON
	
	// effective data
	double* raw_data;
	int size;
};

struct data_set_raw
{
	std::vector<data_item> data_entries;
	std::string SQL_table_name;
	
	int exp_id;
	std::string exp_name;

	std::string set_up;
	std::string project;
	std::string sample;

	long UNIX_start_time;
	long UNIX_stop_time;

	bool uploaded_complete;

	std::string snapshot;
	std::string metadata;

	bool completed;
    int writecount;
};


struct measurement_overview_set{
	std::vector<int> exp_id;
	std::vector<std::string> exp_name;

	std::vector<std::string> set_up;
	std::vector<std::string> project;
	std::vector<std::string> sample;

	std::vector<long> UNIX_start_time;
	std::vector<long> UNIX_stop_time;
};

#endif