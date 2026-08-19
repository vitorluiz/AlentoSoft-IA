"""Vigia local de mudanças em políticas e perfis públicos do Granjimmy.

O módulo faz somente leitura das fontes, guarda snapshots locais e gera um
relatório Markdown. Notificações são opt-in e não alteram contas, anúncios,
perfis ou avaliações.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import smtplib
import subprocess
import sqlite3
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import unified_diff
from email.message import EmailMessage
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable, Optional


@dataclass(frozen=True)
class WatchSource:
    id: str
    platform: str
    title: str
    url: str
    category: str
    priority: str = "important"


@dataclass(frozen=True)
class FetchResult:
    status_code: int
    text: str
    title: str = ""
    error: str = ""


@dataclass(frozen=True)
class Change:
    source: WatchSource
    severity: str
    summary: str
    diff: str
    previous_hash: str
    current_hash: str


@dataclass(frozen=True)
class WatchRun:
    run_id: str
    report_path: Path
    changes: tuple[Change, ...]
    baselines: tuple[str, ...]
    errors: tuple[str, ...]


DEFAULT_SOURCES: tuple[WatchSource, ...] = (
    WatchSource(
        "meta_business_help",
        "Meta",
        "Meta Business Help Center",
        "https://www.facebook.com/business/help/",
        "business_help",
        "important",
    ),
    WatchSource(
        "meta_ads_guide_update",
        "Meta",
        "Facebook Ads Guide — Updates",
        "https://www.facebook.com/business/ads-guide/update",
        "advertising",
        "important",
    ),
    WatchSource(
        "meta_ad_standards",
        "Meta",
        "Meta Advertising Standards",
        "https://transparency.meta.com/policies/ad-standards/",
        "advertising_policy",
        "critical",
    ),
    WatchSource(
        "linkedin_help",
        "LinkedIn",
        "LinkedIn Help",
        "https://www.linkedin.com/help/linkedin",
        "platform_help",
        "important",
    ),
    WatchSource(
        "linkedin_policy_updates",
        "LinkedIn",
        "LinkedIn User Agreement and Privacy Policy updates",
        "https://www.linkedin.com/help/linkedin/answer/a1341216/updates-to-user-agreement-and-privacy-policy",
        "policy_updates",
        "critical",
    ),
    WatchSource(
        "youtube_policy",
        "YouTube",
        "YouTube Creator policies",
        "https://support.google.com/youtube/answer/11616410",
        "creator_policy",
        "important",
    ),
    WatchSource(
        "youtube_monetization",
        "YouTube",
        "YouTube channel monetization policies",
        "https://support.google.com/youtube/answer/1311392?hl=pt-BR",
        "monetization",
        "critical",
    ),
    WatchSource(
        "google_business_help",
        "Google Business Profile",
        "Central de Ajuda do Perfil da Empresa",
        "https://support.google.com/business/?hl=pt-BR",
        "business_help",
        "important",
    ),
    WatchSource(
        "google_business_policies",
        "Google Business Profile",
        "Todas as políticas e diretrizes do Perfil da Empresa",
        "https://support.google.com/business/answer/7667250?hl=pt-BR",
        "business_policy",
        "critical",
    ),
    WatchSource(
        "google_business_representation",
        "Google Business Profile",
        "Diretrizes para representar sua empresa no Google",
        "https://support.google.com/business/answer/3038177?hl=pt-BR",
        "business_representation",
        "critical",
    ),
    WatchSource(
        "google_business_edit_profile",
        "Google Business Profile",
        "Editar o Perfil da Empresa",
        "https://support.google.com/business/answer/3039617?hl=pt-BR",
        "business_operations",
        "critical",
    ),
    WatchSource(
        "google_business_reviews",
        "Google Business Profile",
        "Denunciar avaliações impróprias",
        "https://support.google.com/business/answer/4596773?hl=pt-BR",
        "reviews",
        "critical",
    ),
)


class _VisibleTextParser(HTMLParser):
    """Extrai texto legível sem guardar scripts, estilos ou SVGs."""

    _ignored = {"script", "style", "noscript", "svg", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self._ignore_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in self._ignored:
            self._ignore_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._ignored and self._ignore_depth:
            self._ignore_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._ignore_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
        self.parts.append(data)


def normalize_text(raw: str) -> tuple[str, str]:
    parser = _VisibleTextParser()
    try:
        parser.feed(raw)
        parser.close()
        parts = parser.parts
        title = " ".join(parser.title_parts)
    except Exception:
        parts = [raw]
        title = ""
    text = html.unescape(" ".join(parts))
    text = text.replace("\u00a0", " ")
    lines = []
    previous_blank = False
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if not line:
            if not previous_blank:
                lines.append("")
            previous_blank = True
            continue
        lines.append(line)
        previous_blank = False
    normalized = "\n".join(lines).strip()
    return normalized, re.sub(r"\s+", " ", html.unescape(title)).strip()


def fetch_url(source: WatchSource, timeout: int = 30) -> FetchResult:
    """Baixa uma fonte pública com limite real de tempo e sem executar conteúdo."""
    timeout = max(1, int(timeout))
    marker = "__ALENTO_POLICY_WATCH_STATUS__"
    try:
        completed = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--location",
                "--max-time",
                str(timeout),
                "--connect-timeout",
                str(min(timeout, 10)),
                "--user-agent",
                "AlentoSoft-IA-policy-watch/0.1 (+public-policy-monitor)",
                "--header",
                "Accept: text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
                "--write-out",
                marker + "%{http_code}",
                source.url,
            ],
            capture_output=True,
            timeout=timeout + 2,
            check=False,
        )
    except FileNotFoundError:
        return FetchResult(0, "", error="curl não está instalado")
    except subprocess.TimeoutExpired:
        return FetchResult(0, "", error=f"timeout após {timeout}s")

    output = completed.stdout.decode("utf-8", errors="replace")
    body, separator, status_text = output.rpartition(marker)
    try:
        status_code = int(status_text.strip() or "0")
    except ValueError:
        status_code = 0
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()[:240]
        return FetchResult(status_code, "", error=detail or f"curl exit {completed.returncode}")
    if status_code >= 400 or status_code == 0:
        return FetchResult(status_code, "", error=f"HTTP {status_code or 'desconhecido'}")
    text, title = normalize_text(body if separator else output)
    return FetchResult(status_code, text, title)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _severity(source: WatchSource, diff: str) -> str:
    lowered = diff.lower()
    critical_terms = {
        "suspens", "restri", "proibid", "privacidade", "personal data", "dados pessoais",
        "health", "saúde", "mental health", "copyright", "direitos autorais", "monetiza",
        "horário", "horarios", "telefone", "endereço", "endereco", "categoria", "avaliações",
        "avaliacoes", "reviews", "remov", "extorsão", "extorsao", "política", "politica",
    }
    if source.priority == "critical" or any(term in lowered for term in critical_terms):
        return "critical"
    if source.priority == "important":
        return "important"
    return "informative"


def _diff_summary(diff: str) -> str:
    added = [line[1:].strip() for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    removed = [line[1:].strip() for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    fragments: list[str] = []
    if added:
        fragments.append(f"{len(added)} trecho(s) adicionado(s)")
    if removed:
        fragments.append(f"{len(removed)} trecho(s) removido(s)")
    return "; ".join(fragments) or "o conteúdo normalizado mudou"


def _short_diff(previous: str, current: str, limit: int = 80) -> str:
    diff_lines = list(
        unified_diff(
            previous.splitlines(),
            current.splitlines(),
            fromfile="versão anterior",
            tofile="versão atual",
            lineterm="",
        )
    )
    if len(diff_lines) > limit:
        diff_lines = diff_lines[:limit] + ["... diff truncado ..."]
    return "\n".join(diff_lines)


class PolicyWatch:
    def __init__(
        self,
        db_path: Path,
        report_dir: Path,
        sources: Iterable[WatchSource] = DEFAULT_SOURCES,
        fetcher: Callable[[WatchSource], FetchResult] = fetch_url,
    ) -> None:
        self.db_path = Path(db_path)
        self.report_dir = Path(report_dir)
        self.sources = tuple(sources)
        self.fetcher = fetcher
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    content TEXT NOT NULL,
                    error TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(source_id) REFERENCES sources(id)
                );
                CREATE TABLE IF NOT EXISTS changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    diff TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    current_hash TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES sources(id)
                );
                """
            )
            connection.executemany(
                """
                INSERT INTO sources (id, platform, title, url, category, priority)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    platform=excluded.platform,
                    title=excluded.title,
                    url=excluded.url,
                    category=excluded.category,
                    priority=excluded.priority
                """,
                [(s.id, s.platform, s.title, s.url, s.category, s.priority) for s in self.sources],
            )

    def run(self, now: Optional[datetime] = None) -> WatchRun:
        timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        run_id = timestamp.strftime("%Y%m%dT%H%M%SZ")
        changes: list[Change] = []
        baselines: list[str] = []
        errors: list[str] = []

        with self._connect() as connection:
            for source in self.sources:
                previous = connection.execute(
                    "SELECT * FROM snapshots WHERE source_id = ? ORDER BY id DESC LIMIT 1",
                    (source.id,),
                ).fetchone()
                result = self.fetcher(source)
                content_hash = _hash_text(result.text)
                connection.execute(
                    """
                    INSERT INTO snapshots
                    (source_id, fetched_at, status_code, title, content_hash, content, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source.id,
                        timestamp.isoformat(),
                        result.status_code,
                        result.title,
                        content_hash,
                        result.text,
                        result.error,
                    ),
                )
                if result.error:
                    errors.append(f"{source.title}: {result.error}")
                    continue
                if previous is None:
                    baselines.append(source.id)
                    continue
                if previous["content_hash"] == content_hash:
                    continue
                diff = _short_diff(previous["content"], result.text)
                severity = _severity(source, diff)
                summary = _diff_summary(diff)
                changes.append(
                    Change(
                        source=source,
                        severity=severity,
                        summary=summary,
                        diff=diff,
                        previous_hash=previous["content_hash"],
                        current_hash=content_hash,
                    )
                )
                connection.execute(
                    """
                    INSERT INTO changes
                    (source_id, detected_at, severity, summary, diff, previous_hash, current_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source.id,
                        timestamp.isoformat(),
                        severity,
                        summary,
                        diff,
                        previous["content_hash"],
                        content_hash,
                    ),
                )

        report_path = self._write_report(run_id, timestamp, changes, baselines, errors)
        return WatchRun(run_id, report_path, tuple(changes), tuple(baselines), tuple(errors))

    def _write_report(
        self,
        run_id: str,
        timestamp: datetime,
        changes: list[Change],
        baselines: list[str],
        errors: list[str],
    ) -> Path:
        report_path = self.report_dir / f"policy-watch-{run_id}.md"
        lines = [
            "# Relatório do vigia de políticas",
            "",
            f"- Execução: `{timestamp.isoformat()}`",
            f"- Fontes verificadas: `{len(self.sources)}`",
            f"- Alterações detectadas: `{len(changes)}`",
            f"- Novas linhas de base: `{len(baselines)}`",
            f"- Erros de coleta: `{len(errors)}`",
            "",
        ]
        if not changes:
            lines += ["## Resultado", "", "Nenhuma alteração foi detectada desde o último snapshot.", ""]
        else:
            lines += ["## Alterações detectadas", ""]
            for change in sorted(changes, key=lambda item: (item.severity, item.source.platform, item.source.title)):
                lines += [
                    f"### [{change.severity.upper()}] {change.source.platform} — {change.source.title}",
                    "",
                    f"- URL: {change.source.url}",
                    f"- Categoria: `{change.source.category}`",
                    f"- Resumo: {change.summary}",
                    "",
                    "```diff",
                    change.diff,
                    "```",
                    "",
                ]
        if baselines:
            lines += ["## Fontes inicializadas", "", *[f"- `{source_id}`" for source_id in baselines], ""]
        if errors:
            lines += ["## Erros de coleta", "", *[f"- {error}" for error in errors], ""]
        lines += [
            "## Limites",
            "",
            "Este relatório é informativo. Ele não constitui parecer jurídico, não publica conteúdo, não altera perfis e não denuncia avaliações automaticamente.",
            "",
        ]
        report_path.write_text("\n".join(lines), encoding="utf-8")
        (self.report_dir / "latest.md").write_text("\n".join(lines), encoding="utf-8")
        return report_path


