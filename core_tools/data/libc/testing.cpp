#include "upload_mgr.h"
#include "data_class.h"
#include <chrono>

int main()
{
	/* code */
	std::cout << "starting program;;;" << std::endl;
	data_set_raw mydata = data_set_raw();
	mydata.set_up = "XLD2";
	mydata.project = "6dot";
	mydata.sample = "SQ2020";
	mydata.exp_name = "test";

	upload_mgr my_mgr = upload_mgr("localhost", "stephan", "magicc", "test");
	
	int size = 50000000;
	double* data_x = (double*) malloc (size*sizeof(double*));
	double* data_y = (double*) malloc (size*sizeof(double*));

	for (double i = 0; i < 50; ++i)
	{
		data_x[(int) i] = i*2;
		data_y[(int) i] = i*4; 
	}

	// emulate 1D measurement
	data_item my_data_object_x = data_item();
	my_data_object_x.param_id = 52166745412;
	my_data_object_x.nth_set = 0;
	my_data_object_x.param_id_m_param = 5216621255412;
	my_data_object_x.setpoint = true;
	my_data_object_x.setpoint_local = false;
	my_data_object_x.name_gobal = "P1";

	my_data_object_x.name = "P1";
	my_data_object_x.label = "P1";
	my_data_object_x.unit = "mV";
	my_data_object_x.shape = "[1000000,]";

	my_data_object_x.raw_data = data_x;
	my_data_object_x.size = size;

	data_item my_data_object_y = data_item();
	my_data_object_y.param_id = 5216621255412;
	my_data_object_y.nth_set = 0;
	my_data_object_y.param_id_m_param = 5216621255412;
	my_data_object_y.setpoint = false;
	my_data_object_y.setpoint_local = false;
	my_data_object_y.name_gobal = "keithley";

	my_data_object_y.name = "keithley";
	my_data_object_y.label = "Current";
	my_data_object_y.unit = "pA";
	my_data_object_y.dependency = "[\"P1\",]";
	my_data_object_y.shape = "[1000000,]";

	my_data_object_y.raw_data = data_y;
	my_data_object_y.size = size;

	mydata.data_entries.push_back(my_data_object_x);
	mydata.data_entries.push_back(my_data_object_y);
	
	// my_mgr.request_measurement(&mydata);
	auto t1 = std::chrono::high_resolution_clock::now();
	// my_mgr.start_uploadJob(&mydata);
	auto t2 = std::chrono::high_resolution_clock::now();
	// my_mgr.get_all_measurements(5, "", "", "");
	// my_mgr.get_all_measurements(5, "XLD2", "", "");

	// my_mgr.get_measurements_date_spec(5, std::make_pair(1598615467,0) ,"XLD2", "", "");
	my_mgr.get_data_set(134);
	auto t3 = std::chrono::high_resolution_clock::now();

    auto duration1 = std::chrono::duration_cast<std::chrono::microseconds>( t2 - t1 ).count();
    auto duration2 = std::chrono::duration_cast<std::chrono::microseconds>( t3 - t2 ).count();

    std::cout << "upload time :: " << duration1*1e-6 << std::endl;
    std::cout << "download time :: " << duration2*1e-6 << std::endl;

	return 0;
}
