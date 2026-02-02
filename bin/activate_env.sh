#!/bin/bash
# Get the project root (parent of bin/)
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT="$SCRIPT_DIR/.."

# Add the environment bin to the PATH
export PATH="$PROJECT_ROOT/.mamba_env/bin:$PATH"

# Set SSL Certificate file for GDSFactory/PyGit2
export SSL_CERT_FILE="$PROJECT_ROOT/.mamba_env/lib/python3.11/site-packages/certifi/cacert.pem"

echo "Optical Computing Environment Activated"
echo "Python: $(which python3)"
echo "GDSFactory: Installed"
