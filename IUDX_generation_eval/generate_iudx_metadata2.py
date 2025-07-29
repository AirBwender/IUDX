import os
import json
import uuid
import re
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Configuration for resource types
resource_config = {
    "GeoJSON": {
        "prompt_file": "prompt_template_geojson.txt",
        "required_params": [],
        "metadata": {
            "resourceType": "OGC",
            "iudxResourceAPIs": ["FEATURES"],
            "accessPolicy": "OPEN",
            "apdURL": "acl-apd.geospatial.org.in",
            "additional_fields": {
                "crs": "EPSG:4326",
                "datum": "WGS84",
                "ogcResourceInfo": {
                    "ogcResourceAPIs": ["FEATURES"],
                    "geometryType": "Point"
                }
            }
        }
    },
    "EmergencyVehicle": {
        "prompt_file": "prompt_template_emergency_vehicle.txt",
        "required_params": ["city", "polygon"],
        "metadata": {
            "resourceType": "MESSAGESTREAM",
            "iudxResourceAPIs": ["ATTR", "TEMPORAL", "SPATIAL"],
            "accessPolicy": "SECURE",
            "apdURL": "acl-apd.iudx.org.in"
        }
    },
    "EnvAQM": {
        "prompt_file": "prompt_template_env_aqm.txt",
        "required_params": ["city", "polygon"],
        "metadata": {
            "resourceType": "MESSAGESTREAM",
            "iudxResourceAPIs": ["ATTR", "TEMPORAL"],
            "accessPolicy": "SECURE",
            "apdURL": "acl-apd.iudx.org.in"
        }
    },
    "EnergyMeter": {
        "prompt_file": "prompt_template_energy_meter.txt",
        "required_params": ["location_address"],
        "metadata": {
            "resourceType": "MESSAGESTREAM",
            "iudxResourceAPIs": ["ATTR", "TEMPORAL"],
            "accessPolicy": "SECURE",
            "apdURL": "acl-apd.iudx.org.in"
        }
    },
    "TransitManagement": {
        "prompt_file": "prompt_template_transit_management.txt",
        "required_params": ["city", "polygon"],
        "metadata": {
            "resourceType": "MESSAGESTREAM",
            "iudxResourceAPIs": ["SPATIAL", "TEMPORAL", "ATTR"],
            "accessPolicy": "SECURE",
            "apdURL": "acl-apd.iudx.org.in"
        }
    },
    "TrafficViolations": {
        "prompt_file": "prompt_template_traffic_violations.txt",
        "required_params": ["city", "polygon"],
        "metadata": {
            "resourceType": "MESSAGESTREAM",
            "iudxResourceAPIs": ["TEMPORAL", "SPATIAL", "ATTR"],
            "accessPolicy": "SECURE",
            "apdURL": "acl-apd.iudx.org.in"
        }
    },
    "WaterDistributionNetwork": {
        "prompt_file": "prompt_template_water_distribution_network.txt",
        "required_params": ["city", "polygon", "name"],
        "metadata": {
            "resourceType": "MESSAGESTREAM",
            "iudxResourceAPIs": ["ATTR", "TEMPORAL", "SPATIAL"],
            "accessPolicy": "SECURE",
            "apdURL": "acl-apd.iudx.org.in"
        }
    },
    "BikeDockingStation": {
        "prompt_file": "prompt_template_bike_docking_station.txt",
        "required_params": ["city", "polygon"],
        "metadata": {
            "resourceType": "GSLAYER",
            "iudxResourceAPIs": ["SPATIAL", "ATTR"],
            "accessPolicy": "SECURE",
            "apdURL": "acl-apd.iudx.org.in"
        }
    }
}

def generate_filename(resource_type, city=None, name=None):
    """Generate a descriptive filename based on resource type and parameters."""
    city = city.lower().replace(" ", "_") if city else "unknown"
    if resource_type == "GeoJSON":
        return "location_data.geojson"
    elif resource_type == "EmergencyVehicle":
        return f"{city}_ambulance_live.json"
    elif resource_type == "EnvAQM":
        return f"{city}_aqm_info.json"
    elif resource_type == "EnergyMeter":
        return f"{city}_energy_meter_version_info.json"
    elif resource_type == "TransitManagement":
        return f"{city}_transit_management_live_eta.json"
    elif resource_type == "TrafficViolations":
        return f"{city}_traffic_violations.json"
    elif resource_type == "WaterDistributionNetwork":
        return f"{city}_water_distribution_network_{name.lower()}.json"
    elif resource_type == "BikeDockingStation":
        return f"{city}_bike_docking_stations.json"
    return f"{city}_{resource_type.lower()}.json"

