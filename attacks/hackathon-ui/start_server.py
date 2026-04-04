#!/usr/bin/env python
import os
import sys
import subprocess

os.chdir(r"c:\Users\admin\zero\attacks\hackathon-ui")
sys.path.insert(0, os.getcwd())

cmd = [sys.executable, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8100"]
subprocess.run(cmd)
