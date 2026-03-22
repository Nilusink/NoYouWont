/**
    * @file osm.hpp
    * @author Nilusink
    * @brief Retrieves data from OpenStreetMap
    * @version 0.1
    * @date 2024-06-01
    *
*/
#include <iostream>
#include <string>
#include <curl/curl.h>
#include <nlohmann/json.hpp>


namespace OSM
{
    // Function to handle the response from the API
    size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* userp);

    // Function to retrieve data from OpenStreetMap API
    nlohmann::json getData(const std::string& url);

}
