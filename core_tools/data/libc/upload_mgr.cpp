#include "upload_mgr.h"

void upload_mgr::check_init(){
	stmt = con->createStatement();
	stmt->execute(
		"CREATE TABLE if not EXISTS measurements_overview("
		"	id INT NOT NULL AUTO_INCREMENT,"
		"	set_up varchar(1024) NOT NULL,"
		"	project varchar(1024) NOT NULL,"
		"	sample varchar(1024) NOT NULL,"
		"	start_time TIMESTAMP,"
		"	stop_time TIMESTAMP,"
		"	exp_name varchar(1024) NOT NULL,"
		"	exp_data varchar(1024),"
		"	PRIMARY KEY (id))");
}

upload_mgr::upload_mgr(std::string address, std::string user, std::string password, std::string db_name){
	try {
		con = driver->connect(address, user, password);
		con->setSchema(db_name);
		check_init();
		
	} catch (sql::SQLException &e) {
		cout << "# Failed to connect to SQL server (is it online?) ";
		cout << " (MySQL error code: " << e.getErrorCode()  << ", SQLState: " << e.getSQLState() << " )" << endl;
	}
};

void upload_mgr::request_measurement(data_set_raw *data_set){
	stmt = con->createStatement();
	stmt->execute(
		"INSERT INTO measurements_overview "
		"(set_up, project, sample, exp_name) VALUES ('" + 
			data_set->set_up + "', '" + 
			data_set->project + "', '" + 
			data_set->sample + "', '" + 
			data_set->exp_name + "');");

	res = stmt->executeQuery("SELECT MAX(id) FROM measurements_overview;"); 
	res->next();
	data_set->exp_id = std::stoi(res->getString(1));
	data_set->SQL_table_name = std::to_string(data_set->exp_id) + '_' + data_set->set_up +  '_' + data_set->project +  '_' + data_set->sample;
	std::cout << "Generated measurement with ID :: " << data_set->exp_id << std::endl;
	stmt->execute(
		"UPDATE measurements_overview "
		"SET exp_data = '" + 
		data_set->SQL_table_name + 
		"' WHERE id = " + std::to_string(data_set->exp_id) + ";" );
	res = NULL;
};

void upload_mgr::start_uploadJob(data_set_raw *data_set){
	// make table
	stmt = con->createStatement();
	stmt->execute(
		"CREATE TABLE " + data_set->SQL_table_name + " ( "
		"	id INT NOT NULL, "
		"	name varchar(1024) NOT NULL,"
		"	label varchar(1024) NOT NULL,"
		"	unit varchar(1024) NOT NULL,"
		"	depencies JSON, "
		"	shape JSON, "
		" 	rawdata LONGBLOB"
		"   )"
		);
	
	// fill table columns (except for the data)
	for (uint i = 0; i < data_set->data_entries.size(); ++i){
		stmt->execute("INSERT INTO " + data_set->SQL_table_name + " "
			"(id, name, label, unit, depencies, shape) VALUES ('" + 
				std::to_string(i) + "', '" + 
				data_set->data_entries[i].name + "', '" + 
				data_set->data_entries[i].label + "', '" + 
				data_set->data_entries[i].unit + "', '" + 
				vector_to_json(data_set->data_entries[i].dependency) + "', '" + 
				vector_to_json(data_set->data_entries[i].shape) + "');");
	}

	for (uint i = 0; i < data_set->data_entries.size(); ++i){
		int mysize = data_set->data_entries[i].data_size_flat()*sizeof(double*);
	    char * my_data_as_char = (char*) malloc (mysize);
	    memcpy(my_data_as_char, data_set->data_entries[i].raw_data, mysize);
	    memory_buf my_mem = memory_buf(my_data_as_char, mysize);
		istream my_mem_stream(&my_mem);

		pstmt = con->prepareStatement("UPDATE " + data_set->SQL_table_name + " "
			"SET rawdata = ?"
			" WHERE id = " + std::to_string(i) + ";"
			);
		pstmt->setBlob(1, &my_mem_stream);
		pstmt->execute();
	}
}

