"""Keep this local acceptance credential in the controller process only."""
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from setup_env import gateway_key
from stress.cli_campaign import main

if __name__=='__main__':
    os.environ['SIFT_ACCEPTANCE_API_KEY']=gateway_key()
    main()
