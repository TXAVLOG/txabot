from pytz import timezone
import requests
import threading
import os
import glob
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core.bot_sys import is_admin, read_settings, write_settings
from zlapi.models import *

vn_tz = timezone('Asia/Ho_Chi_Minh')

locations = {
    'Hà Nội': {'latitude': 21.0285, 'longitude': 105.804},
    'Hồ Chí Minh': {'latitude': 10.8231, 'longitude': 106.6297},
    'Đà Nẵng': {'latitude': 16.0471, 'longitude': 108.2068},
    'Cần Thơ': {'latitude': 10.0457, 'longitude': 105.7469},
    'Hải Phòng': {'latitude': 20.8443, 'longitude': 106.6881},
    'An Giang': {'latitude': 10.4515, 'longitude': 105.0719},
    'Bà Rịa – Vũng Tàu': {'latitude': 10.4285, 'longitude': 107.2155},
    'Bắc Giang': {'latitude': 21.2716, 'longitude': 106.1942},
    'Bắc Kạn': {'latitude': 22.0049, 'longitude': 105.8494},
    'Bạc Liêu': {'latitude': 9.2896, 'longitude': 105.7171},
    'Bến Tre': {'latitude': 10.2435, 'longitude': 106.3776},
    'Bình Định': {'latitude': 13.0805, 'longitude': 109.2007},
    'Bình Dương': {'latitude': 10.9639, 'longitude': 106.6678},
    'Bình Phước': {'latitude': 11.2898, 'longitude': 106.9397},
    'Bình Thuận': {'latitude': 10.9333, 'longitude': 108.1097},
    'Cao Bằng': {'latitude': 22.6584, 'longitude': 106.2892},
    'Đắk Lắk': {'latitude': 12.6893, 'longitude': 108.0744},
    'Đắk Nông': {'latitude': 12.0104, 'longitude': 107.8124},
    'Điện Biên': {'latitude': 21.0291, 'longitude': 103.0061},
    'Đồng Nai': {'latitude': 10.9625, 'longitude': 106.6823},
    'Đồng Tháp': {'latitude': 10.4602, 'longitude': 105.7087},
    'Gia Lai': {'latitude': 13.9281, 'longitude': 108.0809},
    'Hà Giang': {'latitude': 22.1545, 'longitude': 104.9862},
    'Hà Nam': {'latitude': 20.5726, 'longitude': 105.8907},
    'Hà Tĩnh': {'latitude': 18.3389, 'longitude': 105.9114},
    'Hải Dương': {'latitude': 20.9294, 'longitude': 106.3181},
    'Hòa Bình': {'latitude': 20.8045, 'longitude': 105.3421},
    'Hưng Yên': {'latitude': 20.9241, 'longitude': 106.0671},
    'Khánh Hòa': {'latitude': 12.2389, 'longitude': 109.1967},
    'Kiên Giang': {'latitude': 10.0109, 'longitude': 104.1043},
    'Kon Tum': {'latitude': 13.0129, 'longitude': 108.0252},
    'Lai Châu': {'latitude': 22.3364, 'longitude': 103.3227},
    'Lâm Đồng': {'latitude': 11.9402, 'longitude': 108.4557},
    'Lạng Sơn': {'latitude': 21.8449, 'longitude': 106.7715},
    'Lào Cai': {'latitude': 22.4799, 'longitude': 103.9821},
    'Long An': {'latitude': 10.5695, 'longitude': 106.4204},
    'Nam Định': {'latitude': 20.4097, 'longitude': 106.1638},
    'Nghệ An': {'latitude': 19.2833, 'longitude': 104.2231},
    'Ninh Bình': {'latitude': 20.2583, 'longitude': 105.9762},
    'Ninh Thuận': {'latitude': 11.5971, 'longitude': 108.9305},
    'Phú Thọ': {'latitude': 21.3103, 'longitude': 105.1919},
    'Phú Yên': {'latitude': 13.0902, 'longitude': 109.3082},
    'Quảng Bình': {'latitude': 17.4905, 'longitude': 106.5991},
    'Quảng Nam': {'latitude': 15.5968, 'longitude': 108.2736},
    'Quảng Ngãi': {'latitude': 15.1312, 'longitude': 108.8055},
    'Quảng Ninh': {'latitude': 21.0469, 'longitude': 107.0837},
    'Sóc Trăng': {'latitude': 9.5951, 'longitude': 105.9719},
    'Sơn La': {'latitude': 21.3144, 'longitude': 103.9005},
    'Tây Ninh': {'latitude': 11.5576, 'longitude': 106.1349},
    'Thái Bình': {'latitude': 20.4469, 'longitude': 106.3384},
    'Thái Nguyên': {'latitude': 21.5976, 'longitude': 105.8427},
    'Thanh Hóa': {'latitude': 19.8052, 'longitude': 105.7847},
    'Thừa Thiên – Huế': {'latitude': 16.4633, 'longitude': 107.5952},
    'Tiền Giang': {'latitude': 10.4574, 'longitude': 106.3501},
    'Trà Vinh': {'latitude': 9.9372, 'longitude': 106.3506},
    'Tuyên Quang': {'latitude': 21.8251, 'longitude': 105.2234},
    'Vĩnh Long': {'latitude': 10.2534, 'longitude': 105.9702},
    'Vĩnh Phúc': {'latitude': 21.3279, 'longitude': 105.5496},
    'Yên Bái': {'latitude': 21.7155, 'longitude': 104.9053},
    'Afghanistan': {'latitude': 34.5553, 'longitude': 69.2075},
    'Albania': {'latitude': 41.3275, 'longitude': 19.8189},
    'Algeria': {'latitude': 36.7377, 'longitude': 3.0866},
    'Andorra': {'latitude': 42.5078, 'longitude': 1.5211},
    'Angola': {'latitude': -8.839, 'longitude': 13.2894},
    'Antigua and Barbuda': {'latitude': 17.1274, 'longitude': -61.8468},
    'Argentina': {'latitude': -34.6037, 'longitude': -58.3816},
    'Armenia': {'latitude': 40.1792, 'longitude': 44.4991},
    'Australia': {'latitude': -35.2809, 'longitude': 149.1300},
    'Austria': {'latitude': 48.2082, 'longitude': 16.3738},
    'Azerbaijan': {'latitude': 40.4093, 'longitude': 49.8671},
    'Bahamas': {'latitude': 25.0343, 'longitude': -77.3963},
    'Bahrain': {'latitude': 26.2235, 'longitude': 50.5876},
    'Bangladesh': {'latitude': 23.8103, 'longitude': 90.4125},
    'Barbados': {'latitude': 13.1939, 'longitude': -59.5432},
    'Belarus': {'latitude': 53.9, 'longitude': 27.5667},
    'Belgium': {'latitude': 50.8503, 'longitude': 4.3517},
    'Belize': {'latitude': 17.1899, 'longitude': -88.4976},
    'Benin': {'latitude': 6.3763, 'longitude': 2.4021},
    'Bhutan': {'latitude': 27.4728, 'longitude': 89.6395},
    'Bolivia': {'latitude': -16.5000, 'longitude': -68.1193},
    'Bosnia and Herzegovina': {'latitude': 43.8486, 'longitude': 18.3564},
    'Botswana': {'latitude': -24.6584, 'longitude': 25.9087},
    'Brazil': {'latitude': -15.7801, 'longitude': -47.9292},
    'Brunei': {'latitude': 4.5353, 'longitude': 114.7277},
    'Bulgaria': {'latitude': 42.6977, 'longitude': 23.3219},
    'Burkina Faso': {'latitude': 12.2383, 'longitude': -1.5616},
    'Burundi': {'latitude': -3.3731, 'longitude': 29.9189},
    'Cabo Verde': {'latitude': 14.933, 'longitude': -23.5133},
    'Cambodia': {'latitude': 11.5624, 'longitude': 104.9259},
    'Cameroon': {'latitude': 3.848, 'longitude': 11.5021},
    'Canada': {'latitude': 45.4215, 'longitude': -75.6992},
    'Central African Republic': {'latitude': 4.3947, 'longitude': 18.5582},
    'Chad': {'latitude': 12.1348, 'longitude': 15.0557},
    'Chile': {'latitude': -33.4489, 'longitude': -70.6693},
    'China': {'latitude': 39.9042, 'longitude': 116.4074},
    'Colombia': {'latitude': 4.7110, 'longitude': -74.0721},
    'Comoros': {'latitude': -11.6455, 'longitude': 43.3333},
    'Congo (Congo-Brazzaville)': {'latitude': -4.4419, 'longitude': 15.2663},
    'Costa Rica': {'latitude': 9.9281, 'longitude': -84.0907},
    'Croatia': {'latitude': 45.1, 'longitude': 15.2},
    'Cuba': {'latitude': 23.1136, 'longitude': -82.3666},
    'Cyprus': {'latitude': 35.1264, 'longitude': 33.4299},
    'Czech Republic': {'latitude': 50.0755, 'longitude': 14.4378},
    'Denmark': {'latitude': 55.6761, 'longitude': 12.5683},
    'Djibouti': {'latitude': 11.8251, 'longitude': 42.5903},
    'Dominica': {'latitude': 15.4149, 'longitude': -61.3704},
    'Dominican Republic': {'latitude': 18.7357, 'longitude': -70.1627},
    'Ecuador': {'latitude': -0.1807, 'longitude': -78.4678},
    'Egypt': {'latitude': 30.0444, 'longitude': 31.2357},
    'El Salvador': {'latitude': 13.6929, 'longitude': -89.2182},
    'Equatorial Guinea': {'latitude': 3.7492, 'longitude': 8.7379},
    'Eritrea': {'latitude': 15.332, 'longitude': 38.013},
    'Estonia': {'latitude': 59.437, 'longitude': 24.7535},
    'Eswatini': {'latitude': -26.5225, 'longitude': 31.4659},
    'Ethiopia': {'latitude': 9.145, 'longitude': 40.4897},
    'Fiji': {'latitude': -18.1248, 'longitude': 178.0650},
    'Finland': {'latitude': 60.1692, 'longitude': 24.9402},
    'France': {'latitude': 48.8566, 'longitude': 2.3522},
    'Gabon': {'latitude': 0.4162, 'longitude': 9.4673},
    'Gambia': {'latitude': 13.4549, 'longitude': -16.5790},
    'Georgia': {'latitude': 41.7151, 'longitude': 44.8271},
    'Germany': {'latitude': 52.5200, 'longitude': 13.4050},
    'Ghana': {'latitude': 5.6037, 'longitude': -0.1870},
    'Greece': {'latitude': 37.9838, 'longitude': 23.7275},
    'Grenada': {'latitude': 12.1165, 'longitude': -61.6790},
    'Guatemala': {'latitude': 14.6349, 'longitude': -90.5069},
    'Guinea': {'latitude': 9.9456, 'longitude': -9.6966},
    'Guinea-Bissau': {'latitude': 11.8037, 'longitude': -15.1804},
    'Guyana': {'latitude': 6.8013, 'longitude': -58.1550},
    'Haiti': {'latitude': 18.5944, 'longitude': -72.3074},
    'Honduras': {'latitude': 13.9431, 'longitude': -83.0000},
    'Hungary': {'latitude': 47.4979, 'longitude': 19.0402},
    'Iceland': {'latitude': 64.1355, 'longitude': -21.8954},
    'India': {'latitude': 28.6139, 'longitude': 77.2090},
    'Indonesia': {'latitude': -6.2088, 'longitude': 106.8456},
    'Iran': {'latitude': 35.6892, 'longitude': 51.3890},
    'Iraq': {'latitude': 33.3152, 'longitude': 44.3661},
    'Ireland': {'latitude': 53.3498, 'longitude': -6.2603},
    'Israel': {'latitude': 31.7683, 'longitude': 35.2137},
    'Italy': {'latitude': 41.9028, 'longitude': 12.4964},
    'Jamaica': {'latitude': 18.1096, 'longitude': -77.2975},
    'Japan': {'latitude': 35.6762, 'longitude': 139.6503},
    'Jordan': {'latitude': 31.9634, 'longitude': 35.9300},
    'Kazakhstan': {'latitude': 51.1694, 'longitude': 71.4491},
    'Kenya': {'latitude': -1.2867, 'longitude': 36.8219},
    'Kiribati': {'latitude': -1.4515, 'longitude': 173.0322},
    'Korea North': {'latitude': 39.0392, 'longitude': 125.7625},
    'Korea South': {'latitude': 37.5665, 'longitude': 126.9780},
    'Kuwait': {'latitude': 29.3759, 'longitude': 47.9774},
    'Kyrgyzstan': {'latitude': 42.8746, 'longitude': 74.6126},
    'Laos': {'latitude': 17.9757, 'longitude': 102.6331},
    'Latvia': {'latitude': 56.946, 'longitude': 24.1059},
    'Lebanon': {'latitude': 33.8886, 'longitude': 35.4955},
    'Lesotho': {'latitude': -29.6094, 'longitude': 28.2336},
    'Liberia': {'latitude': 6.4281, 'longitude': -9.4295},
    'Libya': {'latitude': 32.8872, 'longitude': 13.1913},
    'Liechtenstein': {'latitude': 47.1415, 'longitude': 9.5215},
    'Identity': {'latitude': 54.6892, 'longitude': 25.2798},
    'Luxembourg': {'latitude': 49.6117, 'longitude': 6.13},
    'Madagascar': {'latitude': -18.8792, 'longitude': 47.5079},
    'Malawi': {'latitude': -13.2543, 'longitude': 34.3015},
    'Malaysia': {'latitude': 3.139, 'longitude': 101.6869},
    'Maldives': {'latitude': 3.2028, 'longitude': 73.2207},
    'Mali': {'latitude': 12.6392, 'longitude': -8.0029},
    'Malta': {'latitude': 35.8997, 'longitude': 14.5147},
    'Marshall Islands': {'latitude': 7.094, 'longitude': 171.3802},
    'Mauritania': {'latitude': 18.075, 'longitude': -15.9795},
    'Mauritius': {'latitude': -20.2290, 'longitude': 57.5050},
    'Mexico': {'latitude': 19.4326, 'longitude': -99.1332},
    'Micronesia': {'latitude': 6.9206, 'longitude': 158.2491},
    'Moldova': {'latitude': 47.0105, 'longitude': 28.8638},
    'Monaco': {'latitude': 43.7333, 'longitude': 7.4167},
    'Mongolia': {'latitude': 47.8864, 'longitude': 106.9057},
    'Montenegro': {'latitude': 42.4411, 'longitude': 19.2636},
    'Morocco': {'latitude': 34.020882, 'longitude': -6.84165},
    'Mozambique': {'latitude': -25.9664, 'longitude': 32.5892},
    'Myanmar': {'latitude': 16.8409, 'longitude': 96.1735},
    'Namibia': {'latitude': -22.5597, 'longitude': 17.0832},
    'Nauru': {'latitude': -0.5477, 'longitude': 166.9200},
    'Nepal': {'latitude': 27.7172, 'longitude': 85.3240},
    'Netherlands': {'latitude': 52.3676, 'longitude': 4.9041},
    'New Zealand': {'latitude': -36.8485, 'longitude': 174.7633},
    'Nicaragua': {'latitude': 12.1364, 'longitude': -86.2512},
    'Niger': {'latitude': 13.5128, 'longitude': 2.1128},
    'Nigeria': {'latitude': 9.082, 'longitude': 8.6753},
    'North Macedonia': {'latitude': 41.9981, 'longitude': 21.4254},
    'Norway': {'latitude': 59.9139, 'longitude': 10.7461},
    'Oman': {'latitude': 23.585, 'longitude': 58.4059},
    'Pakistan': {'latitude': 33.6844, 'longitude': 73.0479},
    'Palau': {'latitude': 7.51498, 'longitude': 134.5825},
    'Panama': {'latitude': 8.9824, 'longitude': -79.5190},
    'Papua New Guinea': {'latitude': -9.4438, 'longitude': 147.1803},
    'Paraguay': {'latitude': -25.2637, 'longitude': -57.5759},
    'Peru': {'latitude': -12.0464, 'longitude': -77.0428},
    'Philippines': {'latitude': 14.5995, 'longitude': 120.9842},
    'Poland': {'latitude': 52.2298, 'longitude': 21.0118},
    'Portugal': {'latitude': 38.7169, 'longitude': -9.1395},
    'Qatar': {'latitude': 25.276987, 'longitude': 51.520008},
    'Romania': {'latitude': 44.4268, 'longitude': 26.1025},
    'Russia': {'latitude': 55.7558, 'longitude': 37.6173},
    'Rwanda': {'latitude': -1.9403, 'longitude': 29.8739},
    'Saint Kitts and Nevis': {'latitude': 17.3576, 'longitude': -62.7834},
    'Saint Lucia': {'latitude': 13.9094, 'longitude': -60.9789},
    'Saint Vincent and the Grenadines': {'latitude': 13.2528, 'longitude': -61.1977},
    'Samoa': {'latitude': -13.7590, 'longitude': -172.1046},
    'San Marino': {'latitude': 43.9333, 'longitude': 12.45},
    'São Tomé and Príncipe': {'latitude': 0.1864, 'longitude': 6.6131},
    'Saudi Arabia': {'latitude': 24.7136, 'longitude': 46.6753},
    'Senegal': {'latitude': 14.6928, 'longitude': -17.4467},
    'Serbia': {'latitude': 44.8176, 'longitude': 20.4633},
    'Seychelles': {'latitude': -4.6293, 'longitude': 55.4510},
    'Sierra Leone': {'latitude': 8.4657, 'longitude': -13.2317},
    'Singapore': {'latitude': 1.3521, 'longitude': 103.8198},
    'Slovakia': {'latitude': 48.1482, 'longitude': 17.1067},
    'Slovenia': {'latitude': 46.0511, 'longitude': 14.5051},
    'Solomon Islands': {'latitude': -9.4295, 'longitude': 160.0101},
    'Somalia': {'latitude': 2.0469, 'longitude': 45.3182},
    'South Africa': {'latitude': -25.7461, 'longitude': 28.1881},
    'South Sudan': {'latitude': 4.8594, 'longitude': 31.5712},
    'Spain': {'latitude': 40.4168, 'longitude': -3.7038},
    'Sri Lanka': {'latitude': 6.9271, 'longitude': 79.8612},
    'Sudan': {'latitude': 15.5007, 'longitude': 32.5599},
    'Suriname': {'latitude': 5.8661, 'longitude': -55.1711},
    'Sweden': {'latitude': 59.3293, 'longitude': 18.0686},
    'Switzerland': {'latitude': 46.9481, 'longitude': 7.4474},
    'Syria': {'latitude': 33.5138, 'longitude': 36.2765},
    'Taiwan': {'latitude': 25.0329, 'longitude': 121.5654},
    'Tajikistan': {'latitude': 38.5367, 'longitude': 68.7791},
    'Tanzania': {'latitude': -6.7924, 'longitude': 39.2083},
    'Thailand': {'latitude': 13.7563, 'longitude': 100.5018},
    'Timor-Leste': {'latitude': -8.5569, 'longitude': 125.5872},
    'Togo': {'latitude': 6.1725, 'longitude': 1.2315},
    'Tonga': {'latitude': -21.1789, 'longitude': -175.1982},
    'Trinidad and Tobago': {'latitude': 10.6918, 'longitude': -61.2225},
    'Tunisia': {'latitude': 36.8065, 'longitude': 10.1815},
    'Turkey': {'latitude': 41.0082, 'longitude': 28.9784},
    'Turkmenistan': {'latitude': 37.9601, 'longitude': 58.3792},
    'Tuvalu': {'latitude': -7.1095, 'longitude': 179.1940},
    'Uganda': {'latitude': 0.3136, 'longitude': 32.5810},
    'Ukraine': {'latitude': 50.4501, 'longitude': 30.5236},
    'United Arab Emirates': {'latitude': 23.4241, 'longitude': 53.8478},
    'United Kingdom': {'latitude': 51.5074, 'longitude': -0.1278},
    'United States': {'latitude': 38.9072, 'longitude': -77.0369},
    'Uruguay': {'latitude': -34.9011, 'longitude': -56.1645},
    'Uzbekistan': {'latitude': 41.2995, 'longitude': 69.2401},
    'Vanuatu': {'latitude': -17.7333, 'longitude': 168.3219},
    'Vatican City': {'latitude': 41.9029, 'longitude': 12.4534},
    'Venezuela': {'latitude': 10.4806, 'longitude': -66.8772},
    'Vietnam': {'latitude': 21.0285, 'longitude': 105.804},
    'Yemen': {'latitude': 15.3694, 'longitude': 44.1910},
    'Zambia': {'latitude': -15.3875, 'longitude': 28.3228},
    'Zimbabwe': {'latitude': -17.8292, 'longitude': 31.0522},
}

