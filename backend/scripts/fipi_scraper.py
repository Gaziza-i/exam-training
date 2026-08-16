#!/usr/bin/env python3
"""
Парсер открытого банка заданий ФИПИ (ege.fipi.ru/bank/).

⚠️ ВАЖНО, ПРОЧТИТЕ ПЕРЕД ЗАПУСКОМ
----------------------------------
Этот скрипт написан «вслепую»: на момент написания сайт ege.fipi.ru
недоступен из среды, где я работаю (сеть блокирует прямые запросы к
fipi.ru), поэтому я не могу открыть реальную страницу и подобрать точные
CSS-селекторы под её текущую вёрстку. Каркас (сессия, пагинация, сохранение
в нужном формате, вежливые паузы между запросами) рабочий, а вот функции
`parse_task_list()` и `parse_task_detail()` — это лучшее предположение по
структуре сайта, собранное по обрывкам публичной информации о нём
(URL вида `index.php?proj=<GUID>&qid=<ID>`), и почти наверняка потребуют
правки под реальную HTML-разметку.

Как довести до рабочего состояния (быстрее всего — через меня):
1. Запустите скрипт с флагом --debug-dump — он сохранит сырой HTML
   страниц в папку fipi_dump/.
2. Если задания не находятся (в консоли будет предупреждение) — пришлите
   мне файл(ы) из fipi_dump/ (или просто вставьте кусок HTML вокруг одного
   задания, скопированный через "Просмотр кода страницы" в браузере).
   По реальной разметке я поправлю селекторы за один проход.
3. Альтернатива — сделать это самостоятельно: открыть DevTools (F12) на
   странице банка, найти блоки с текстом задания/вариантами ответа/кнопкой
   «показать ответ», и подставить правильные селекторы в функции ниже.

Как получить proj (GUID предмета):
  1. Откройте https://ege.fipi.ru/bank/ в браузере.
  2. Выберите предмет (например, «Русский язык» или «Математика (базовый
     уровень)») в выпадающем меню.
  3. Скопируйте значение параметра proj из адресной строки, например:
     https://ege.fipi.ru/bank/index.php?proj=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

Использование:
    pip install requests beautifulsoup4
    python fipi_scraper.py --proj <GUID> --subject rus --out tasks_rus.json
    python fipi_scraper.py --proj <GUID> --subject rus --out tasks_rus.json --debug-dump --max-pages 2

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

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://ege.fipi.ru/bank/"
DEFAULT_DELAY = 1.5  # секунд между запросами — не уменьшайте сильно, будьте вежливы к чужому серверу
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ege-exam-trainer personal study tool; "
        "+https://github.com/gaziza-i/exam-training)"
    )
}


def make_session(use_system_proxy: bool, timeout: int) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    # По умолчанию игнорируем системные настройки прокси (переменные окружения
    # HTTP_PROXY/HTTPS_PROXY или прокси из настроек Windows) — на некоторых
    # компьютерах (VPN, антивирус с проверкой HTTPS, корпоративная сеть) такой
    # прокси зависает при подключении к fipi.ru и требests просто висит до
    # таймаута. Если без прокси у вас вообще нет доступа в интернет — запустите
    # скрипт с флагом --use-system-proxy.
    session.trust_env = use_system_proxy
    try:
        # Первый запрос на index.php обычно выставляет сессионную куку, без
        # которой сайт может не отдавать список заданий.
        session.get(BASE_URL, timeout=timeout)
    except requests.exceptions.RequestException as exc:
        print(
            f"\n⚠️  Не удалось подключиться к {BASE_URL}: {exc}\n"
            "Проверьте:\n"
            "  1) открывается ли этот адрес в обычном браузере на этом же компьютере;\n"
            "  2) не включён ли VPN или антивирус с проверкой HTTPS-трафика — попробуйте "
            "временно его отключить;\n"
            "  3) если для доступа в интернет обязательно нужен прокси — запустите с "
            "флагом --use-system-proxy;\n"
            "  4) попробуйте увеличить время ожидания флагом --timeout 60.\n",
            file=sys.stderr,
        )
        raise
    return session


def fetch(session: requests.Session, url: str, params: dict, debug_dump: Path | None, name: str, timeout: int) -> BeautifulSoup:
    resp = session.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"

    if debug_dump:
        debug_dump.mkdir(parents=True, exist_ok=True)
        (debug_dump / f"{name}.html").write_text(resp.text, encoding="utf-8")

    return BeautifulSoup(resp.text, "html.parser")


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


def has_next_page(soup: BeautifulSoup, current_page: int) -> bool:
    """
    TODO(нужно подтвердить): предполагаем, что есть ссылка/кнопка «Далее»
    или нумерация страниц вида ?page=N. Если пагинация устроена иначе
    (например, через AJAX-подгрузку без смены URL) — этот скрипт её не
    увидит, придётся адаптировать под реальный механизм.
    """
    next_link = soup.select_one("a.next, a[rel='next'], a:-soup-contains('Далее')")
    if next_link:
        return True
    page_links = soup.select(f"a[href*='page={current_page + 1}']")
    return bool(page_links)


def parse_task_detail(soup: BeautifulSoup, qid: str) -> dict | None:
    """
    Извлекает текст задания, варианты ответа (если есть) и верный ответ
    с отдельной страницы задания.

    TODO(нужно подтвердить на реальной странице): селекторы ниже —
    предположения по распространённым паттернам подобных сайтов, а не
    проверенная разметка ege.fipi.ru. Скорее всего понадобится правка.
    Особые сложности, которые стоит иметь в виду:
      - часть заданий (особенно в математике) может рендериться как
        картинка с формулой, а не как текст — такие задания скрипт не
        сможет корректно перенести в текстовом виде без OCR;
      - правильный ответ на сайте иногда открывается по клику
        ("Показать ответ"), подгружаемому отдельным JS-запросом — тогда
        потребуется найти этот endpoint через вкладку Network в DevTools
        и дёрнуть его отдельным запросом.
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
    use_system_proxy: bool,
    timeout: int,
) -> list[dict]:
    session = make_session(use_system_proxy, timeout)
    results: list[dict] = []
    seen_qids: set[str] = set()

    page = 1
    while page <= max_pages:
        params = {"proj": proj, "page": page}
        if topic_number:
            params["theme"] = topic_number  # TODO: подтвердить имя параметра темы

        print(f"[{subject_label}] Страница {page}…", file=sys.stderr)
        list_soup = fetch(session, BASE_URL + "index.php", params, debug_dump, f"list_page_{page}", timeout)
        qids = parse_task_list(list_soup)

        if not qids:
            print(
                "  ⚠️  На странице не найдено ни одного задания. Похоже, селекторы "
                "parse_task_list() не подходят под реальную вёрстку сайта — запустите "
                "с --debug-dump и пришлите HTML для правки.",
                file=sys.stderr,
            )
            break

        for qid in qids:
            if qid in seen_qids:
                continue
            seen_qids.add(qid)

            time.sleep(delay)
            detail_soup = fetch(
                session, BASE_URL + "index.php", {"proj": proj, "qid": qid}, debug_dump, f"task_{qid}", timeout
            )
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

        if not has_next_page(list_soup, page):
            break

        page += 1
        time.sleep(delay)

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
        help="Сохранять сырой HTML каждой запрошенной страницы в папку fipi_dump/ — полезно для отладки селекторов",
    )
    parser.add_argument(
        "--use-system-proxy",
        action="store_true",
        help=(
            "Использовать системные настройки прокси (переменные окружения / прокси Windows). "
            "По умолчанию скрипт их игнорирует — на некоторых компьютерах (VPN, антивирус с "
            "проверкой HTTPS, корпоративная сеть) такой прокси зависает при подключении к fipi.ru."
        ),
    )
    parser.add_argument("--timeout", type=int, default=20, help="Таймаут запроса в секундах (по умолчанию 20)")
    args = parser.parse_args()

    debug_dir = Path("fipi_dump") if args.debug_dump else None

    tasks = scrape(
        proj=args.proj,
        subject_label=args.subject,
        topic_number=args.topic,
        max_pages=args.max_pages,
        delay=args.delay,
        debug_dump=debug_dir,
        use_system_proxy=args.use_system_proxy,
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
