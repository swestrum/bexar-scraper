from bs4 import BeautifulSoup
import requests
import re
from collections import OrderedDict
from typing import Any, List
from rich import print

def currency_str_convert(currency_str: str) -> int:
    return int(currency_str.replace("$", "").replace(",", ""))

def convert_key(key_str: str) -> str:
    return key_str.replace(":", "").replace(" ", "_").replace(".", "").replace('%', 'percent').replace("-", "_").lower()

def scrape(id_list: List[int], quiet: bool = False) -> List[OrderedDict[int, Any]]:
    starting_url = "https://bexar.trueautomation.com/ClientDB/Property.aspx?cid=110&prop_id="
    property_info_list = []
    for id in id_list:
        property_id = str(id)
        property_site = requests.get(f"{starting_url}{property_id}")
        property_soup = BeautifulSoup(property_site.content, "html.parser")
        page_messages = property_soup.find("div", id="pageMessage").contents
        if len(page_messages) > 0:
            if "Property not found." in page_messages[0]:
                continue
        for e in property_soup.findAll('br'):
            e.replace_with('')
        property_info_structured = get_empty_property_info()
        property_info_structured["info_url"] = f"{starting_url}{property_id}"
        # Grab all property details
        property_detail = OrderedDict({section.get("id"): section for section in property_soup.find_all("div", class_="details")})
        # Extract the basic details into a dictionary
        basic_details = [detail for detail in property_detail["propertyDetails"].find_all("td") if "detailTitle" not in detail.get("class", []) and bool(str(detail.string).strip())]
        stripped_details = []
        for detail in basic_details:
            if len(detail.contents) == 1:
                stripped_details.append(re.sub(r'\s+', ' ', str(detail.string).strip()))
            else:
                stripped_details.append(re.sub(r'\s+', ' ', ''.join(detail.contents)))
        basic_details = stripped_details
        basic_details_dict = OrderedDict()
        for i, detail in enumerate(basic_details):
            if detail is not None and detail.endswith(":"):
                detail_val = basic_details[i+1] if i+1 < len(basic_details) else ""
                basic_details_dict.update({convert_key(detail.replace(":", "")): detail_val})
        # Only scrape real, single family properties
        if basic_details_dict["type"] != "Real" or basic_details_dict["property_use_description"] != "Single Family":
            if not quiet:
                print(f"\n[red bold]ERROR: Non-real property {property_id} detected!")
            continue
        property_info_structured.update(basic_details_dict)
        # Extract the values details into a dictionary
        values_details = [str(detail.string).strip() for detail in property_detail["valuesDetails"].find_all("td")]
        values_details = [detail for detail in values_details if detail and '-------' not in detail]
        values_details_dict = OrderedDict()
        for i, detail in enumerate(values_details):
            if detail is not None and detail.endswith(":"):
                values_details_dict.update({convert_key(detail.split(" ", 1)[1].replace(":", "")): currency_str_convert(values_details[i + 2])})
        property_info_structured.update(values_details_dict)
        # Extract the improvement details
        all_improvements = []
        improvement_headers = [detail for detail in property_detail["improvementBuildingDetails"].find_all("table", class_="improvements")]
        improvement_details = [detail for detail in property_detail["improvementBuildingDetails"].find_all("table", class_="improvementDetails")]
        total_living_area = 0
        num_improvements = 0
        for headers, details in zip(improvement_headers, improvement_details):
            num_improvements += 1
            improvements_dict = OrderedDict({re.sub(r'\#\d', 'type', convert_key(key.string)): str(detail.string).strip() for key, detail in zip(headers.find_all("th"), headers.find_all("td"))})
            improvements_dict["property_id"] = property_info_structured["property_id"]
            improvements_dict["improvement_id"] = f"{improvements_dict['property_id']}-{num_improvements}"
            try:
                improvements_dict["living_area"] = int(float(improvements_dict["living_area"].replace(" sqft", "")))
            except ValueError:
                improvements_dict["living_area"] = 0
            total_living_area += improvements_dict["living_area"]
            improvements_dict["value"] = currency_str_convert(improvements_dict["value"])
            improvements_dict["details"] = []
            improvement_detail_headers = [detail.string for detail in details.find_all("th")]
            improvement_detail_rows = [detail.find_all("td", class_="") for detail in details.find_all("tr") if detail.find_all("td", class_="")]
            for row in improvement_detail_rows:
                row = [detail.string for detail in row]
                improvement_details_dict = OrderedDict({convert_key(key): value for key, value in zip(improvement_detail_headers, row)})
                improvement_details_dict['year_built'] = int(improvement_details_dict['year_built'])
                improvement_details_dict['sqft'] = int(float(improvement_details_dict['sqft']))
                if improvement_details_dict["description"] == "Living Area":
                    property_info_structured["year_built"] = improvement_details_dict["year_built"]
                improvement_details_dict["improvement_id"] = improvements_dict["improvement_id"]
                improvements_dict["details"].append(improvement_details_dict)
            all_improvements.append({convert_key(key):value for key, value in improvements_dict.items()})
        property_info_structured.update({"improvements": all_improvements})
        property_info_structured["living_area"] = total_living_area
        if not property_info_structured.get("year_built"):
            property_info_structured["year_built"] = 0
        # Extract the land details
        land_details = OrderedDict({f"land_{convert_key(key.string)}": value.string.strip() for key, value in zip(property_detail["landDetails"].find_all("th"), property_detail["landDetails"].find_all("td"))})
        if land_details:
            land_details.pop("land_#")
            land_details["land_acres"] = float(land_details["land_acres"])
            land_details["land_sqft"] = int(float(land_details["land_sqft"]))
            land_details["land_eff_front"] = int(float(land_details["land_eff_front"]))
            land_details["land_eff_depth"] = int(float(land_details["land_eff_depth"]))
            land_details["land_market_value"] = currency_str_convert(land_details["land_market_value"])
            land_details["land_prod_value"] = currency_str_convert(land_details["land_prod_value"])
            property_info_structured.update(land_details)
        # Extract the value history
        history_list = []
        history_headers = [header.string for header in property_detail["rollHistoryDetails"].find_all("th")]
        history_rows = [record.find_all("td") for record in property_detail["rollHistoryDetails"].find_all("tr", class_="")]
        for row in history_rows:
            row = [value.string for value in row]
            row_dict = OrderedDict({convert_key(key): currency_str_convert(value.string) for key, value in zip(history_headers, row)})
            row_dict.update({"property_id": property_info_structured["property_id"]})
            history_list.append(row_dict)
        property_info_structured.update({"value_history": history_list})
        property_info_list.append(property_info_structured)
        if not quiet:
            print(f"\n[yellow bold]INFO: Scraped data for property ID {property_id}")
    return property_info_list