def remove_accents(input_str):
    s1 = u'ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹ'
    s0 = u'AAAAEEEIIOOOOUUYaaaaeeeiiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYyYy'
    for i in range(len(s1)):
        input_str = input_str.replace(s1[i], s0[i])
    return input_str

def search_location_coords(query):
    query_clean = query.strip().lower()
    for loc in locations:
        if loc.lower() == query_clean:
            return loc, locations[loc]['latitude'], locations[loc]['longitude']
            
    query_no_accent = remove_accents(query_clean)
    for loc in locations:
        loc_no_accent = remove_accents(loc.lower())
        if loc_no_accent == query_no_accent:
            return loc, locations[loc]['latitude'], locations[loc]['longitude']
            
    for loc in locations:
        loc_no_accent = remove_accents(loc.lower())
        if query_no_accent in loc_no_accent or loc_no_accent in query_no_accent:
            return loc, locations[loc]['latitude'], locations[loc]['longitude']
            
    try:
        import urllib.parse
        quoted_query = urllib.parse.quote(query)
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={quoted_query}&count=1&language=vi"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                result = data['results'][0]
                name = result.get('name', query)
                country = result.get('country', '')
                full_name = f"{name}, {country}" if country else name
                return full_name, result['latitude'], result['longitude']
    except Exception as e:
        print(f"[ERROR] Geocoding API error: {e}")
        
    return None, None, None

