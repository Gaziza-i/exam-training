#!/usr/bin/env python3
"""
Парсер открытого банка заданий ФИПИ (ege.fipi.ru/bank/) на Playwright.

⚠️ ВАЖНО, ПРОЧТИТЕ ПЕРЕД ЗАПУСКОМ
----------------------------------
Этот скрипт написан «вслепую»: на момент написания сайт ege.fipi.ru
недоступен из среды, где я работаю (сеть блокирует прямые запросы к
fipi.ru), поэтому я не могу открыть реальную страницу и подобрать точные
CSS-селекторы под её текущую вёрстку. Каркас (запуск браузера, пагинация,
сохранение в нужном формате, вежливые паузы между запросами) рабочий, а вот
функции `parse_task_list()` и `parse_task_detail()` — это лучшее
предположение по структуре сайта и почти наверняка потребуют правки под
реальную HTML-разметку.

Почему Playwright, а не requests: обычный requests-скрипт зависал на
TLS-подключении к сайту, хотя в обычном браузере сайт открывается — похоже
на защиту от ботов по «отпечатку» TLS/браузера. Playwright запускает
настоящий Chromium, поэтому для сайта он неотличим от обычного посетителя.

Как довести до рабочего состояния (быстрее всего — через меня):
1. Запустите скрипт с флагом --debug-dump — он сохранит отрендеренный HTML
   страниц (после выполнения JS) в папку fipi_dump/.
2. Если задания не находятся (в консоли будет предупреждение) — пришлите
   мне файл(ы) из fipi_dump/, я поправлю селекторы под реальную разметку.
3. Альтернатива — сделать это самостоятельно: открыть DevTools (F12) на
   странице банка, найти блоки с текстом задания/вариантами ответа/кнопкой
   «показать ответ», и подставить правильные селекторы в функции ниже.

Как получить proj (GUID предмета):
  1. Откройте https://ege.fipi.ru/bank/ в браузере.
  2. Выберите предмет (например, «Русский язык» или «Математика (базовый
     уровень)») в выпадающем меню.
  3. Скопируйте значение параметра proj из адресной строки, например:
     https://ege.fipi.ru/bank/index.php?proj=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

Установка и использование:
    pip install playwright beautifulsoup4
    playwright install chromium

    python fipi_scraper.py --proj <GUID> --subject rus --out tasks_rus.json
    python fipi_scraper.py --proj <GUID> --subject rus --out tasks_rus.json --debug-dump --max-pages 2

Если "python" у вас указывает на заглушку Windows Store — используйte
"py" вместо "python" (как и раньше).

Результат — JSON в формате, который понимает `manage.py import_fipi`:
    python manage.py import_fipi tasks_rus.json --subject rus

Пожалуйста, уважайте сайт: скрипт по умолчанию делает паузу между запросами
и не запускает параллельные потоки. Открытый банк создан для бесплатного
использования школьниками при подготовке к экзаменам — не превращайте
скрипт в источник нагрузки на чужой сервер и не запускайте его на весь банк
целиком за один присест.
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
DEFAULT_DELAY = 1.5  # секунд между запросами — не уменьшайте сильно, будьте вежливы к чужому серверу


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
    page.goto(url, timeout=timeout_ms, wait_until="load")
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass  # некоторые страницы держат соединение открытым и никогда не "затихают" — не критично

    html = page.content()

    if debug_dump:
        debug_dump.mkdir(parents=True, exist_ok=True)
        (debug_dump / f"{name}.html").write_text(html, encoding="utf-8")

    return BeautifulSoup(html, "html.parser")


def parse_task_list(soup: BeautifulSoup) -> list[str]:
    """
    Возвращает список qid найденных на странице заданий.

    TODO(нужно подтвердить на реальной странице): ниже — предположение,
    что каждое задание на странице списка обёрнуто в ссылку вида
    `index.php?proj=...&qid=XXXXXX`. Если это не так — пришлите мне HTML
    из fipi_dump/list_page_*.html, поправлю разбор.
    """
    qids: list[str] = []
    for link in soup.select("a[href*='qid=']"):
        href = link.get("href", "")
        if "qid=" in href:
            qid = href.split("qid=")[-1].split("&")[0]
            if qid and qid not in qids:
                qids.append(qid)
    return qids


def parse_task_detail(soup: BeautifulSoup, qid: str) -> dict | None:
    """
    Извлекает текст задания, варианты ответа (если есть) и верный ответ
    с отдельной страницы задания.

    TODO(нужно подтвердить на реальной странице): селекторы ниже —
    предположения, а не проверенная разметка ege.fipi.ru. Особые
    сложности, которые стоит иметь в виду:
      - часть заданий (особенно в математике) может рендериться как
        картинка с формулой, а не как текст — такие задания скрипт не
        сможет корректно перенести в текстовом виде без OCR;
      - правильный ответ на сайте иногда открывается только по клику
        ("Показать ответ") — тогда в parse_task_detail() нужно будет
        сначала кликнуть по кнопке через page.click(...) перед тем, как
        брать soup из page.content().
    """
    text_block = soup.select_one(".qtext, .task-text, .question, #task_text")
    if not text_block:
        return None
    text = text_block.get_text("\n", strip=True)

    options = None
    option_nodes = soup.select(".answer-options li, .qanswer li, .options li")
    if option_nodes:
        options = [o.get_text(" ", strip=True) for o in option_nodes]

    answer_block = soup.select_one(".qanswer, .correct-answer, .answer, #answer")
    correct_answer = answer_block.get_text(" ", strip=True) if answer_block else ""

    return {
        "fipi_id": qid,
        "text": text,
        "options": options,
        "correct_answer": correct_answer,
        "explanation": "",
    }


def scrape(
    proj: str,
    subject_label: str,
    topic_number: int | None,
    max_pages: int,
    delay: float,
    debug_dump: Path | None,
    headless: bool,
    timeout: int,
) -> list[dict]:
    results: list[dict] = []
    seen_qids: set[str] = set()
    timeout_ms = timeout * 1000

    with sync_playwright() as pw:
        page, browser = open_page(pw, headless)
        try:
            # Список заданий на index.php реально не находится — он подгружается
            # отдельной страницей questions.php внутрь <iframe id="questions_container">.
            # Поэтому сначала один раз открываем index.php (получить сессию/куки),
            # а затем ходим напрямую в questions.php за списком заданий.
            print(f"[{subject_label}] Открываю index.php (сессия)…", file=sys.stderr)
            goto(page, f"{BASE_URL}index.php?proj={proj}", debug_dump, "index", timeout_ms)

            pagesize = 10  # как на сайте по умолчанию (см. hidden-поле pagesize в форме фильтров)
            page_num = 1
            while page_num <= max_pages:
                # page на сайте считается с 0, поэтому page_num-1
                url = f"{BASE_URL}questions.php?proj={proj}&page={page_num - 1}&pagesize={pagesize}"
                if topic_number:
                    url += f"&theme={topic_number}"  # TODO: подтвердить, что фильтр по теме так работает через GET

                print(f"[{subject_label}] Страница {page_num} (questions.php)…", file=sys.stderr)
                list_soup = goto(page, url, debug_dump, f"list_page_{page_num}", timeout_ms)
                qids = parse_task_list(list_soup)

                if not qids:
                    print(
                        "  ⚠️  На странице не найдено ни одного задания. Похоже, селекторы "
                        "parse_task_list() не подходят под реальную вёрстку questions.php — запустите "
                        "с --debug-dump и пришлите HTML файла list_page_1.html для правки.",
                        file=sys.stderr,
                    )
                    break

                for qid in qids:
                    if qid in seen_qids:
                        continue
                    seen_qids.add(qid)

                    time.sleep(delay)
                    detail_url = f"{BASE_URL}index.php?proj={proj}&qid={qid}"
                    detail_soup = goto(page, detail_url, debug_dump, f"task_{qid}", timeout_ms)
                    task = parse_task_detail(detail_soup, qid)
                    if task is None:
                        print(f"  ⚠️  Не удалось разобрать задание qid={qid} — пропущено.", file=sys.stderr)
                        continue

                    task["topic_number"] = topic_number or 0
                    task["topic_title"] = ""
                    task["task_type"] = "choice" if task.get("options") else "short_answer"
                    task["difficulty"] = "base"
                    results.append(task)
                    print(f"  + qid={qid}: {task['text'][:60]}…", file=sys.stderr)

                if len(qids) < pagesize:
                    break  # последняя страница — заданий меньше полного размера страницы

                page_num += 1
                time.sleep(delay)
        finally:
            browser.close()

    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--proj", required=True, help="GUID предмета из URL банка (параметр proj)")
    parser.add_argument("--subject", required=True, help="Метка предмета для лога, например rus или math_base")
    parser.add_argument("--topic", type=int, default=None, help="Номер темы/задания КИМ (если фильтруете по теме)")
    parser.add_argument("--out", required=True, help="Путь к выходному JSON-файлу")
    parser.add_argument("--max-pages", type=int, default=3, help="Сколько страниц списка обойти (по умолчанию 3)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Пауза между запросами, сек")
    parser.add_argument(
        "--debug-dump",
        action="store_true",
        help="Сохранять отрендеренный HTML каждой страницы в папку fipi_dump/ — полезно для отладки селекторов",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Показать окно браузера вместо headless-режима — полезно, чтобы увидеть глазами, что происходит",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Таймаут загрузки страницы в секундах (по умолчанию 30)")
    args = parser.parse_args()

    debug_dir = Path("fipi_dump") if args.debug_dump else None

    tasks = scrape(
        proj=args.proj,
        subject_label=args.subject,
        topic_number=args.topic,
        max_pages=args.max_pages,
        delay=args.delay,
        debug_dump=debug_dir,
        headless=not args.show_browser,
        timeout=args.timeout,
    )

    out_path = Path(args.out)
    out_path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nГотово: {len(tasks)} заданий сохранено в {out_path}", file=sys.stderr)
    if debug_dir:
        print(f"Отладочный HTML сохранён в {debug_dir}/", file=sys.stderr)
    if not tasks:
        print(
            "\nЗаданий не найдено — почти наверняка нужно поправить селекторы под "
            "реальную разметку сайта (см. TODO в начале файла и в функциях parse_*).",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
