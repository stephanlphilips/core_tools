#ifndef UPLOAD_MGR_H
#define UPLOAD_MGR_H

#include <thread> 
#include <iostream>
#include <string>
#include <cstring>

#include "mysql_connection.h"

#include <cppconn/driver.h>
#include <cppconn/exception.h>
#include <cppconn/resultset.h>
#include <cppconn/statement.h>
#include <cppconn/prepared_statement.h>

#include "data_class.h"
#include "utility.h"

using namespace std; 

class upload_mgr{
	sql::Driver *driver =  get_driver_instance();
	sql::Connection *con;
	sql::Statement *stmt;
	sql::PreparedStatement *pstmt;
	sql::ResultSet *res;
	void check_init();
public:
	upload_mgr(std::string address, std::string user, std::string password, std::string db_name);

	void request_measurement(data_set_raw *data_set);
	void start_uploadJob(data_set_raw *data_set);
	data_set_raw get_data_set(int exp_id);
	measurement_overview_set get_all_measurements(int N,
		std::string set_up, std::string project, std::string sample);
	measurement_overview_set get_measurements_date_spec(int N, std::pair<long, long> start_stop, 
		std::string set_up, std::string project, std::string sample);	
};

#endif