def _send_email(report: str, subject: str) -> None:
    host = os.getenv("POLICY_WATCH_SMTP_HOST", "")
    port = int(os.getenv("POLICY_WATCH_SMTP_PORT", "587"))
    user = os.getenv("POLICY_WATCH_SMTP_USER", "")
    password = os.getenv("POLICY_WATCH_SMTP_PASSWORD", "")
    sender = os.getenv("POLICY_WATCH_EMAIL_FROM", user)
    recipient = os.getenv("POLICY_WATCH_EMAIL_TO", "")
    if not all((host, user, password, sender, recipient)):
        raise RuntimeError(
            "E-mail exige POLICY_WATCH_SMTP_HOST, POLICY_WATCH_SMTP_USER, "
            "POLICY_WATCH_SMTP_PASSWORD, POLICY_WATCH_EMAIL_FROM e POLICY_WATCH_EMAIL_TO."
        )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(report)
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls(context=context)
        server.login(user, password)
        server.send_message(message)


def _send_whatsapp(summary: str) -> None:
    token = os.getenv("POLICY_WATCH_WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = os.getenv("POLICY_WATCH_WHATSAPP_PHONE_NUMBER_ID", "")
    recipient = os.getenv("POLICY_WATCH_WHATSAPP_TO", "")
    template_name = os.getenv("POLICY_WATCH_WHATSAPP_TEMPLATE_NAME", "")
    language = os.getenv("POLICY_WATCH_WHATSAPP_TEMPLATE_LANGUAGE", "pt_BR")
    api_version = os.getenv("POLICY_WATCH_WHATSAPP_API_VERSION", "v26.0")
    if not all((token, phone_number_id, recipient, template_name)):
        raise RuntimeError(
            "WhatsApp exige token, phone number ID, destinatário e template aprovado. "
            "Use as variáveis POLICY_WATCH_WHATSAPP_*."
        )
    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": summary[:1024]}],
                }
            ],
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status >= 300:
                raise RuntimeError(f"WhatsApp HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"WhatsApp HTTP {exc.code}") from exc


def _notification_summary(run: WatchRun) -> str:
    if run.errors:
        error_text = "; ".join(run.errors[:3])
    else:
        error_text = "nenhum"
    critical = sum(change.severity == "critical" for change in run.changes)
    return (
        f"Vigia Granjimmy: {len(run.changes)} alteração(ões), "
        f"{critical} crítica(s), {len(run.baselines)} fonte(s) inicializada(s), "
        f"erros de coleta: {error_text}. Consulte o relatório local."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vigia semanal de políticas do Granjimmy")
    parser.add_argument("--db", type=Path, default=Path("workspaces/policy-watch/policy_watch.sqlite3"))
    parser.add_argument("--report-dir", type=Path, default=Path("workspaces/policy-watch/reports"))
    parser.add_argument("--timeout", type=int, default=15, help="Tempo máximo em segundos por fonte")
    parser.add_argument("--send-email", action="store_true", help="Envia o resumo para o e-mail configurado")
    parser.add_argument("--send-whatsapp", action="store_true", help="Envia o resumo via template WhatsApp configurado")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    fetcher = lambda source: fetch_url(source, timeout=max(1, args.timeout))
    run = PolicyWatch(args.db, args.report_dir, fetcher=fetcher).run()
    notification_errors: list[str] = []
    summary = _notification_summary(run)
    if args.send_email:
        try:
            _send_email(run.report_path.read_text(encoding="utf-8"), f"Vigia Granjimmy — {run.run_id}")
        except Exception as exc:
            notification_errors.append(f"e-mail: {exc}")
    if args.send_whatsapp:
        try:
            _send_whatsapp(summary)
        except Exception as exc:
            notification_errors.append(f"WhatsApp: {exc}")
    print(json.dumps({
        "run_id": run.run_id,
        "report_path": str(run.report_path),
        "database_path": str(args.db),
        "changes": [
            {
                "source_id": change.source.id,
                "platform": change.source.platform,
                "title": change.source.title,
                "severity": change.severity,
                "summary": change.summary,
            }
            for change in run.changes
        ],
        "baselines": list(run.baselines),
        "errors": list(run.errors),
        "notification_errors": notification_errors,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
