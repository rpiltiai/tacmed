
try:
    # PowerShell > might produce UTF-16LE
    with open('repro_out.txt', 'r', encoding='utf-16') as f:
        content = f.read()
except UnicodeError:
    # Fallback to defaults
    try:
        with open('repro_out.txt', 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        with open('repro_out.txt', 'r') as f:
            content = f.read()

print(f"Content length: {len(content)}")
if "FALLBACK DETECTED" in content:
    print("MATCH: FALLBACK_DETECTED")
if "RESULT: SUCCESS" in content:
    count = content.count("RESULT: SUCCESS")
    print(f"SUCCESS_COUNT: {count}")
    
# Print first few lines
print("--- PREVIEW ---")
print(content[:500])