def fetch_weather_open_meteo(latitude, longitude):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}&"
        f"current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,snowfall,weather_code,wind_speed_10m,visibility,is_day&"
        f"hourly=temperature_2m,weather_code,precipitation_probability,relative_humidity_2m,dew_point_2m&"
        f"daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&"
        f"timezone=Asia%2FBangkok"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Fetch weather from open-meteo failed: {e}")
        return None

wmo_weather_info = {
    0: {"desc": "Trời quang", "icon": "sunny.png"},
    1: {"desc": "Chủ yếu trời quang", "icon": "partly_cloudy.png"},
    2: {"desc": "Mây rải rác", "icon": "partly_cloudy.png"},
    3: {"desc": "Mây nhiều", "icon": "cloudy.png"},
    45: {"desc": "Sương mù", "icon": "fog.png"},
    48: {"desc": "Sương mù đóng băng", "icon": "fog.png"},
    51: {"desc": "Mưa phùn nhẹ", "icon": "rain.png"},
    53: {"desc": "Mưa phùn vừa", "icon": "rain.png"},
    55: {"desc": "Mưa phùn dày", "icon": "rain.png"},
    56: {"desc": "Mưa phùn đóng băng nhẹ", "icon": "rain.png"},
    57: {"desc": "Mưa phùn đóng băng dày", "icon": "rain.png"},
    61: {"desc": "Mưa nhẹ", "icon": "rain.png"},
    63: {"desc": "Mưa vừa", "icon": "rain.png"},
    65: {"desc": "Mưa lớn", "icon": "rain.png"},
    66: {"desc": "Mưa đóng băng nhẹ", "icon": "rain.png"},
    67: {"desc": "Mưa đóng băng mạnh", "icon": "rain.png"},
    71: {"desc": "Tuyết rơi nhẹ", "icon": "snow.png"},
    73: {"desc": "Tuyết rơi vừa", "icon": "snow.png"},
    75: {"desc": "Tuyết rơi dày", "icon": "snow.png"},
    77: {"desc": "Hạt tuyết", "icon": "snow.png"},
    80: {"desc": "Mưa rào nhẹ", "icon": "rain.png"},
    81: {"desc": "Mưa rào vừa", "icon": "rain.png"},
    82: {"desc": "Mưa rào lớn", "icon": "rain.png"},
    85: {"desc": "Mưa tuyết nhẹ", "icon": "snow.png"},
    86: {"desc": "Mưa tuyết lớn", "icon": "snow.png"},
    95: {"desc": "Giông bão", "icon": "thunderstorms.png"},
    96: {"desc": "Giông bão kèm mưa đá nhẹ", "icon": "thunderstorms.png"},
    99: {"desc": "Giông bão kèm mưa đá nặng", "icon": "thunderstorms.png"}
}