def get_empty_property_info():
    schema = get_scraped_data_schema()
    property_info = OrderedDict()
    for key in schema['property']:
        property_info[key] = None
    property_info['value_history'] = None
    property_info['improvements'] = None
    return property_info

def get_scraped_data_schema():
    data_schema = {
        'improvement': ['improvement_type', 'state_code', 'living_area', 'value', 'property_id', 'improvement_id'],
        'improvement_details': ['type', 'description', 'class_cd', 'exterior_wall', 'year_built', 'sqft', 'improvement_id'],
        'value_history': ['year', 'improvements', 'land_market', 'ag_valuation', 'appraised', 'hs_cap', 'assessed', 'property_id'],
        'property': [
            'info_url',
            'property_id',
            'legal_description',
            'geographic_id',
            'zoning',
            'type',
            'agent_code',
            'property_use_code',
            'property_use_description',
            'protest_status',
            'informal_date',
            'formal_date',
            'address',
            'mapsco',
            'neighborhood',
            'map_id',
            'neighborhood_cd',
            'name',
            'owner_id',
            'mailing_address',
            'percent_ownership',
            'exemptions',
            'improvement_homesite_value',
            'improvement_non_homesite_value',
            'land_homesite_value',
            'land_non_homesite_value',
            'agricultural_market_valuation',
            'timber_market_valuation',
            'market_value',
            'ag_or_timber_use_value_reduction',
            'appraised_value',
            'hs_cap',
            'assessed_value',
            'year_built',
            'living_area',
            'land_type',
            'land_description',
            'land_acres',
            'land_sqft',
            'land_eff_front',
            'land_eff_depth',
            'land_market_value',
            'land_prod_value',
            'parent_property_id'
        ]
    }
    return data_schema