#include <iostream>
#include "data_source/osm.hpp"
#include <nlohmann/json.hpp>


int main()
{
    nlohmann::json data = OSM::getData("http://home.nilus.ink:43210/simple/weather/");

    std::cout << "Hello world" << std::endl;
    return 0;
}
