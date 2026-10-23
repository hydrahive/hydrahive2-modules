"""Echter kleiner SMTP-Server für die Versand-Tests (Thread, 127.0.0.1, zufälliger Port).

Spricht SMTP über TLS (Modus „ssl“) oder Klartext mit/ohne STARTTLS-Angebot. Zertifikate aus einer Test-CA
(cryptography) – damit wird die Zertifikatsprüfung echt getestet, nicht nachgebildet.
"""
from __future__ import annotations

import base64
import datetime
import socket
import ssl
import threading
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


def _name(cn):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def make_ca(tmp: Path, hostname: str = "localhost"):
    """Test-CA + Server-Zertifikat für hostname. Gibt (ca_pem, cert_pem, key_pem) als Pfade zurück."""
    now = datetime.datetime.now(datetime.timezone.utc)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca = (x509.CertificateBuilder().subject_name(_name("Mailbox Test CA")).issuer_name(_name("Mailbox Test CA"))
          .public_key(ca_key.public_key()).serial_number(1).not_valid_before(now - datetime.timedelta(days=1))
          .not_valid_after(now + datetime.timedelta(days=2))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
          .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True, content_commitment=False,
                                       key_encipherment=False, data_encipherment=False, key_agreement=False,
                                       encipher_only=False, decipher_only=False), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
          .sign(ca_key, hashes.SHA256()))
    key = ec.generate_private_key(ec.SECP256R1())
    cert = (x509.CertificateBuilder().subject_name(_name(hostname)).issuer_name(ca.subject)
            .public_key(key.public_key()).serial_number(2).not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=2))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(hostname)]), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(ca_key, hashes.SHA256()))
    p = {"ca": tmp / "ca.pem", "cert": tmp / f"{hostname}.pem", "key": tmp / f"{hostname}.key"}
    p["ca"].write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    p["cert"].write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    p["key"].write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    return p


class SMTPServer:
    def __init__(self, certs: dict, *, mode: str, user="till@example.net", password="pw", reject=()):
        self.mode, self.user, self.password, self.reject = mode, user, password, set(reject)
        self.ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.ctx.load_cert_chain(certs["cert"], certs["key"])
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        self.received: list[dict] = []
        self.plain_auth_seen = False      # AUTH ohne TLS gesehen → darf nie passieren
        self.token = "AT-1"               # erwarteter Zugriffstoken bei XOAUTH2
        self.xoauth: list[bytes] = []
        threading.Thread(target=self._serve, daemon=True).start()

    def close(self):
        self.sock.close()

    def _serve(self):
        while True:
            try:
                c, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self._session, args=(c,), daemon=True).start()

    def _session(self, c):
        try:
            if self.mode == "ssl":
                c = self.ctx.wrap_socket(c, server_side=True)
            self._talk(c, tls=self.mode == "ssl")
        except (OSError, ssl.SSLError):
            pass
        finally:
            c.close()

    def _talk(self, c, *, tls, greet=True):
        f = c.makefile("rb")
        say = lambda s: c.sendall(s.encode() + b"\r\n")  # noqa: E731
        if greet:
            say("220 test ESMTP")
        mail = {"from": None, "rcpt": [], "data": b""}
        while True:
            line = f.readline()
            if not line:
                return
            cmd = line.decode(errors="replace").strip()
            up = cmd.upper()
            if up.startswith(("EHLO", "HELO")):
                ext = ["250-test"] + (["250-STARTTLS"] if self.mode == "starttls" and not tls else [])
                say("\r\n".join(ext + ["250 AUTH PLAIN XOAUTH2"]))
            elif up == "STARTTLS" and self.mode == "starttls" and not tls:
                say("220 go")
                c = self.ctx.wrap_socket(c, server_side=True)
                return self._talk(c, tls=True, greet=False)
            elif up.startswith("AUTH PLAIN"):
                if not tls:
                    self.plain_auth_seen = True
                parts = base64.b64decode(cmd.split()[2]).split(b"\0")
                ok = parts[1].decode() == self.user and parts[2].decode() == self.password
                say("235 ok" if ok else f"535 5.7.8 auth failed for {parts[1].decode()} {parts[2].decode()}")
            elif up.startswith("AUTH XOAUTH2"):
                if not tls:
                    self.plain_auth_seen = True
                raw = base64.b64decode(cmd.split()[2])
                self.xoauth.append(raw)
                ok = raw == f"user={self.user}\x01auth=Bearer {self.token}\x01\x01".encode()
                say("235 2.7.0 Authentication successful" if ok else "535 5.7.3 Authentication unsuccessful")
            elif up.startswith("MAIL FROM:"):
                mail = {"from": cmd[10:].strip(" <>"), "rcpt": [], "data": b""}
                say("250 ok")
            elif up.startswith("RCPT TO:"):
                addr = cmd[8:].strip(" <>")
                if addr in self.reject:
                    say("550 5.1.1 no such user")
                else:
                    mail["rcpt"].append(addr)
                    say("250 ok")
            elif up == "DATA":
                say("354 go")
                buf = []
                while (ln := f.readline()) not in (b".\r\n", b""):
                    buf.append(ln[1:] if ln.startswith(b"..") else ln)
                mail["data"] = b"".join(buf)
                self.received.append(mail)
                say("250 queued")
            elif up == "QUIT":
                say("221 bye")
                return
            else:
                say("250 ok" if up.startswith(("RSET", "NOOP")) else "502 nope")

