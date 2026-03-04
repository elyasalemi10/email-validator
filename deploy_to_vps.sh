#!/bin/bash
# Deploy email-validator to your VPS (run from your Mac)
# Usage: ./deploy_to_vps.sh
# Uses: ssh root@170.64.199.80 (or set VPS_HOST)

VPS_HOST="${VPS_HOST:-170.64.199.80}"
VPS_USER="${VPS_USER:-root}"
INSTALL_DIR="/opt/email-validator"  # Separate from n8n, won't affect it

set -e
echo "Deploying to $VPS_USER@$VPS_HOST (install: $INSTALL_DIR)"
echo "n8n will not be affected - we only add files to $INSTALL_DIR"
echo ""

ssh "$VPS_USER@$VPS_HOST" bash -s << 'REMOTE'
set -e
echo "=== Installing email-validator (isolated from n8n) ==="

# Ensure python3 + git
command -v python3 >/dev/null || (apt-get update -qq && apt-get install -y -qq python3 python3-venv python3-pip git)

# Install in /opt - separate from n8n (usually in ~ or /root)
cd /opt
if [ -d email-validator/.git ]; then
  cd email-validator && git pull
else
  rm -rf email-validator 2>/dev/null
  git clone https://github.com/elyasalemi10/email-validator.git
  cd email-validator
fi

python3 -m venv venv
./venv/bin/pip install -q -r requirements.txt
chmod +x validate

echo ""
echo "=== Done ==="
echo "Validate: ssh $VPS_USER@$VPS_HOST '/opt/email-validator/validate user@example.com'"
echo "Or SSH in and run: cd /opt/email-validator && ./validate user@example.com"
REMOTE

echo ""
echo "Deployment complete. Test with:"
echo "  ssh $VPS_USER@$VPS_HOST '/opt/email-validator/validate user@example.com'"
