import requests
import re

r = requests.get('http://localhost:5080/swagger/index.html', timeout=5)
print('Status:', r.status_code)

# Print the HTML to find the swagger config
print('--- HTML (first 5000 chars) ---')
print(r.text[:5000])