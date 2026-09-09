import requests
import json

r = requests.get('http://192.168.20.196:5080/docs/parcel-lifecycle/openapi.json', timeout=5)
if r.status_code == 200:
    data = r.json()
    print(json.dumps(data.get('components', {}).get('schemas', {}), indent=2, ensure_ascii=False))