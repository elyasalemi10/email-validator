#!/bin/bash
# VPS setup script - run on Ubuntu/Debian VPS (DigitalOcean, Linode, etc.)
# Port 25 is open on VPS - full SMTP validation will work

set -e
echo "=== Email Validator VPS Setup ==="

# Update system
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv git

# Clone repo (or pull if exists)
if [ -d "email-validator" ]; then
  cd email-validator && git pull
else
  git clone https://github.com/elyasalemi10/email-validator.git
  cd email-validator
fi

# Create venv and install deps
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

# Make validate script executable
chmod +x validate

echo ""
echo "=== Setup complete ==="
echo ""
echo "Quick validate single email:"
echo "  ./validate user@example.com"
echo ""
echo "Validate CSV:"
echo "  ./validate -f leads.csv -o results.csv"
echo ""
echo "Or: source venv/bin/activate && python validator.py email@example.com"