/*
 * get a overview of the measuremenets
 *
 * Args
 *	N : number of measurements to get (if 0, get all)
 *  start_stop : get measurrements in between dates. If stop is 0, the end data is now.
 * set_up, project, sample : if empty, no not select on this property
*/
measurement_overview_set upload_mgr::get_measurements_date_spec(int N, std::pair<long, long> start_stop, 
	std::string set_up, std::string project, std::string sample){
	
	std::string query = "SELECT id, set_up, project, sample, UNIX_TIMESTAMP(start_time), UNIX_TIMESTAMP(stop_time), exp_name "
		"FROM measurements_overview "
		" WHERE ";

	// no selection is to select all.
	if (set_up != "")
		query+= "set_up = '" + set_up +"' AND ";
	if (project != "")
		query+= "project = '" + project +"' AND ";
	if (sample != "")
		query+= "sample = '" + sample +"' AND ";
	if (start_stop.first == 0 and start_stop.second == 0)
		query += "1=1 ";
	else if (start_stop.first == 0)
		query+= "stop_time <= FROM_UNIXTIME(" + to_string(start_stop.second) + ") ";
	else if (start_stop.second == 0)
		query+= "start_time >= FROM_UNIXTIME(" + to_string(start_stop.first) +") ";
	else
		query+= "start_time >= FROM_UNIXTIME(" + to_string(start_stop.first) +") AND "
			"stop_time <= FROM_UNIXTIME(" + to_string(start_stop.second) +") ";

	query += "ORDER BY id DESC ";

	if (N == 0){
		query += ";";
	}else{
		query += "LIMIT " + std::to_string(N) +";";
	}
	res = stmt->executeQuery(query);

	measurement_overview_set measurements_overview;
	
	while (res->next()) {
		measurements_overview.exp_id.push_back(res->getInt("id"));
		measurements_overview.exp_name.push_back(res->getString("exp_name"));
		measurements_overview.set_up.push_back(res->getString("set_up"));
		measurements_overview.project.push_back(res->getString("project"));
		measurements_overview.sample.push_back(res->getString("sample"));
		measurements_overview.UNIX_start_time.push_back(res->getInt(5));
		measurements_overview.UNIX_stop_time.push_back(res->getInt(6));
	}

	return measurements_overview;

};

measurement_overview_set upload_mgr::get_all_measurements(int N,
	std::string set_up, std::string project, std::string sample){

	std::pair<long, long> start_stop(0,0);
	return get_measurements_date_spec(N, start_stop, set_up, project, sample);
};

data_set_raw upload_mgr::get_data_set(int exp_id){
	data_set_raw data_set;

	data_set.exp_id = exp_id;

	std::string query = "SELECT id, set_up, project, sample, "
		"UNIX_TIMESTAMP(start_time), UNIX_TIMESTAMP(stop_time), exp_name, exp_data "
		"FROM measurements_overview "
		"WHERE id = " + std::to_string(exp_id) + " ;";
	
	res = stmt->executeQuery(query);

	if (res->rowsCount() == 0)
		std::cout << "Warning :: dataset with id " + std::to_string(exp_id) +
		"does not exist. Returning empty data set.";
	else{
		// general measurement information
		res->next();
		data_set.exp_id = res->getInt("id");
		data_set.exp_name = res->getString("exp_name");
		data_set.set_up = res->getString("set_up");
		data_set.project = res->getString("project");
		data_set.sample = res->getString("sample");
		data_set.UNIX_start_time = res->getInt(5);
		data_set.UNIX_stop_time = res->getInt(6);


		query = "SELECT * from " + res->getString("exp_data") + " ;";
		res = stmt->executeQuery(query);

		while(res->next()){
			data_item my_data_item;

			my_data_item.name = res->getString("name");
			my_data_item.label = res->getString("label");
			my_data_item.unit = res->getString("unit");
			my_data_item.dependency = json_to_vector_str(res->getString("depencies"));
			my_data_item.shape = json_to_vector_int(res->getString("shape"));

			// double copy, could not get access to the pointer.. -> good solution?
			char *binary_input_data_raw = (char*) malloc (my_data_item.data_size_flat()*sizeof(double*));
			std::istream* binary_input_data = res->getBlob("name");
			binary_input_data->read(binary_input_data_raw, my_data_item.data_size_flat()*sizeof(double*));

			double* measurement_data = (double*) malloc (my_data_item.data_size_flat()*sizeof(double*));
			memcpy(measurement_data, binary_input_data_raw,
				my_data_item.data_size_flat()*sizeof(double*));
			
			my_data_item.raw_data = measurement_data;

			data_set.data_entries.push_back(my_data_item);
		}
	}

	return data_set;
	
};