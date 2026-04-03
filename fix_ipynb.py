import json

path = './notebooks/quantize_model.ipynb'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Let's find the last occurrence of close bracket "  ]\n}"
idx = text.rfind('  ]\n}')
if idx != -1:
    fixed_text = text[:idx] + '  ],\n  "metadata": {},\n  "nbformat": 4,\n  "nbformat_minor": 0\n}\n'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(fixed_text)
    print("Fixed syntax in", path)
else:
    print("Could not find the end sequence")

# Now verify it
try:
    with open(path, 'r') as f:
        json.load(f)
    print("JSON IS VALID!")
except Exception as e:
    print("STILL INVALID:", e)
