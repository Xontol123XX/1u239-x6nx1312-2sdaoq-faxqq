import json
with open("C:\\Users\\isakm\\OneDrive\\Desktop\\ArcCas\\Server\\dataManagement\\GameData\\TenorData.json", "w") as dat:
    
    default_data = {
        "crashHistory": [],
        "TenorProfit": [],
        "TenorLastBetTotal": [],
        "AvgMultiplyCashout": [],
        "TotalPlayerCashout":[]
    }
    json.dump(default_data,dat, indent=4)