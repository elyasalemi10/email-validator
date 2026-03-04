# Email Validator

Local email validation (syntax + MX + SMTP) — same checks as Verifalia. Works best on a VPS where port 25 is open.

## Quick Start

```bash
# Single email
./validate user@example.com

# Or
python validator.py user@example.com
```

## VPS Setup (recommended)

Port 25 is blocked on most home networks. Run on a VPS for full SMTP validation:

```bash
# On your VPS (Ubuntu/Debian)
curl -sSL https://raw.githubusercontent.com/elyasalemi10/email-validator/main/setup_vps.sh | bash
```

Or manually:

```bash
git clone https://github.com/elyasalemi10/email-validator.git
cd email-validator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
chmod +x validate
```

## Usage

| Command | Description |
|---------|-------------|
| `./validate email@example.com` | Validate single email |
| `./validate -q email@example.com` | Quiet: just "Valid" or "Invalid" |
| `./validate -f leads.csv` | Batch validate CSV |
| `./validate -f leads.csv -o results.csv` | Export results |

## Checks

1. **Syntax** – Email format correct
2. **MX records** – Domain has mail servers
3. **SMTP dialog** – Connects to server, RCPT TO
4. **Server response** – 250 = deliverable, 451/550 = not