def generate_metadata(json_input, resource_type, **kwargs):
    """
    Generate IUDX-compliant JSON-LD metadata for the given input JSON and resource type.
    
    Args:
        json_input (dict): The input JSON data.
        resource_type (str): The type of resource (e.g., "GeoJSON", "EnergyMeter").
        **kwargs: Additional parameters like location_address, city, polygon, name, etc.
    
    Returns:
        dict: The generated IUDX-compliant JSON-LD metadata.
    """
    if resource_type not in resource_config:
        raise ValueError(f"Unknown resource_type: {resource_type}")

    config = resource_config[resource_type]
    prompt_file = config["prompt_file"]

    # Load prompt template
    with open(prompt_file, "r") as f:
        template = f.read()

    # Validate required parameters
    for param in config["required_params"]:
        if param not in kwargs:
            raise ValueError(f"Missing required parameter: {param} for {resource_type}")

    # Replace placeholders
    prompt = template
    replacements = {"json_input": json.dumps(json_input, indent=2)}
    for key, value in kwargs.items():
        replacements[key] = json.dumps(value) if key == "polygon" else str(value)
    for placeholder, value in replacements.items():
        prompt = prompt.replace(f"{{{placeholder}}}", value)

    # Query the model
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": "You are a JSON-LD generator for IUDX metadata."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw_output = response.choices[0].message.content.strip()

    # Extract and clean JSON block
    start = raw_output.find("{")
    end = raw_output.rfind("}") + 1
    if start == -1 or end == -1:
        raise ValueError("No valid JSON object found in model output.")

    clean_json_str = raw_output[start:end]
    parsed_metadata = json.loads(clean_json_str)

    # Add UUID as `id`
    parsed_metadata["id"] = str(uuid.uuid4())

    # Set itemCreatedAt to current datetime in IST
    parsed_metadata["itemCreatedAt"] = datetime.now().isoformat() + "+0530"

    # Ensure database-retrieved fields are blank
    parsed_metadata["provider"] = ""
    parsed_metadata["resourceServer"] = ""
    parsed_metadata["resourceGroup"] = ""

    # Add metadata from config
    for key, value in config["metadata"].items():
        parsed_metadata[key] = value
    if "additional_fields" in config["metadata"]:
        parsed_metadata.update(config["metadata"]["additional_fields"])

    return parsed_metadata

