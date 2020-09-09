from libcpp.string cimport string
from libcpp.vector cimport vector
from libcpp.pair cimport pair
from libcpp cimport bool

cdef extern from "data_class.h":
	struct data_item:
		long param_id
		int nth_set
		long param_id_m_param
		bool setpoint
		bool setpoint_local
		string name_gobal

		string name
		string label
		string unit
		string dependency
		string shape

		double *raw_data

		int data_size_flat()
		int size

	struct data_set_raw:
		vector[data_item] data_entries
		string SQL_table_name
		
		int exp_id
		string exp_name

		string set_up
		string project
		string sample

		long UNIX_start_time
		long UNIX_stop_time

		bool uploaded_complete

		string snapshot
		string metadata

		bool completed
		int writecount

	struct measurement_overview_set:
		vector[int] exp_id
		vector[string] exp_name

		vector[string] set_up
		vector[string] project
		vector[string] sample

		vector[long] UNIX_start_time
		vector[long] UNIX_stop_time

cdef extern from "upload_mgr.h":
	cdef cppclass upload_mgr:
		upload_mgr(string, string, string, string)
		void request_measurement(data_set_raw *data_set);
		void start_uploadJob(data_set_raw *data_set);
		data_set_raw get_data_set(int exp_id);
		measurement_overview_set get_all_measurements(int N,
			string set_up, string project, string sample);
		measurement_overview_set get_measurements_date_spec(int N, pair[long, long] start_stop, 
			string set_up, string project, string sample);	