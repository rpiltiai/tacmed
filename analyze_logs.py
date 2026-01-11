
try:
    with open('tail_logs.txt', 'r', encoding='utf-8') as f:
        content = f.read()
except:
    with open('tail_logs.txt', 'r') as f:
        content = f.read()

print(f"Log length: {len(content)}")
found = False
for line in content.splitlines():
    if "Bedrock Error" in line or "Error" in line:
        print(f"FOUND ERROR: {line}")
        found = True

if not found:
    print("No errors found in captured logs.")
