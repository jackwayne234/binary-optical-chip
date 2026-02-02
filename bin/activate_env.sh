#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Add the environment bin to the PATH
export PATH="$SCRIPT_DIR/.mamba_env/bin:$PATH"

# Set SSL Certificate file for GDSFactory/PyGit2
export SSL_CERT_FILE="$SCRIPT_DIR/.mamba_env/lib/python3.11/site-packages/certifi/cacert.pem"

echo "Optical Computing Environment Activated"
echo "Python: $(which python3)"
echo "GDSFactory: Installed"
