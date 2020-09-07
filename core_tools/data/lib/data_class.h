#ifndef DATA_CLASSES_H
#define DATA_CLASSES_H


#include <string>
#include <vector>

// todo, check time -- unix time -- windows time - do all automatically match well
// todo add snapshop and metadata (JSON data)
// todo put upload in a seperate thread with a private connection (= dynamic updates) + check last mod (prevent unneed uploads)
// to check -- on serverside, how many concurrent uploads/downdload can be handled
// todo update max packet size to 1GB

// FEAT :: update measurement data?

struct data_item
{
	std::string name;
	std::string label;
	std::string unit;
	std::vector<std::string> dependency;
	double* raw_data;
	std::vector<int> shape;

	int data_size_flat();
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