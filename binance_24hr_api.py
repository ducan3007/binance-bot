import requests

URL = "http://localhost:8000/trigger-send24hrPriceChange"

if __name__ == "__main__":
    response = requests.post(URL)
    print(response.json())
