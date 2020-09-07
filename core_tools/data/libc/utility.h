#ifndef UTILITY_H
#define UTILITY_H

#include <string>
#include <vector>
#include <iostream>

std::string vector_to_json(std::vector<int> input_vector);
std::string vector_to_json(std::vector<std::string> input_vector);
std::vector<int> json_to_vector_int(std::string input_json);
std::vector<std::string> json_to_vector_str(std::string input_json);

struct memory_buf : std::streambuf {
    memory_buf(char* base, std::size_t n);
};
#endif