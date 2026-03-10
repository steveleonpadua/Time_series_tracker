API_KEY = "YOUR_API_KEY"

BASE_URL = "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/"

PARAMS = {
    "frequency": "daily",
    "data[0]": "value",
    "sort[0][column]": "period",
    "sort[0][direction]": "desc",
    "offset": 0,
    "length": 5000
}
