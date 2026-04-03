import os
import re

with open("docker-compose.yml", "r") as f:
    text = f.read()

services = ["behavior-agent", "orchestrator", "deception-agent", "threat-intel"]

for s in services:
    text = text.replace(
        f"context: ./services/{s}\n      dockerfile: Dockerfile",
        f"context: .\n      dockerfile: ./services/{s}/Dockerfile"
    )

with open("docker-compose.yml", "w") as f:
    f.write(text)

for s in services:
    df_path = f"services/{s}/Dockerfile"
    with open(df_path, "r") as f:
        df_text = f.read()
    
    df_text = df_text.replace("COPY requirements.txt .", f"COPY services/{s}/requirements.txt .")
    
    # Remove existing shared memory copies just in case
    df_text = re.sub(r"COPY \.\./\.\./shared.*?\n", "", df_text)
    df_text = re.sub(r"COPY shared/python.*?\n", "", df_text)
    df_text = re.sub(r"ENV PYTHONPATH=.*?\n", "", df_text)
    
    # insert our new copy instead of COPY . .
    # Note: wait, if we copy shared/python /shared/python, then copy the rest
    df_text = df_text.replace("COPY . .", f"COPY shared/python /shared/python\nENV PYTHONPATH=\"/shared/python:${{PYTHONPATH}}\"\nCOPY services/{s} .")
    
    with open(df_path, "w") as f:
        f.write(df_text)

print("Done")
