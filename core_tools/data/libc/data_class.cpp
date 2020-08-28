#include "data_class.h"

int data_item::data_size_flat(){
	int my_size = 1;
	for (uint i = 0; i < shape.size(); ++i){
		my_size *= shape[i];
	}
	return my_size;
};