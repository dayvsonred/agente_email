from __future__ import annotations

import argparse
import itertools
import sys
import threading
import time

from app.batch_processor import process_todoist_folder
from app.config import get_settings


class Spinner:
    def __init__(self, message: str) -> None:
        self.message = message
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "Spinner":
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r")
        sys.stdout.flush()

    def _run(self) -> None:
        frames = itertools.cycle(["/", "|", "\\", "-"])
        start = time.time()
        while not self._stop_event.is_set():
            frame = next(frames)
            elapsed = int(time.time() - start)
            sys.stdout.write(f"\r[{frame}] {self.message} ({elapsed}s)")
            sys.stdout.flush()
            time.sleep(0.12)


def run_once(
    auto_send: bool,
    candidate_name: str | None,
    fix_email: str | None,
    only_email: str | None,
) -> int:
    settings = get_settings()
    try:
        with Spinner("Processando imagens em TODOIST_DIR"):
            result = process_todoist_folder(
                settings=settings,
                auto_send=auto_send,
                candidate_name=candidate_name,
                fix_email=fix_email,
                only_email=only_email,
            )
    except Exception as exc:
        print(f"[ERRO] Falha ao processar lote: {exc}")
        return 1

    print("[OK] Execucao finalizada.")
    print(
        "Resumo: "
        f"scanned={result.scanned_files}, "
        f"new={result.processed_new_files}, "
        f"duplicates={result.skipped_duplicates}, "
        f"errors={result.errors}, "
        f"sent={result.sent_emails}"
    )

    for item in result.results:
        reason = f" reason={item.reason}" if item.reason else ""
        target = f" moved_to={item.moved_to}" if item.moved_to else ""
        email = f" email={item.extracted_email}" if item.extracted_email else ""
        target_email = f" target_email={item.target_email}" if item.target_email else ""
        source = f" email_source={item.email_source}" if item.email_source else ""
        print(
            f"- {item.file_name}: status={item.status}, sent={item.sent}"
            f"{email}{target_email}{source}{target}{reason}"
        )
    return 0 if result.errors == 0 else 1


def run_watch(
    interval_seconds: int,
    auto_send: bool,
    candidate_name: str | None,
    fix_email: str | None,
    only_email: str | None,
) -> int:
    print(f"Watch ativo. Varredura a cada {interval_seconds}s. Pressione CTRL+C para sair.")
    try:
        while True:
            run_once(
                auto_send=auto_send,
                candidate_name=candidate_name,
                fix_email=fix_email,
                only_email=only_email,
            )
            print(f"Aguardando {interval_seconds}s para a proxima varredura...")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("Encerrado pelo usuario.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Worker para processar prints em TODOIST_DIR e mover para DONE_DIR."
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Executa em loop continuo.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Intervalo do loop em segundos quando --watch estiver ativo.",
    )
    parser.add_argument(
        "--auto-send",
        action="store_true",
        help="Envia e-mails automaticamente apos processar.",
    )
    parser.add_argument(
        "--candidate-name",
        type=str,
        default=None,
        help="Sobrescreve o nome do candidato para esta execucao.",
    )
    parser.add_argument(
        "--fix-email",
        "--fix_email",
        dest="fix_email",
        type=str,
        default=None,
        help="Usa este e-mail somente quando o print nao tiver e-mail detectado.",
    )
    parser.add_argument(
        "--only-email",
        "--only_email",
        dest="only_email",
        type=str,
        default=None,
        help="Sempre envia para este e-mail e ignora e-mail encontrado no print.",
    )
    args = parser.parse_args()

    if args.watch:
        return run_watch(
            interval_seconds=max(1, args.interval),
            auto_send=args.auto_send,
            candidate_name=args.candidate_name,
            fix_email=args.fix_email,
            only_email=args.only_email,
        )
    return run_once(
        auto_send=args.auto_send,
        candidate_name=args.candidate_name,
        fix_email=args.fix_email,
        only_email=args.only_email,
    )


if __name__ == "__main__":
    raise SystemExit(main())