# Example usage for all resource types
if __name__ == "__main__":
    # GeoJSON
    geojson_input = {
        "type": "Feature",
        "properties": {"Type_": 2},
        "geometry": {"type": "Point", "coordinates": [76.41462895569893, 29.157327761329174]},
        "filename": "location_of_temple_sonipat_haryana.geojson"
    }
    metadata_geojson = generate_metadata(geojson_input, "GeoJSON")
    with open("output_geojson.jsonld", "w") as f:
        json.dump(metadata_geojson, f, indent=2)

    # EmergencyVehicle
    emergency_vehicle_input = {
        "emergencyVehicleType": "AMBULANCE",
        "license_plate": "GJ06G6385",
        "observationDateTime": "2021-07-25T19:46:04+05:30",
        "location": {"type": "Point", "coordinates": [73.171237, 22.309942]},
        "filename": generate_filename("EmergencyVehicle", city="Vadodara")
    }
    metadata_emergency_vehicle = generate_metadata(
        emergency_vehicle_input,
        "EmergencyVehicle",
        city="Vadodara",
        polygon=[[[73.13804, 22.38404], [73.10508, 22.30084], [73.18714, 22.22967], [73.28224, 22.30466], [73.2249, 22.38214], [73.13804, 22.38404]]]
    )
    with open("output_emergency_vehicle.jsonld", "w") as f:
        json.dump(metadata_emergency_vehicle, f, indent=2)

    # EnvAQM
    env_aqm_input = {
        "deviceID": "hsxuyiwbjj59psvv",
        "observationDateTime": "2022-08-25T04:00:12+05:30",
        "airTemperature": {"instValue": 24.88},
        "airQualityIndex": 257.480537794617,
        "atmosphericPressure": 971.57,
        "relativeHumidity": {"instValue": 100},
        "pm10": {"instValue": 70},
        "pm2p5": {"instValue": 55},
        "co": {"instValue": 0.046},
        "no2": {"instValue": 0.123},
        "co2": {"instValue": 409},
        "filename": generate_filename("EnvAQM", city="Raipur")
    }
    metadata_env_aqm = generate_metadata(
        env_aqm_input,
        "EnvAQM",
        city="Raipur",
        polygon=[[[81.644453, 21.341153], [81.534932, 21.253856], [81.599111, 21.189913], [81.682841, 21.204769], [81.702036, 21.276331], [81.644453, 21.341153]]]
    )
    with open("output_env_aqm.jsonld", "w") as f:
        json.dump(metadata_env_aqm, f, indent=2)

    # EnergyMeter
    energy_meter_input = {
        "deviceInfo": {
            "deviceName": "Energy Monitoring",
            "deviceID": "EM-NC-VN01-00"
        },
        "versionInfo": [
            {
                "versionSpec": {
                    "frequency": "",
                    "reactiveEnergyLead": "",
                    "reactiveEnergyLag": "",
                    "rssi": "",
                    "phaseCurrent": "",
                    "phaseVoltage": "",
                    "controller": "'Energy API running in a Django application on the Resource Server",
                    "totalActivePower": "",
                    "totalApparentPower": "",
                    "powerFactor": "",
                    "energyConsumed": ""
                },
                "comments": "Energy Monitoring",
                "startDateTime": "2020-08-19T10:00:00+05:30",
                "endDateTime": "9999-99-99T99:99:99+05:30",
                "versionName": "V1.00.00"
            }
        ],
        "filename": generate_filename("EnergyMeter", city="iiit_hyderabad")
    }
    metadata_energy_meter = generate_metadata(
        energy_meter_input,
        "EnergyMeter",
        location_address="IIIT Hyderabad, Telangana"
    )
    with open("output_energy_meter.jsonld", "w") as f:
        json.dump(metadata_energy_meter, f, indent=2)

    # TransitManagement
    transit_management_input = {
        "location": {"coordinates": [72.886055, 21.224406], "type": "Point"},
        "last_stop_id": "4032",
        "actual_trip_start_time": "2020-09-16T13:30:00+05:30",
        "speed": 28,
        "observationDateTime": "2020-09-16T13:30:00+05:30",
        "trip_delay": 11968,
        "trip_direction": "DN",
        "last_stop_arrival_time": "13:30:12",
        "vehicle_label": "A03",
        "route_id": "17AD",
        "license_plate": "GJ05BX1583",
        "trip_id": "23952340",
        "filename": generate_filename("TransitManagement", city="Surat")
    }
    metadata_transit_management = generate_metadata(
        transit_management_input,
        "TransitManagement",
        city="Surat",
        polygon=[[[72.941762, 21.259964], [72.896444, 21.166506], [72.822981, 21.068548], [72.713804, 21.136772], [72.746763, 21.200163], [72.831564, 21.269925], [72.941762, 21.259964]]]
    )
    with open("output_transit_management.jsonld", "w") as f:
        json.dump(metadata_transit_management, f, indent=2)

    # TrafficViolations
    traffic_violations_input = {
        "alertType": "RED_LIGHT_VIOLATION_DETECTION",
        "location": {"coordinates": [77.595183, 12.910289], "type": "Point"},
        "cameraUsage": "ANPR",
        "junctionName": "JPnagar-8thmain-9thcross",
        "vehicleType": "Motorbike",
        "license_plate": "915cb0f52443154dc7990ee84a1beb846cd44447",
        "observationDateTime": "2024-02-14T15:24:07+05:30",
        "filename": generate_filename("TrafficViolations", city="Bengaluru")
    }
    metadata_traffic_violations = generate_metadata(
        traffic_violations_input,
        "TrafficViolations",
        city="Bengaluru",
        polygon=[[[77.316284, 13.02329], [77.445373, 12.79707], [77.737884, 12.768946], [77.843627, 12.96575], [77.742004, 13.161062], [77.487945, 13.186468], [77.316284, 13.02329]]]
    )
    with open("output_traffic_violations.jsonld", "w") as f:
        json.dump(metadata_traffic_violations, f, indent=2)

    # WaterDistributionNetwork (RWPH)
    water_distribution_network_input_rwph = {
        "deviceName": "RWPH.RWPH_1.PROCESS.RWPH1_PT_103",
        "measurand": "PUMP3 OUTLET Pressure Transmitter | Unit: KG/CM2",
        "deviceStatus": "NORMAL:6-4 | Range: 0-10",
        "deviceMeasure": 4.4256591797,
        "observationDateTime": "2024-11-05T15:34:28+05:30",
        "address": "RWPH1",
        "location": {"coordinates": [80.89743, 24.55826]},
        "filename": generate_filename("WaterDistributionNetwork", city="Satna", name="rwph")
    }
    metadata_water_distribution_network_rwph = generate_metadata(
        water_distribution_network_input_rwph,
        "WaterDistributionNetwork",
        city="Satna",
        polygon=[[[80.7754566807481, 24.5982538195379], [80.7686723964293, 24.5722522821716], [80.7817554999998, 24.5607883640749], [80.8253740931068, 24.5532818867026], [80.8728716781444, 24.5568064615414], [80.9174898454848, 24.5902897773785], [80.8757570400335, 24.6268852484211], [80.8127544894199, 24.6290987351912], [80.7754566807481, 24.5982538195379]]],
        name="rwph"
    )
    with open("output_water_distribution_network_rwph.jsonld", "w") as f:
        json.dump(metadata_water_distribution_network_rwph, f, indent=2)

    # WaterDistributionNetwork (MLD-18)
    water_distribution_network_input_mld18 = {
        "deviceName": "18MLD.WTP2.PROCESS.CWS_PT_103",
        "measurand": "CWS PUMP1 O/L PRESSURE TRANSMITTER | Unit: KG/CM2",
        "deviceStatus": "LOW LOW:2 | Range: 0-10",
        "deviceMeasure": 0,
        "observationDateTime": "2024-11-05T15:03:59+05:30",
        "location": {"coordinates": [80.852842, 24.571722]},
        "filename": generate_filename("WaterDistributionNetwork", city="Satna", name="mld18")
    }
    metadata_water_distribution_network_mld18 = generate_metadata(
        water_distribution_network_input_mld18,
        "WaterDistributionNetwork",
        city="Satna",
        polygon=[[[80.7754566807481, 24.5982538195379], [80.7686723964293, 24.5722522821716], [80.7817554999998, 24.5607883640749], [80.8253740931068, 24.5532818867026], [80.8728716781444, 24.5568064615414], [80.9174898454848, 24.5902897773785], [80.8757570400335, 24.6268852484211], [80.8127544894199, 24.6290987351912], [80.7754566807481, 24.5982538195379]]],
        name="mld18"
    )
    with open("output_water_distribution_network_mld18.jsonld", "w") as f:
        json.dump(metadata_water_distribution_network_mld18, f, indent=2)

    # BikeDockingStation
    bike_docking_station_input = {
        "name": "Bike Docking Station Alandur Metro",
        "stationName": "Alandur Metro",
        "location": {"type": "Point", "coordinates": [80.2010611, 13.0035349]},
        "filename": generate_filename("BikeDockingStation", city="Chennai")
    }
    metadata_bike_docking_station = generate_metadata(
        bike_docking_station_input,
        "BikeDockingStation",
        city="Chennai",
        polygon=[[[80.194702, 13.113586], [80.187492, 13.078475], [80.199851, 13.05473], [80.230751, 13.041686], [80.277442, 13.050382], [80.295295, 13.08115], [80.283966, 13.108236], [80.266113, 13.130972], [80.230751, 13.136656], [80.194702, 13.113586]]]
    )
    with open("output_bike_docking_station.jsonld", "w") as f:
        json.dump(metadata_bike_docking_station, f, indent=2)