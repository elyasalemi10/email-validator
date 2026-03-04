#!/usr/bin/env python3
"""
Local Email Validator - Syntax, MX, SMTP dialog (like Verifalia)
Usage: python validator.py email@example.com
       python validator.py -f leads.csv
"""

import argparse
import socket
import smtplib
import sys
from dataclasses import dataclass, field
from typing import Optional

from email_validator import validate_email as _validate_syntax, EmailNotValidError
import dns.resolver
import dns.exception


@dataclass
class ValidationResult:
    email: str
    syntax_ok: bool = False
    syntax_detail: str = ""
    mx_records: list = field(default_factory=list)
    mx_ok: bool = False
    dialog_host: Optional[str] = None
    dialog_ok: bool = False
    server_code: Optional[int] = None
    server_message: str = ""
    overall_valid: bool = False


def check_syntax(email: str) -> tuple[bool, str]:
    try:
        _validate_syntax(email, check_deliverability=False)
        return True, "The Email Address Syntax is correct"
    except EmailNotValidError as e:
        return False, str(e)


def check_mx_records(domain: str) -> tuple[list, bool]:
    try:
        answers = dns.resolver.resolve(domain, "MX")
        records = [(str(r.exchange).rstrip("."), r.preference) for r in answers]
        records.sort(key=lambda x: x[1])
        return records, len(records) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException):
        return [], False


def check_smtp_dialog(email: str, mx_records: list, timeout: int = 10) -> tuple[bool, Optional[str], Optional[int], str]:
    if not mx_records:
        return False, None, None, "No MX records to connect to"

    for host, priority in mx_records:
        for port, use_tls in [(25, False), (587, True)]:
            try:
                with smtplib.SMTP(timeout=timeout) as smtp:
                    smtp.set_debuglevel(0)
                    smtp.connect(host, port)
                    if use_tls:
                        smtp.starttls()
                    smtp.ehlo()
                    smtp.docmd("MAIL FROM:<>")
                    try:
                        code, message = smtp.docmd(f"RCPT TO:<{email}>")
                        msg_str = message.decode("utf-8", errors="replace") if isinstance(message, bytes) else str(message)
                    except smtplib.SMTPDataError as e:
                        code = getattr(e, "smtp_code", 0)
                        msg_str = (e.smtp_error.decode("utf-8", errors="replace") if isinstance(e.smtp_error, bytes) else str(e.smtp_error))
                        return True, host, code, msg_str.strip()
                    except smtplib.SMTPRecipientsRefused as e:
                        errs = getattr(e, "recipients", {})
                        code, msg_str = errs.get(email, (0, str(e)))[:2] if errs else (0, str(e))
                        msg_str = msg_str.decode("utf-8", errors="replace") if isinstance(msg_str, bytes) else str(msg_str)
                        return True, host, code, str(msg_str).strip()
                    return True, host, code, msg_str.strip()
            except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, socket.timeout, socket.gaierror):
                continue
            except (smtplib.SMTPDataError, smtplib.SMTPRecipientsRefused) as e:
                code = getattr(e, "smtp_code", 0)
                msg_str = getattr(e, "smtp_error", str(e).encode())
                msg_str = msg_str.decode("utf-8", errors="replace") if isinstance(msg_str, bytes) else str(msg_str)
                return True, host, code, msg_str.strip()
            except Exception as e:
                if "451" in str(e) or "temporarily" in str(e).lower():
                    return True, host, 451, str(e)
                continue

    return False, None, None, "Could not complete dialog with any MX server"


def validate_email(email: str, timeout: int = 10) -> ValidationResult:
    email = email.strip().lower()
    result = ValidationResult(email=email)

    result.syntax_ok, result.syntax_detail = check_syntax(email)
    if not result.syntax_ok:
        return result

    domain = email.split("@")[1]
    result.mx_records, result.mx_ok = check_mx_records(domain)
    if not result.mx_ok:
        return result

    result.dialog_ok, result.dialog_host, result.server_code, result.server_message = check_smtp_dialog(
        email, result.mx_records, timeout=timeout
    )

    result.overall_valid = result.syntax_ok and result.mx_ok and result.dialog_ok and (result.server_code in (250, 251))
    return result


def format_result(result: ValidationResult) -> str:
    lines = []
    lines.append(f"  {'✓' if result.syntax_ok else '✗'} {result.syntax_detail}")
    for host, prio in result.mx_records:
        lines.append(f"  {'✓' if result.mx_ok else '✗'} MX record found: {host} (Priority {prio})")
    if result.syntax_ok and not result.mx_ok:
        lines.append("  ✗ No MX records found")
    if result.dialog_host:
        lines.append(f"  {'✓' if result.dialog_ok else '✗'} Dialog with {result.dialog_host} succeeded")
        if result.server_code is not None:
            status = "✓" if result.server_code in (250, 251) else "✗"
            lines.append(f"  {status} Server Response: {result.server_code} {result.server_message}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("email", nargs="?", help="Email to validate")
    parser.add_argument("-f", "--file", help="CSV file with 'email' column")
    parser.add_argument("-t", "--timeout", type=int, default=10)
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("-o", "--output", help="Export to CSV (with -f)")
    args = parser.parse_args()

    if args.file:
        import csv
        from pathlib import Path
        from concurrent.futures import ThreadPoolExecutor, as_completed

        path = Path(args.file)
        if not path.exists():
            print(f"File not found: {path}")
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            col = "email" if "email" in cols else "Email"
            name_col = "business_name" if "business_name" in cols else ("Business Name" if "Business Name" in cols else None)
            rows = [r for r in reader if r.get(col, "").strip() and "@" in r.get(col, "")]
        emails = [(r.get(name_col, ""), r[col].strip()) for r in rows]
        results_by_idx = {}
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(validate_email, e, args.timeout): (i, e) for i, (_, e) in enumerate(emails)}
            for fut in as_completed(futures):
                i, email = futures[fut]
                try:
                    results_by_idx[i] = fut.result()
                except Exception as e:
                    results_by_idx[i] = ValidationResult(email=email, syntax_detail=str(e))
        results = [results_by_idx[i] for i in range(len(emails))]
        for i, (r, (_, email)) in enumerate(zip(results, emails)):
            if not args.quiet:
                print(f"\n[{i+1}/{len(emails)}] {email}")
                print(format_result(r))
        valid_count = sum(1 for r in results if r.overall_valid)
        print(f"\n--- {valid_count}/{len(results)} valid ---")

        if args.output:
            with open(args.output, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["email", "business_name", "valid"])
                w.writeheader()
                for (name, _), r in zip(emails, results):
                    w.writerow({"email": r.email, "business_name": name, "valid": r.overall_valid})
            print(f"Exported: {args.output}")
        return

    if not args.email:
        parser.print_help()
        sys.exit(1)

    result = validate_email(args.email, timeout=args.timeout)
    if args.quiet:
        print("Valid" if result.overall_valid else "Invalid")
    else:
        print(f"\nValidating: {args.email}\n")
        print(format_result(result))
        print(f"\n{'Valid' if result.overall_valid else 'Invalid'}")


if __name__ == "__main__":
    main()
