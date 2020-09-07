#include "upload_mgr.h"

#include "upload_mgr.cpp"
#include "utility.cpp"
#include "data_class.cpp"


int main(int argc, char const *argv[])
{
	/* code */

	data_set_raw mydata = data_set_raw();
	mydata.set_up = "XLD2";
	mydata.project = "6dot";
	mydata.sample = "SQ2020";
	mydata.exp_name = "test";

	upload_mgr my_mgr = upload_mgr("localhost", "stephan", "magicc", "test");
	// my_mgr.request_measurement(&mydata);
	
	int size = 1000000;
	double* data_x = (double*) malloc (size*sizeof(double*));
	double* data_y = (double*) malloc (size*sizeof(double*));

	for (double i = 0; i < 50; ++i)
	{
		data_x[(int) i] = i*2;
		data_y[(int) i] = i*4; 
	}

	std::vector<int> shape;
	shape.push_back(size);

	// emulate 1D measurement
	data_item my_data_object_x = data_item();
	my_data_object_x.name = "P1";
	my_data_object_x.label = "P1";
	my_data_object_x.unit = "mV";
	my_data_object_x.raw_data = data_x;
	my_data_object_x.shape = shape;

	data_item my_data_object_y = data_item();
	my_data_object_y.name = "keithley";
	my_data_object_y.label = "Current";
	my_data_object_y.unit = "pA";
	my_data_object_y.dependency.push_back("P1");
	my_data_object_y.raw_data = data_y;
	my_data_object_y.shape = shape;

	mydata.data_entries.push_back(my_data_object_x);
	mydata.data_entries.push_back(my_data_object_y);

	// my_mgr.start_uploadJob(&mydata);

	// my_mgr.get_all_measurements(5, "", "", "");
	// my_mgr.get_all_measurements(5, "XLD2", "", "");

	my_mgr.get_measurements_date_spec(5, std::make_pair(1598615467,0) ,"XLD2", "", "");
	my_mgr.get_data_set(66);
	return 0;
}