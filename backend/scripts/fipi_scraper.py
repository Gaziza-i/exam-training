#!/usr/bin/env python3
"""
Парсер открытого банка заданий ФИПИ (ege.fipi.ru/bank/) на Playwright.

СТАТУС: селекторы проверены на реальном HTML сайта (спасибо тестовому
прогону) и вытаскивают текст задания, варианты ответа, тип ответа и код
КЭС (темы) прямо со страницы списка — заходить на отдельную страницу
каждого задания не нужно, там просто нет отдельной страницы: все данные
уже в списке (`questions.php`).

⚠️ ГЛАВНОЕ ОГРАНИЧЕНИЕ: сайт НЕ публикует правильные ответы в HTML.
Кнопка «Ответить» отправляет ваш ответ на сервер (`solve.php`) и получает
в ответ только «верно/неверно/решено» — без текста самого правильного
ответа. Это осознанная защита от списывания, и обойти её просто скрапингом
нельзя. Поэтому в выгруженном JSON поле `correct_answer` всегда пустое —
дозаполнить его придётся вручную (или прислать выгрузку человеку/ИИ,
который умеет решать эти задания).

Как получить proj (GUID предмета):
  1. Откройте https://ege.fipi.ru/bank/ в браузере.
  2. Выберите предмет (например, «Русский язык» или «Математика (базовый
     уровень)») в выпадающем меню.
  3. Скопируйте значение параметра proj из адресной строки, например:
     https://ege.fipi.ru/bank/index.php?proj=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

Установка и использование (Windows: используйте `py` вместо `python`, если
`python` у вас указывает на заглушку Microsoft Store):
    pip install playwright beautifulsoup4
    playwright install chromium

    python fipi_scraper.py --proj <GUID> --subject rus --out tasks_rus.json
    python fipi_scraper.py --proj <GUID> --subject rus --out tasks_rus.json --max-pages 5

Результат — JSON с текстами реальных заданий ФИПИ (без ответов). Дальше:
  1. Пришлите файл сюда в чат (или его часть) — дозаполню correct_answer.
  2. Импортируйте дозаполненный файл: python manage.py import_fipi tasks_rus.json --subject rus

Пожалуйста, уважайте сайт: скрипт по умолчанию делает паузу между
страницами и не запускает параллельные потоки. Открытый банк создан для
бесплатного использования школьниками при подготовке к экзаменам — не
превращайте скрипт в источник нагрузки на чужой сервер и не выкачивайте
весь банк (в нём тысячи заданий) за один присест.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup

try:
    from playwright.sync_api import Page, sync_playwright
except ImportError:
    print(
        "Не найден пакет playwright. Установите:\n"
        "    pip install playwright beautifulsoup4\n"
        "    playwright install chromium\n"
        "(если 'pip' не работает — используйте 'py -m pip install ...')",
        file=sys.stderr,
    )
    raise

BASE_URL = "https://ege.fipi.ru/bank/"
DEFAULT_DELAY = 1.5  # секунд между страницами — не уменьшайте сильно, будьте вежливы к чужому серверу
PAGE_SIZE = 10  # как на сайте по умолчанию (hidden-поле pagesize в форме фильтров)


def open_page(playwright, headless: bool) -> tuple[Page, "any"]:
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        locale="ru-RU",
    )
    page = context.new_page()
    return page, browser


def goto(page: Page, url: str, debug_dump: Path | None, name: str, timeout_ms: int) -> BeautifulSoup:
    # "load" ждёт вообще всех ресурсов страницы (включая шрифты для формул с
    # внешнего CDN) и может зависать надолго/навсегда — используем менее
    # строгое условие, нам нужен только готовый HTML.
    page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass  # некоторые страницы держат соединение открытым и никогда не "затихают" — не критично

    html = page.content()

    if debug_dump:
        debug_dump.mkdir(parents=True, exist_ok=True)
        (debug_dump / f"{name}.html").write_text(html, encoding="utf-8")

    return BeautifulSoup(html, "html.parser")


def parse_tasks(soup: BeautifulSoup) -> list[dict]:
    """
    Разбирает страницу списка заданий (questions.php). Каждое задание —
    это пара блоков <div class="qblock" id="qXXXXXX"> (текст + форма
    ответа) и <div id="iXXXXXX"> (метаданные: КЭС, тип ответа, номер).
    """
    tasks: list[dict] = []

    for qblock in soup.select("div.qblock"):
        block_id = qblock.get("id", "")
        if not block_id.startswith("q"):
            continue
        qid = block_id[1:]

        text_cell = qblock.select_one("td.cell_0")
        if not text_cell:
            continue
        text = text_cell.get_text("\n", strip=True)

        # Варианты ответа — есть только у заданий с чекбоксами/радио
        # (distractors-table); у заданий с текстовым полем вариантов нет.
        options = []
        for row in qblock.select(".distractors-table tr"):
            cells = row.select("td")
            if len(cells) >= 3:
                option_text = cells[-1].get_text(" ", strip=True)
                if option_text:
                    options.append(option_text)

        # Метаданные (КЭС, тип ответа) лежат в соседнем блоке #i<qid>
        info_block = soup.select_one(f"#i{qid}")
        kes_codes: list[str] = []
        answer_type_label = ""
        if info_block:
            for row in info_block.select(".task-info-content table tr"):
                cells = row.select("td")
                if len(cells) < 2:
                    continue
                label = cells[0].get_text(strip=True)
                if label == "КЭС:":
                    kes_codes = [d.get_text(" ", strip=True) for d in cells[1].select("div")]
                elif label == "Тип ответа:":
                    answer_type_label = cells[1].get_text(strip=True)

        tasks.append(
            {
                "fipi_id": qid,
                "text": text,
                "options": options or None,
                "task_type": "choice" if options else "short_answer",
                "correct_answer": "",  # сайт не публикует ответы — заполняется вручную
                "explanation": "",
                "kes_codes": kes_codes,  # коды тем КЭС, напр. "3.8.6 Знаки препинания..."
                "answer_type_label": answer_type_label,  # как на сайте: "Краткий ответ" и т.п.
                "topic_number": 0,  # нужно сопоставить с номером задания КИМ вручную/через import
                "topic_title": "",
                "difficulty": "base",
            }
        )

    return tasks


def scrape(
    proj: str,
    subject_label: str,
    max_pages: int,
    delay: float,
    debug_dump: Path | None,
    headless: bool,
    timeout: int,
    start_page: int = 1,
) -> list[dict]:
    results: list[dict] = []
    seen_qids: set[str] = set()
    timeout_ms = timeout * 1000

    with sync_playwright() as pw:
        page, browser = open_page(pw, headless)
        try:
            print(f"[{subject_label}] Открываю index.php (сессия)…", file=sys.stderr)
            goto(page, f"{BASE_URL}index.php?proj={proj}", debug_dump, "index", timeout_ms)

            page_num = start_page
            last_page = start_page + max_pages - 1
            while page_num <= last_page:
                # На сайте нумерация страниц с 0, поэтому page_num-1.
                url = f"{BASE_URL}questions.php?proj={proj}&page={page_num - 1}&pagesize={PAGE_SIZE}"

                print(f"[{subject_label}] Страница {page_num}…", file=sys.stderr)
                list_soup = goto(page, url, debug_dump, f"list_page_{page_num}", timeout_ms)
                page_tasks = parse_tasks(list_soup)

                if not page_tasks:
                    print(
                        "  ⚠️  На странице не найдено ни одного задания. Возможно, вёрстка сайта "
                        "снова изменилась — пришлите HTML файла list_page_N.html для правки.",
                        file=sys.stderr,
                    )
                    break

                new_count = 0
                for task in page_tasks:
                    if task["fipi_id"] in seen_qids:
                        continue
                    seen_qids.add(task["fipi_id"])
                    results.append(task)
                    new_count += 1
                    print(f"  + {task['fipi_id']}: {task['text'][:60]}…", file=sys.stderr)

                if len(page_tasks) < PAGE_SIZE or new_count == 0:
                    break  # последняя страница — заданий меньше полного размера, либо повтор

                page_num += 1
                time.sleep(delay)
        finally:
            browser.close()

    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--proj", required=True, help="GUID предмета из URL банка (параметр proj)")
    parser.add_argument("--subject", required=True, help="Метка предмета для лога, например rus или math_base")
    parser.add_argument("--out", required=True, help="Путь к выходному JSON-файлу")
    parser.add_argument("--max-pages", type=int, default=3, help="Сколько страниц списка обойти (по умолчанию 3, 10 заданий на странице)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Пауза между страницами, сек")
    parser.add_argument(
        "--debug-dump",
        action="store_true",
        help="Сохранять отрендеренный HTML каждой страницы в папку fipi_dump/ — полезно для отладки",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Показать окно браузера вместо headless-режима",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Таймаут загрузки страницы в секундах (по умолчанию 30)")
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="С какой страницы начинать (по умолчанию 1) — используйте, чтобы не скачивать заново уже собранные страницы",
    )
    args = parser.parse_args()

    debug_dir = Path("fipi_dump") if args.debug_dump else None

    tasks = scrape(
        proj=args.proj,
        subject_label=args.subject,
        max_pages=args.max_pages,
        delay=args.delay,
        debug_dump=debug_dir,
        headless=not args.show_browser,
        timeout=args.timeout,
        start_page=args.start_page,
    )

    out_path = Path(args.out)
    out_path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nГотово: {len(tasks)} заданий сохранено в {out_path}", file=sys.stderr)
    if debug_dir:
        print(f"Отладочный HTML сохранён в {debug_dir}/", file=sys.stderr)
    if tasks:
        print(
            "\n⚠️  correct_answer у всех заданий пустой — сайт не публикует ответы. "
            "Пришлите этот файл сюда в чат, дозаполню ответы вручную перед импортом.",
            file=sys.stderr,
        )
    else:
        print(
            "\nЗаданий не найдено — вёрстка сайта могла снова измениться (см. --debug-dump).",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
