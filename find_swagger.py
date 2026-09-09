import requests
import re

r = requests.get('http://192.168.20.196:5080/swagger/index.html', timeout=5)
print('Status:', r.status_code)

# Find swagger JSON URL in the HTML
urls = re.findall(r'url["\']?\s*:\s*["\']([^"\']+\.json)["\']', r.text)
for u in urls:
    print('Found URL:', u)

# Also look for swagger config
if 'urls' in r.text:
    urls2 = re.findall(r'urls\s*=\s*(\[[^\]]+\])', r.text)
    for u in urls2:
        print('urls config:', u)

# Try to find all .json references
all_json = re.findall(r'["\']([^"\']*swagger[^"\']*\.json)["\']', r.text)
for u in all_json:
    print('Swagger JSON ref:', u)

all_json2 = re.findall(r'["\']([^"\']*openapi[^"\']*\.json)["\']', r.text)
for u in all_json2:
    print('OpenAPI JSON ref:', u)