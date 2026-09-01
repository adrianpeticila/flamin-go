import re

with open('/Users/pc/Documents/NYX/PROJECTS/FLAMINGO/repo/b2a_gateway.py', 'r') as f:
    content = f.read()

# 1. Add import re
if 'import re' not in content:
    content = content.replace('import os', 'import os\nimport re')

# 2. Format X-Price-Amount
content = content.replace('"X-Price-Amount": str(price),', '"X-Price-Amount": f"{price:.2f}",')

# 3. Update message
old_message = '"message": "Payment required to access Flamin.go B2A intelligence endpoint",'
new_message = '"message": "Payment challenge nonce has expired. Please request a fresh challenge." if "expired" in msg.lower() else "Payment required to access Flamin.go B2A intelligence endpoint",'
content = content.replace(old_message, new_message)

with open('/Users/pc/Documents/NYX/PROJECTS/FLAMINGO/repo/b2a_gateway.py', 'w') as f:
    f.write(content)
print("Patch applied successfully.")
