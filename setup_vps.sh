#!/bin/bash
# VPS setup - run: curl -sSL https://raw.githubusercontent.com/elyasalemi10/email-validator/main/setup_vps.sh | bash

set -e
echo "=== Email Validator VPS Setup ==="

sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv git

INSTALL_DIR="${HOME}/email-validator"
if [ -d "$INSTALL_DIR" ]; then
  cd "$INSTALL_DIR" && git pull
else
  git clone https://github.com/elyasalemi10/email-validator.git "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
chmod +x validate

echo ""
echo "=== Done! ==="
echo "cd $INSTALL_DIR"
echo "./validate user@example.com"
