import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Sequence


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class EmailService:
    """Serviço simples para envio de emails de confirmação."""

    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST", "localhost")
        self.port = int(os.getenv("SMTP_PORT", "1025"))
        self.username = os.getenv("SMTP_USERNAME", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.use_tls = _env_bool("SMTP_USE_TLS", "false")
        self.from_address = os.getenv("SMTP_FROM", "cinema@example.com")

    def _connect(self) -> smtplib.SMTP:
        server = smtplib.SMTP(self.host, self.port, timeout=10)
        if self.use_tls:
            server.starttls()
        if self.username and self.password:
            server.login(self.username, self.password)
        return server

    def send_confirmation(self, *, nome: str, email: str, sessao: str, assentos: Sequence[str]) -> None:
        """Envia um email com o resumo da compra."""
        if not email:
            logging.warning("Email não informado para envio de confirmação.")
            return

        msg = EmailMessage()
        msg["Subject"] = f"Confirmação da reserva - Sessão {sessao}"
        msg["From"] = self.from_address
        msg["To"] = email

        assentos_lista = ", ".join(sorted(assentos))
        msg.set_content(
            "\n".join(
                [
                    f"Olá, {nome or 'cliente'}!",
                    "",
                    "Recebemos o pagamento fictício da sua reserva.",
                    f"Sessão: {sessao}",
                    f"Assentos: {assentos_lista}",
                    "",
                    "Bom filme!",
                    "Equipe Cinemas Costa Dourada",
                ]
            )
        )

        try:
            with self._connect() as server:
                server.send_message(msg)
            logging.info("Email de confirmação enviado para %s", email)
        except Exception as exc:  # pragma: no cover - apenas loga
            logging.error("Falha ao enviar email para %s: %s", email, exc)