def get_wmo_info(code, is_day=1):
    info = wmo_weather_info.get(code, {"desc": "Thời tiết không xác định", "icon": "partly_cloudy.png"})
    desc = info["desc"]
    icon = info["icon"]
    if not is_day:
        if icon == "sunny.png":
            icon = "clear_night.png"
            if desc == "Trời quang":
                desc = "Trời quang (Đêm)"
        elif icon == "partly_cloudy.png":
            icon = "partly_cloudy_night.png"
            if desc == "Chủ yếu trời quang":
                desc = "Trời quang (Đêm)"
            elif desc == "Mây rải rác":
                desc = "Mây ít (Đêm)"
    return {"desc": desc, "icon": icon}

def get_emoji_font(size):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    path = os.path.join(BASE_DIR, "font", "emoji.ttf")
    if not os.path.exists(path):
        path = os.path.join(BASE_DIR, "font", "NotoEmoji-Bold.ttf")
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            return None
    return None

def draw_centered_text(draw, text, center_x, y, font, fill_color, shadow_color=None, shadow_offset=(2, 2)):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    start_x = center_x - w // 2
    if shadow_color:
        draw.text((start_x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
    draw.text((start_x, y), text, font=font, fill=fill_color)

def draw_centered_multiline_text(draw, text, center_x, start_y, font, fill_color, line_spacing=5):
    lines = text.split('\n')
    current_y = start_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        start_x = center_x - w // 2
        draw.text((start_x, current_y), line, font=font, fill=fill_color)
        current_y += (h + line_spacing)

def draw_centered_mixed_text(draw, text, center_x, y, font_text, font_emoji, fill_color, shadow_color=None, shadow_offset=(2, 2)):
    import emoji
    parts = []
    current_part = ""
    for char in text:
        if char == '\ufe0f':
            continue
        if emoji.is_emoji(char):
            if current_part:
                parts.append((current_part, False))
                current_part = ""
            parts.append((char, True))
        else:
            current_part += char
    if current_part:
        parts.append((current_part, False))
        
    total_w = 0
    part_widths = []
    for part, is_emoji in parts:
        font = font_emoji if (is_emoji and font_emoji) else font_text
        bbox = draw.textbbox((0, 0), part, font=font)
        w = bbox[2] - bbox[0]
        part_widths.append(w)
        total_w += w
        
    current_x = center_x - total_w // 2
    for (part, is_emoji), w in zip(parts, part_widths):
        font = font_emoji if (is_emoji and font_emoji) else font_text
        y_offset = 2 if is_emoji else 0
        if shadow_color:
            draw.text((current_x + shadow_offset[0], y + shadow_offset[1] + y_offset), part, font=font, fill=shadow_color)
        draw.text((current_x, y + y_offset), part, font=font, fill=fill_color)
        current_x += w

def wrap_text(text, max_chars_per_line=10):
    words = text.split(' ')
    lines = []
    current_line = []
    current_len = 0
    for word in words:
        if current_len + len(word) > max_chars_per_line:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_len = len(word)
        else:
            current_line.append(word)
            current_len += len(word) + 1
    if current_line:
        lines.append(' '.join(current_line))
    return '\n'.join(lines)

def draw_thermometer(draw, x, y, w, h, temp, liquid_color=(230, 50, 50, 255)):
    # x, y: tọa độ góc trên bên trái của nhiệt kế
    # w: độ rộng (ví dụ 30)
    # h: chiều cao (ví dụ 130)
    # temp: nhiệt độ hiện tại (ví dụ 28)
    
    # Giới hạn nhiệt độ từ -10 đến 50 độ C
    temp_clamped = max(-10, min(50, temp))
    
    # Màu sắc
    border_color = (255, 255, 255, 220)
    fill_bg = (100, 100, 100, 60)      # Nền ống thủy tinh (xám mờ)
    
    # Các thông số hình học
    r_bulb = w // 2                   # Bán kính bầu tròn dưới
    cx = x + w // 2                   # Tâm x của ống và bầu
    cy = y + h - r_bulb               # Tâm y của bầu tròn
    
    w_tube = int(w * 0.55)            # Độ rộng ống thủy tinh
    x_tube_left = cx - w_tube // 2
    x_tube_right = cx + w_tube // 2
    y_tube_top = y + w_tube // 2      # Đỉnh ống
    y_tube_bottom = cy - r_bulb // 2  # Điểm nối với bầu tròn
    
    # 1. Vẽ nền và viền cho phần ống thủy tinh
    # Vẽ đỉnh tròn của ống
    draw.ellipse([x_tube_left, y, x_tube_right - 1, y + w_tube], fill=fill_bg, outline=border_color, width=2)
    # Vẽ thân ống chữ nhật
    draw.rectangle([x_tube_left, y + w_tube // 2, x_tube_right - 1, y_tube_bottom], fill=fill_bg, outline=border_color, width=2)
    # Vẽ bầu tròn dưới
    draw.ellipse([cx - r_bulb, cy - r_bulb, cx + r_bulb - 1, cy + r_bulb - 1], fill=fill_bg, outline=border_color, width=2)
    
    # Xóa bớt đường viền giao nhau giữa bầu và thân ống để trông liền mạch
    draw.rectangle([x_tube_left + 1, y_tube_bottom - 2, x_tube_right - 2, y_tube_bottom + 2], fill=fill_bg)
    
    # 2. Vẽ cột chất lỏng màu đỏ dâng lên dựa vào nhiệt độ
    temp_min, temp_max = -10, 50
    ratio = (temp_clamped - temp_min) / (temp_max - temp_min)
    
    # Chiều cao hoạt động của ống
    tube_active_height = y_tube_bottom - (y + w_tube // 2)
    liquid_top = y_tube_bottom - int(ratio * tube_active_height)
    
    # Vẽ bầu chất lỏng màu đỏ ở đáy
    r_bulb_inner = r_bulb - 3
    draw.ellipse([cx - r_bulb_inner, cy - r_bulb_inner, cx + r_bulb_inner - 1, cy + r_bulb_inner - 1], fill=liquid_color)
    
    # Vẽ cột chất lỏng màu đỏ trong ống
    w_tube_inner = w_tube - 4
    x_inner_left = cx - w_tube_inner // 2
    x_inner_right = cx + w_tube_inner // 2
    
    if liquid_top < y_tube_bottom:
        draw.rectangle([x_inner_left, liquid_top, x_inner_right - 1, y_tube_bottom + 1], fill=liquid_color)
        # Nếu dâng lên gần đỉnh, vẽ bo tròn đỉnh chất lỏng
        if liquid_top <= y + w_tube // 2:
            draw.ellipse([x_inner_left, liquid_top - w_tube_inner // 2, x_inner_right - 1, liquid_top + w_tube_inner // 2], fill=liquid_color)

def draw_drop_icon(draw, x, y, size=13, color=(100, 180, 255, 220)):
    cx = x + size // 2
    cy = y + int(size * 0.65)
    r = size // 3.5
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    draw.polygon([(cx - r + 0.5, cy - r // 2), (cx, y + 1), (cx + r - 0.5, cy - r // 2)], fill=color)

def draw_umbrella_icon(draw, x, y, size=15, color=(150, 210, 255, 220)):
    cx = x + size // 2
    draw.line([(cx, y + 3), (cx, y + size - 2)], fill=color, width=2)
    draw.arc([cx - 4, y + size - 5, cx, y + size - 1], start=0, end=180, fill=color, width=2)
    draw.chord([x, y + 1, x + size, y + int(size * 0.7)], start=180, end=360, fill=color)
    draw.line([(cx, y - 1), (cx, y + 2)], fill=color, width=2)

def draw_pin_icon(draw, x, y, size=16, color=(255, 100, 100, 220)):
    cx = x + size // 2
    cy = y + size // 3 + 1
    r = size // 4.5
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    draw.polygon([(cx - r + 0.5, cy), (cx, y + size - 1), (cx + r - 0.5, cy)], fill=color)
    draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(255, 255, 255, 255))

def generate_weather_image(bot, area, current, daily, hourly, latitude=None, longitude=None, elevation=None):
    # 0. Safeguard inputs against missing keys
    h_time = hourly.get('time', [])
    h_temp = hourly.get('temperature_2m', [25.0] * len(h_time))
    h_weather_code = hourly.get('weather_code', [0] * len(h_time))
    h_humidity = hourly.get('relative_humidity_2m', [70] * len(h_time))
    h_dew_point = hourly.get('dew_point_2m', [t - 4 for t in h_temp])
    h_precip_prob = hourly.get('precipitation_probability', [0] * len(h_time))

    d_time = daily.get('time', [])
    d_weather_code = daily.get('weather_code', [0] * len(d_time))
    d_temp_max = daily.get('temperature_2m_max', [30.0] * len(d_time))
    d_temp_min = daily.get('temperature_2m_min', [20.0] * len(d_time))
    d_precip_max = daily.get('precipitation_probability_max', [0] * len(d_time))

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    BACKGROUND_PATH = os.path.join(BASE_DIR, "background")
    CACHE_PATH = os.path.join(BASE_DIR, "modules", "cache")
    OUTPUT_IMAGE_PATH = os.path.join(CACHE_PATH, "weather.png")
    
    images = glob.glob(os.path.join(BACKGROUND_PATH, "*.jpg")) + \
             glob.glob(os.path.join(BACKGROUND_PATH, "*.png")) + \
             glob.glob(os.path.join(BACKGROUND_PATH, "*.jpeg"))
             
    images = [img for img in images if not os.path.basename(img).startswith(".") and "trashed" not in os.path.basename(img)]
    
    size = (1300, 940)
    if images:
        bg_image_path = random.choice(images)
        try:
            bg_image = Image.open(bg_image_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
            bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=15))
        except Exception as e:
            print(f"[ERROR] Failed to load background: {e}")
            bg_image = Image.new("RGBA", size, (30, 30, 45, 255))
    else:
        bg_image = Image.new("RGBA", size, (30, 30, 45, 255))
        
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Khôi phục màu nền card ngẫu nhiên từ danh sách màu đẹp cũ
    card_colors = [
        (188, 108, 120, 160),  # Hồng ngọc ấm
        (85, 112, 102, 160),   # Xanh rêu khói
        (90, 120, 145, 160),   # Xanh dương băng giá
        (110, 95, 135, 160),   # Tím oải hương
        (105, 105, 115, 160),  # Xám sương mù
        (190, 120, 100, 160),  # Cam san hô nhạt
        (145, 115, 95, 160)    # Nâu đất ấm
    ]
    card_color = random.choice(card_colors)
    draw.rounded_rectangle([(30, 30), (1270, 915)], radius=35, fill=card_color, outline=(255, 255, 255, 45), width=2)
    
    font_dir = os.path.join(BASE_DIR, "font")
    font_bold_path = os.path.join(font_dir, "SF-Pro.ttf")
    if not os.path.exists(font_bold_path):
        font_bold_path = os.path.join(font_dir, "NotoSans-Bold.ttf")
    if not os.path.exists(font_bold_path):
        font_bold_path = os.path.join(font_dir, "arial unicode ms.otf")
        
    font_title = ImageFont.truetype(font_bold_path, size=38)
    font_large = ImageFont.truetype(font_bold_path, size=28)
    font_medium = ImageFont.truetype(font_bold_path, size=22)
    font_small = ImageFont.truetype(font_bold_path, size=18)
    font_xsmall = ImageFont.truetype(font_bold_path, size=15)
    font_xxsmall = ImageFont.truetype(font_bold_path, size=13)
    
    # Thiết lập font có kích thước gấp đôi phục vụ Supersampling biểu đồ
    font_xsmall_x2 = ImageFont.truetype(font_bold_path, size=15 * 2)
    font_xxsmall_x2 = ImageFont.truetype(font_bold_path, size=13 * 2)
    
    # 1. HEADER
    draw.text((50, 45), "DỰ BÁO THỜI TIẾT 7 NGÀY TỚI", font=font_title, fill=(255, 225, 120, 255))
    
    lat_val = latitude if latitude is not None else 0.0
    lon_val = longitude if longitude is not None else 0.0
    elev_val = elevation if elevation is not None else 0.0
    
    # Vẽ ghim định vị
    draw_pin_icon(draw, 50, 96, size=16, color=(255, 100, 100, 220))
    draw.text((75, 95), f"Địa điểm: {area} ({lat_val:.5f}°N, {lon_val:.5f}°E)  |  Độ cao: {elev_val:.1f}m", font=font_small, fill=(235, 245, 255, 220))
        
    try:
        current_time_str = current['time']
        time_obj = datetime.strptime(current_time_str, "%Y-%m-%dT%H:%M")
        formatted_time = time_obj.strftime("%d/%m/%Y %H:%M")
    except Exception:
        formatted_time = "--/--/---- --:--"
    update_text = f"Cập nhật: {formatted_time} (GMT+7)"
    draw.rounded_rectangle([(930, 45), (1250, 85)], radius=10, fill=(30, 60, 110, 150), outline=(255, 255, 255, 80), width=1)
    draw.text((950, 53), update_text, font=font_xsmall, fill=(220, 240, 255, 230))
    
    current_temp = int(round(current['temperature_2m']))
    curr_text = f"Hiện tại: {current_temp}°C"
    draw.rounded_rectangle([(670, 45), (910, 85)], radius=10, fill=(20, 35, 65, 170), outline=(255, 255, 255, 90), width=1)
    draw.text((685, 53), curr_text, font=font_small, fill=(255, 225, 100, 255))
    draw_thermometer(draw, 872, 48, 16, 32, current_temp)
    
    # 2. DỰ BÁO 7 NGÀY TỚI (DAILY CARDS)
    icons_cache_dir = os.path.join(BASE_DIR, "modules", "cache", "weather_icons")
    
    # Khôi phục danh sách màu daily cards ngẫu nhiên từ bản cũ
    col_colors = [
        (168, 77, 126, 180),
        (85, 112, 126, 180),
        (185, 78, 97, 180),
        (92, 134, 125, 180),
        (97, 91, 144, 180),
        (95, 108, 133, 180),
        (107, 101, 89, 180)
    ]
    
    for i in range(7):
        if i >= len(d_time):
            break
            
        x1 = 50 + i * 174
        x2 = x1 + 162
        y1 = 135
        y2 = 425
        
        card_fill = col_colors[i] if i < len(col_colors) else (255, 255, 255, 30)
        draw.rounded_rectangle([(x1, y1), (x2, y2)], radius=20, fill=card_fill, outline=(255, 255, 255, 60), width=1)
        
        date_str = d_time[i]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d/%m")
        
        weekday = date_obj.weekday()
        weekday_names = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        weekday_name = weekday_names[weekday]
        
        day_color = (255, 110, 110, 255) if weekday == 6 else (255, 235, 180, 255)
        draw_centered_text(draw, weekday_name, x1 + 81, y1 + 15, font_small, day_color)
        draw_centered_text(draw, formatted_date, x1 + 81, y1 + 38, font_xsmall, (220, 240, 255, 220))
        
        day_code = d_weather_code[i]
        day_info = get_wmo_info(day_code, is_day=1)
        day_icon_name = day_info['icon']
        day_icon_path = os.path.join(icons_cache_dir, day_icon_name)
        
        if os.path.exists(day_icon_path):
            try:
                day_icon_img = Image.open(day_icon_path).convert("RGBA").resize((65, 65), Image.Resampling.LANCZOS)
                overlay.paste(day_icon_img, (x1 + (162 - 65) // 2, y1 + 68), day_icon_img)
            except Exception as e:
                print(f"[ERROR] daily card icon error: {e}")
                
        max_temp = int(round(d_temp_max[i]))
        min_temp = int(round(d_temp_min[i]))
        
        max_str = f"{max_temp}°"
        sep_str = " | "
        min_str = f"{min_temp}°"
        
        w_max = draw.textbbox((0, 0), max_str, font=font_small)[2] - draw.textbbox((0, 0), max_str, font=font_small)[0]
        w_sep = draw.textbbox((0, 0), sep_str, font=font_small)[2] - draw.textbbox((0, 0), sep_str, font=font_small)[0]
        w_min = draw.textbbox((0, 0), min_str, font=font_small)[2] - draw.textbbox((0, 0), min_str, font=font_small)[0]
        
        total_w = w_max + w_sep + w_min
        temp_start_x = (x1 + 81) - total_w // 2
        
        draw.text((temp_start_x, y1 + 145), max_str, font=font_small, fill=(255, 120, 120, 255))
        draw.text((temp_start_x + w_max, y1 + 145), sep_str, font=font_small, fill=(255, 255, 255, 150))
        draw.text((temp_start_x + w_max + w_sep, y1 + 145), min_str, font=font_small, fill=(120, 200, 255, 255))
        
        day_desc = day_info['desc']
        wrapped_desc = wrap_text(day_desc, max_chars_per_line=11)
        draw_centered_multiline_text(draw, wrapped_desc, x1 + 81, y1 + 180, font_xsmall, (240, 245, 255, 230), line_spacing=3)
        
        day_humidity_list = [h_humidity[idx] for idx, t in enumerate(h_time) if t.startswith(date_str)]
        avg_humidity = sum(day_humidity_list) / len(day_humidity_list) if day_humidity_list else 70.0
        avg_humidity = int(round(avg_humidity))
        max_precip_prob = d_precip_max[i]
        
        # Vẽ các biểu tượng vector giọt nước và ô mưa
        draw_drop_icon(draw, x1 + 12, y2 - 32, size=13, color=(100, 180, 255, 200))
        draw.text((x1 + 32, y2 - 32), f"{avg_humidity}%", font=font_xxsmall, fill=(180, 225, 255, 220))
        draw_umbrella_icon(draw, x1 + 84, y2 - 33, size=14, color=(150, 210, 255, 200))
        draw.text((x1 + 104, y2 - 32), f"{max_precip_prob}%", font=font_xxsmall, fill=(180, 225, 255, 220))
            
    # 3. DỰ BÁO THEO GIỜ & BIỂU ĐỒ ĐƯỜNG (HOURLY LINE CHART) BẰNG SUPERSAMPLING CỤC BỘ (Khử răng cưa)
    chart_w, chart_h = 1200, 260
    chart_img = Image.new("RGBA", (chart_w * 2, chart_h * 2), (0, 0, 0, 0))
    chart_draw = ImageDraw.Draw(chart_img)
    
    # Hộp viền lớn ngoài
    chart_draw.rounded_rectangle([(0, 0), (chart_w * 2, chart_h * 2)], radius=30, fill=(255, 255, 255, 15), outline=(255, 255, 255, 35), width=2)
    
    # Hộp tiêu đề DỰ BÁO THEO GIỜ
    chart_draw.rounded_rectangle([(30, 30), (320, 90)], radius=12, fill=(30, 80, 150, 200), outline=(255, 255, 255, 60), width=2)
    chart_draw.text((50, 42), "DỰ BÁO THEO GIỜ", font=font_xxsmall_x2, fill=(255, 225, 120, 255))
    
    try:
        dt_now = datetime.strptime(current['time'], "%Y-%m-%dT%H:%M")
        rounded_now_str = dt_now.strftime("%Y-%m-%dT%H:00")
        curr_idx = h_time.index(rounded_now_str)
    except Exception:
        curr_idx = 0
        
    hourly_indices = [curr_idx + idx * 3 for idx in range(9)]
    hourly_indices = [idx for idx in hourly_indices if idx < len(h_time)]
    
    # Tọa độ X cục bộ (so với x=50 của chart_y1)
    x_start_loc = 200
    x_width_loc = 960
    num_pts = len(hourly_indices)
    x_step_loc = x_width_loc / 8 if num_pts > 1 else 120
    x_coords_loc = [x_start_loc + idx * x_step_loc for idx in range(num_pts)]
    x_coords_x2 = [x * 2 for x in x_coords_loc]
    
    # Chú thích bên trái (nhãn biểu đồ)
    chart_draw.text((40, 190), "Nhiệt độ (°C)", font=font_xxsmall_x2, fill=(255, 120, 120, 240))
    chart_draw.line([(260, 204), (320, 204)], fill=(255, 100, 100, 240), width=4)
    
    chart_draw.text((40, 240), "Điểm sương (°C)", font=font_xxsmall_x2, fill=(100, 180, 255, 240))
    chart_draw.line([(260, 254), (320, 254)], fill=(100, 180, 255, 240), width=4)
    
    draw_drop_icon(chart_draw, 40, 380, size=26, color=(255, 255, 255, 200))
    chart_draw.text((80, 380), "Độ ẩm (%)", font=font_xxsmall_x2, fill=(180, 225, 255, 220))
    draw_umbrella_icon(chart_draw, 40, 440, size=28, color=(255, 255, 255, 200))
    chart_draw.text((80, 440), "Xác suất mưa (%)", font=font_xxsmall_x2, fill=(180, 225, 255, 220))
        
    temps = [h_temp[idx] for idx in hourly_indices]
    dews = [h_dew_point[idx] for idx in hourly_indices]
    
    val_min = min(temps + dews) - 2 if temps else 0
    val_max = max(temps + dews) + 2 if temps else 40
    if val_max == val_min:
        val_max += 2
        
    line_y_start_x2 = 160
    line_y_end_x2 = 320
    
    y_temp_coords_x2 = [line_y_end_x2 - (t - val_min) / (val_max - val_min) * (line_y_end_x2 - line_y_start_x2) for t in temps]
    y_dew_coords_x2 = [line_y_end_x2 - (d - val_min) / (val_max - val_min) * (line_y_end_x2 - line_y_start_x2) for d in dews]
    
    for i, idx in enumerate(hourly_indices):
        x_pt_x2 = x_coords_x2[i]
        
        hour_time = h_time[idx]
        hour_dt = datetime.strptime(hour_time, "%Y-%m-%dT%H:%M")
        hour_text = hour_dt.strftime("%H:%M")
        draw_centered_text(chart_draw, hour_text, x_pt_x2, 36, font_xsmall_x2, (255, 240, 200, 230))
        
        hour_is_day = 1 if 6 <= hour_dt.hour < 18 else 0
        h_info = get_wmo_info(h_weather_code[idx], is_day=hour_is_day)
        h_icon_path = os.path.join(icons_cache_dir, h_info['icon'])
        if os.path.exists(h_icon_path):
            try:
                h_icon_img = Image.open(h_icon_path).convert("RGBA").resize((76, 76), Image.Resampling.LANCZOS)
                chart_img.paste(h_icon_img, (int(x_pt_x2 - 38), 80), h_icon_img)
            except Exception as e:
                print(f"[ERROR] hourly chart icon paste error: {e}")
                
        humidity_val = h_humidity[idx]
        precip_val = h_precip_prob[idx]
        draw_centered_text(chart_draw, f"{humidity_val}%", x_pt_x2, 380, font_xsmall_x2, (180, 225, 255, 220))
        draw_centered_text(chart_draw, f"{precip_val}%", x_pt_x2, 440, font_xsmall_x2, (180, 225, 255, 220))
        
    for i in range(num_pts - 1):
        chart_draw.line([(x_coords_x2[i], y_temp_coords_x2[i]), (x_coords_x2[i+1], y_temp_coords_x2[i+1])], fill=(255, 100, 100, 240), width=6)
        chart_draw.line([(x_coords_x2[i], y_dew_coords_x2[i]), (x_coords_x2[i+1], y_dew_coords_x2[i+1])], fill=(100, 180, 255, 240), width=6)
        
    for i in range(num_pts):
        chart_draw.ellipse([x_coords_x2[i] - 8, y_temp_coords_x2[i] - 8, x_coords_x2[i] + 8, y_temp_coords_x2[i] + 8], fill=(255, 100, 100, 255))
        t_val = int(round(temps[i]))
        draw_centered_text(chart_draw, f"{t_val}°C", x_coords_x2[i], y_temp_coords_x2[i] - 44, font_xxsmall_x2, (255, 150, 150, 255))
        
        chart_draw.ellipse([x_coords_x2[i] - 8, y_dew_coords_x2[i] - 8, x_coords_x2[i] + 8, y_dew_coords_x2[i] + 8], fill=(100, 180, 255, 255))
        d_val = int(round(dews[i]))
        draw_centered_text(chart_draw, f"{d_val}°C", x_coords_x2[i], y_dew_coords_x2[i] + 16, font_xxsmall_x2, (150, 210, 255, 255))
        
    chart_img_resized = chart_img.resize((chart_w, chart_h), Image.Resampling.LANCZOS)
    overlay.paste(chart_img_resized, (50, 455), chart_img_resized)
        
    # 4. CHI TIẾT DƯỚI ĐÁY
    y_footer_card = 730
    h_footer_card = 145
    
    # Cột 1: GHI CHÚ
    draw.rounded_rectangle([(50, y_footer_card), (420, y_footer_card + h_footer_card)], radius=12, fill=(255, 255, 255, 15), outline=(255, 255, 255, 30), width=1)
    draw.rounded_rectangle([(65, y_footer_card + 10), (145, y_footer_card + 35)], radius=5, fill=(30, 80, 150, 200), outline=(255, 255, 255, 50), width=1)
    draw.text((77, y_footer_card + 14), "GHI CHÚ", font=font_xxsmall, fill=(255, 225, 120, 255))
    
    has_storm = any(code in [95, 96, 99] for code in d_weather_code)
    has_rain = any(code in [61, 63, 65, 80, 81, 82] for code in d_weather_code)
    max_t_week = max(d_temp_max) if d_temp_max else 30
    
    if has_storm:
        note_text = "Có giông bão xuất hiện trong tuần. Đề phòng mưa lớn cục bộ, lốc sét và gió giật mạnh."
    elif has_rain:
        note_text = "Có mưa rào rải rác trong tuần. Đề phòng thời điểm chuyển mưa đột ngột, mang theo ô dù khi ra ngoài."
    elif max_t_week > 35:
        note_text = "Trời nắng nóng gay gắt kéo dài. Hạn chế ra đường vào khung giờ trưa từ 11h - 14h và uống đủ nước."
    else:
        note_text = "Thời tiết tương đối ôn hòa, thích hợp cho các hoạt động di chuyển và hoạt động ngoài trời."
        
    wrapped_note = wrap_text(note_text, max_chars_per_line=30)
    draw_centered_multiline_text(draw, wrapped_note, 235, y_footer_card + 50, font_xsmall, (245, 250, 255, 230), line_spacing=4)
    
    # Cột 2: TỔNG QUAN 7 NGÀY
    draw.rounded_rectangle([(435, y_footer_card), (845, y_footer_card + h_footer_card)], radius=12, fill=(255, 255, 255, 15), outline=(255, 255, 255, 30), width=1)
    draw.rounded_rectangle([(450, y_footer_card + 10), (590, y_footer_card + 35)], radius=5, fill=(30, 80, 150, 200), outline=(255, 255, 255, 50), width=1)
    draw.text((460, y_footer_card + 14), "TỔNG QUAN 7 NGÀY", font=font_xxsmall, fill=(255, 225, 120, 255))
    
    max_t_all = int(round(max(d_temp_max))) if d_temp_max else 30
    min_t_all = int(round(min(d_temp_min))) if d_temp_min else 20
    
    total_humidity = sum(h_humidity) / len(h_humidity) if h_humidity else 70.0
    avg_humidity_all = int(round(total_humidity))
    
    from collections import Counter
    codes_cnt = Counter(d_weather_code)
    common_code = codes_cnt.most_common(1)[0][0] if d_weather_code else 0
    trend_desc = get_wmo_info(common_code, is_day=1)['desc']
    
    draw.text((495, y_footer_card + 53), f"Nhiệt độ cao nhất: {max_t_all}°C", font=font_xsmall, fill=(255, 245, 230, 220))
    draw_thermometer(draw, 465, y_footer_card + 48, 14, 25, max_t_all, liquid_color=(255, 90, 90, 255))
    
    draw.text((495, y_footer_card + 88), f"Nhiệt độ thấp nhất: {min_t_all}°C", font=font_xsmall, fill=(240, 250, 255, 220))
    draw_thermometer(draw, 465, y_footer_card + 83, 14, 25, min_t_all, liquid_color=(100, 180, 255, 255))
    
    draw.text((460, y_footer_card + 122), f"Độ ẩm trung bình: {avg_humidity_all}%  |  Xu hướng: {trend_desc}", font=font_xsmall, fill=(245, 250, 255, 220))
    
    # Cột 3: THANG MỨC XÁC SUẤT MƯA
    draw.rounded_rectangle([(860, y_footer_card), (1250, y_footer_card + h_footer_card)], radius=12, fill=(255, 255, 255, 15), outline=(255, 255, 255, 30), width=1)
    draw.rounded_rectangle([(875, y_footer_card + 10), (1055, y_footer_card + 35)], radius=5, fill=(30, 80, 150, 200), outline=(255, 255, 255, 50), width=1)
    draw.text((885, y_footer_card + 14), "THANG MỨC XÁC SUẤT MƯA", font=font_xxsmall, fill=(255, 225, 120, 255))
    
    draw_umbrella_icon(draw, 875, y_footer_card + 48, size=13, color=(255, 255, 255, 190))
    draw.text((898, y_footer_card + 48), "< 20%    : Rất ít khả năng mưa", font=font_xxsmall, fill=(245, 250, 255, 220))
    
    draw_umbrella_icon(draw, 875, y_footer_card + 68, size=13, color=(255, 255, 255, 190))
    draw.text((898, y_footer_card + 68), "20-50%  : Ít khả năng mưa", font=font_xxsmall, fill=(245, 250, 255, 220))
    
    draw_umbrella_icon(draw, 875, y_footer_card + 88, size=13, color=(255, 255, 255, 190))
    draw.text((898, y_footer_card + 88), "50-80%  : Có khả năng mưa vừa", font=font_xxsmall, fill=(245, 250, 255, 220))
    
    draw_umbrella_icon(draw, 875, y_footer_card + 108, size=13, color=(255, 255, 255, 190))
    draw.text((898, y_footer_card + 108), "> 80%    : Khả năng mưa rất cao", font=font_xxsmall, fill=(245, 250, 255, 220))
    
    ox = 1195
    oy = y_footer_card + 100
    draw.line([(ox, oy), (ox, oy + 32)], fill=(255, 255, 255, 200), width=3)
    draw.arc([ox - 10, oy + 28, ox, oy + 38], start=0, end=180, fill=(255, 255, 255, 200), width=3)
    draw.chord([ox - 35, oy - 25, ox + 35, oy + 10], start=180, end=360, fill=(100, 180, 255, 180), outline=(255, 255, 255, 200))
    draw.line([(ox, oy - 25), (ox, oy - 30)], fill=(255, 255, 255, 200), width=2)
    draw.line([(ox - 25, oy - 35), (ox - 22, oy - 30)], fill=(150, 210, 255, 180), width=2)
    draw.line([(ox + 28, oy - 20), (ox + 31, oy - 15)], fill=(150, 210, 255, 180), width=2)
    draw.line([(ox - 10, oy - 10), (ox - 7, oy - 5)], fill=(150, 210, 255, 180), width=2)
    
    # 5. FOOTER CHÂN TRANG
    bot_name = getattr(bot, 'me_name', 'txabot') or 'txabot'
    bot_version = getattr(bot, 'version', '1.6.7') or '1.6.7'
    footer_text = f"Bot: {bot_name}  |  Tác giả: TXA  |  Version: {bot_version}  |  Nguồn: open-meteo.com"
    draw_centered_text(draw, footer_text, 650, 887, font_xsmall, (255, 255, 255, 200))
    
    final_image = Image.alpha_composite(bg_image, overlay)
    os.makedirs(os.path.dirname(OUTPUT_IMAGE_PATH), exist_ok=True)
    final_image.save(OUTPUT_IMAGE_PATH, "PNG", quality=95)
    return OUTPUT_IMAGE_PATH

def fetch_weather_info(bot, area):
    full_name, lat, lon = search_location_coords(area)
    if not lat or not lon:
        return f"❌ Không tìm thấy tọa độ địa điểm: {area}"
        
    data = fetch_weather_open_meteo(lat, lon)
    if not data or 'current' not in data or 'daily' not in data or 'hourly' not in data:
        return "❌ Không thể lấy thông tin thời tiết từ Open-Meteo API."
        
    try:
        image_path = generate_weather_image(
            bot, full_name, data['current'], data['daily'], data['hourly'],
            latitude=data.get('latitude'), longitude=data.get('longitude'), elevation=data.get('elevation')
        )
        return image_path
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ Lỗi khi tạo ảnh thời tiết: {str(e)}"

def handle_weather_on(bot, thread_id):
    settings = read_settings(bot.uid)
    if "weather" not in settings:
        settings["weather"] = {}
    settings["weather"][thread_id] = True
    write_settings(bot.uid, settings)
    return f"🚦Lệnh {bot.prefix}weather đã được Bật 🚀 trong nhóm này ✅"

def handle_weather_off(bot, thread_id):
    settings = read_settings(bot.uid)
    if "weather" in settings and thread_id in settings["weather"]:
        settings["weather"][thread_id] = False
        write_settings(bot.uid, settings)
        return f"🚦Lệnh {bot.prefix}weather đã Tắt ⭕️ trong nhóm này ✅"
    return "🚦Nhóm chưa có thông tin cấu hình weather để ⭕️ Tắt 🤗"

def handle_weather_command(message, message_object, thread_id, thread_type, author_id, client):
    args = message.split(" ", 1)
    area = args[1].strip() if len(args) > 1 else "Đồng Nai"
    settings = read_settings(client.uid)
    
    user_message = message.replace(f"{client.prefix}weather ", "").strip().lower()
    if user_message == "on":
        if not is_admin(client, author_id):  
            response = "❌Bạn không phải admin bot!"
        else:
            response = handle_weather_on(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return
    elif user_message == "off":
        if not is_admin(client, author_id):  
            response = "❌Bạn không phải admin bot!"
        else:
            response = handle_weather_off(client, thread_id)
        client.replyMessage(Message(text=response), thread_id=thread_id, thread_type=thread_type, replyMsg=message_object)
        return
    
    if not (settings.get("weather", {}).get(thread_id, False)):
        return
        
    def send_weather():
        result = fetch_weather_info(client, area)
        try:
            if os.path.exists(result) and result.endswith(".png"):
                client.sendLocalImage(
                    imagePath=result,
                    message=Message(text=f"Thời tiết {area} của bạn đây 🐳"),
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=1300,
                    height=940,
                    ttl=240000
                )
            else:
                client.sendMessage(
                    Message(text=result),
                    thread_id,
                    thread_type,
                    ttl=120000
                )
        except Exception as e:
            error_msg = f"Lỗi khi gửi tin nhắn: {str(e)}"
            client.sendMessage(
                Message(text=error_msg),
                thread_id,
                thread_type,
                ttl=120000
            )

    weather_thread = threading.Thread(target=send_weather)
    weather_thread.start()

txa = {
    "name": "pro_weather",
    "desc": "Xem thời tiết theo địa điểm. Hỗ trợ xem dự báo thời tiết hiện tại và gửi vào nhóm. Admin có thể bật/tắt tính năng.",
    "author": "TXA",
    "command": ['weather']
}

def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()
    
    dispatch_map = {
        'weather': handle_weather_command
    }
    
    func = dispatch_map.get(cmd)
    if func:
        import inspect
        sig = inspect.signature(func)
        args_map = {
            'bot': bot,
            'client': bot,
            'message_object': message_object,
            'thread_id': thread_id,
            'thread_type': thread_type,
            'author_id': author_id,
            'message': message_text,
            'message_text': message_text,
            'message_lower': message_text.lower()
        }
        args = []
        for param_name in sig.parameters:
            if param_name in args_map:
                args.append(args_map[param_name])
            else:
                args.append(None)
        func(*args)
