#include "utility.h"

std::string vector_to_json(std::vector<int> input_vector){
	std::string json_out;

	json_out += "[";
	for (uint i = 0; i < input_vector.size(); ++i){
		json_out += std::to_string(input_vector[i]);
		if (i != input_vector.size()-1)
			json_out += ",";
	}
	if (input_vector.size()==0)
		json_out += " ";
	json_out += "]";
	
	return json_out;
};

std::string vector_to_json(std::vector<std::string> input_vector){
	std::string json_out;

	json_out += "[";
	for (uint i = 0; i < input_vector.size(); ++i){
		json_out += "\"" + input_vector[i] + "\"";
		if (i != input_vector.size()-1)
			json_out += ", ";
	}
	if (input_vector.size()==0)
		json_out += " ";
	json_out += "]";
	
	return json_out;
};


std::vector<int> json_to_vector_int(std::string input_json){
	std::vector<int> output_vector;

    size_t pos = 0;
    
    input_json.erase(0,1);
    input_json.erase(input_json.size()-1,input_json.size());

	while ((pos = input_json.find(", ")) != std::string::npos) {
	    output_vector.push_back(std::stoi(input_json.substr(0, pos)));
	    input_json.erase(0, pos + 2);
	}
	output_vector.push_back(std::stoi(input_json));

    return output_vector;
}

std::vector<std::string> json_to_vector_str(std::string input_json){
	std::vector<std::string> output_vector;

    size_t pos = 0;
    
    input_json.erase(0,1);
    input_json.erase(input_json.size()-1,input_json.size());

	while ((pos = input_json.find(", ")) != std::string::npos) {
	    output_vector.push_back(input_json.substr(0, pos));
	    input_json.erase(0, pos + 2);
	}
	output_vector.push_back(input_json);

    return output_vector;
}


memory_buf::memory_buf(char* base, std::size_t n) {
    setg(base, base, base + n);
};