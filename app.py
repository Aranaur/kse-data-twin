"""Цифровий двійник у залі. Запуск: uv run shiny run app.py --port 7861

Дані живуть лише в пам'яті одного процесу.
Адреси: / для телефона, /?paper=1 для паперових анкет,
/?screen=1&key=... для екрана, /?screen=1&key=...&names=1 зі списком імен.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from urllib.parse import parse_qs

from shiny import App, reactive, render, ui
from starlette.requests import Request

from room import TOPICS, Room

# У репозиторії лежить лише хеш ключа ведучого.
ADMIN_KEY_SHA256 = "00aedec99af8b749a8d53af8f53fce26083e138b0af411b51590b47e94e303ec"

room = Room()

STYLE = """
body { background: #0a0a1a; color: #eeeeff; font-size: 17px; }
.phone { max-width: 460px; margin: 0 auto; padding: 20px 16px 40px; }
.phone h1 { font-size: 24px; margin: 0 0 6px; }
.phone p { color: #a0a0cc; }
.phone .form-control { background: #15152e; color: #fff; border: 1px solid #44446a; }
.phone .form-group { width: 100%; }
.phone .btn { width: 100%; padding: 14px; font-size: 18px; font-weight: 700;
              color: #fff; border: 0; background: #7c5cfc; }
.error { color: #ff8a8a; min-height: 24px; }
.big { font-size: 34px; font-weight: 800; color: #00d4ff; margin: 8px 0; }
.topic { display: block; margin-bottom: 14px; font-weight: 400; }
.topic-row { display: flex; justify-content: space-between; }
.topic-row b { color: #00d4ff; }
.rate { width: 100%; height: 32px; accent-color: #7c5cfc; }
html, body.screen { height: 100%; }
.board { display: flex; flex-direction: column; height: 100vh; padding: 24px 40px; box-sizing: border-box; }
.board header { display: flex; align-items: center; gap: 24px; font-size: 34px; }
.board header .count { flex: 1; }
.board b { color: #00d4ff; }
.board .btn { font-size: 22px; padding: 10px 20px; border: 0; color: #fff; background: #7c5cfc; }
.board .btn.quiet { background: #2a2a4a; }
.board .shiny-html-output { flex: 1; min-height: 0; }
.board svg { width: 100%; height: 100%; }
.names { font-size: 24px; columns: 2; max-height: 30vh; overflow: auto; }
"""

CLIENT_ID = """
$(document).on('shiny:connected', function () {
  var id = localStorage.getItem('twin-id');
  if (!id) {
    id = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now();
    localStorage.setItem('twin-id', id);
  }
  Shiny.setInputValue('client_id', id);
});

function twinClear() {
  document.getElementById('name').value = '';
  document.querySelectorAll('.rate').forEach(function (el) { el.value = 0; el.oninput(); });
}

function twinSend() {
  var ratings = Array.from(document.querySelectorAll('.rate')).map(function (el) { return Number(el.value); });
  var name = document.getElementById('name').value;
  Shiny.setInputValue('answer', { name: name, ratings: ratings }, { priority: 'event' });
}
"""


def is_admin(key: str) -> bool:
    digest = hashlib.sha256(key.encode()).hexdigest()
    return secrets.compare_digest(digest, ADMIN_KEY_SHA256)


def head() -> ui.Tag:
    return ui.tags.head(
        ui.tags.meta(name="viewport", content="width=device-width, initial-scale=1"),
        ui.tags.title("Цифровий двійник"),
        ui.tags.style(STYLE),
    )


def phone_ui() -> ui.Tag:
    return ui.page_fluid(
        head(),
        ui.tags.script(CLIENT_ID),
        ui.div(ui.output_ui("view"), class_="phone"),
    )


def screen_ui(admin: bool) -> ui.Tag:
    buttons = (
        [
            ui.input_action_button("reveal", "Показати двійників"),
            ui.input_action_button("reset", "Очистити", class_="quiet"),
        ]
        if admin
        else []
    )
    return ui.page_fluid(
        head(),
        ui.div(
            ui.tags.header(ui.span(ui.output_ui("count", inline=True), class_="count"), *buttons),
            ui.output_ui("board"),
            ui.output_ui("names"),
            class_="board",
        ),
    )


def app_ui(request: Request) -> ui.Tag:
    params = request.query_params
    if "screen" in params:
        return screen_ui(is_admin(params.get("key", "")))
    return phone_ui()


def topic_input(i: int, topic: str) -> ui.Tag:
    return ui.tags.label(
        ui.div(ui.span(topic), ui.tags.b("0", id=f"v{i}"), class_="topic-row"),
        ui.tags.input(
            type="range", min="0", max="5", step="1", value="0", class_="rate",
            oninput=f"document.getElementById('v{i}').textContent = this.value",
        ),
        class_="topic",
    )


def form() -> ui.TagList:
    return ui.TagList(
        ui.h1("🔍 Твій профіль"),
        ui.p("Оціни теми від 0 до 5. Ім'я побачить лише той, кому ти випадеш двійником. Після лекції дані видаляються."),
        ui.tags.label("Ім'я або псевдонім", class_="topic"),
        ui.tags.input(id="name", type="text", maxlength="24", autocomplete="off", class_="form-control mb-3"),
        *[topic_input(i, topic) for i, topic in enumerate(TOPICS)],
        ui.output_ui("error"),
        ui.tags.button("Готово", type="button", class_="btn", onclick="twinSend()"),
    )


def result(me: dict) -> ui.TagList:
    shared = f"Вам обом подобається: {', '.join(me['shared'])}" if me["shared"] else ""
    return ui.TagList(
        ui.p("Твій цифровий двійник у цьому залі:"),
        ui.div(me["twin"], class_="big"),
        ui.p(f"Схожість: {me['similarity']}%"),
        ui.p(shared),
        ui.p("Знайди цю людину й дізнайся, де алгоритм помилився."),
    )


def svg(data: dict) -> str:
    """У розмітку потрапляють лише числа, імен тут немає."""
    points = data["points"]
    lines = "".join(
        f'<line x1="{points[a][0]}" y1="{points[a][1]}" x2="{points[b][0]}" y2="{points[b][1]}" '
        'stroke="#00d4ff" stroke-width="0.006" opacity="0.6"/>'
        for a, b in enumerate(data["links"])
    )
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="0.028" fill="#7c5cfc"/>' for x, y in points)
    return f'<svg viewBox="-1.1 -1.1 2.2 2.2" preserveAspectRatio="xMidYMid meet">{lines}{dots}</svg>'


def server(input, output, session):
    me_state = reactive.value({"status": "unknown"})
    error = reactive.value("")
    paper_saved = reactive.value(0)

    @reactive.calc
    def query() -> dict:
        return parse_qs(session.clientdata.url_search().lstrip("?"), keep_blank_values=True)

    def paper() -> bool:
        return "paper" in query()

    def admin() -> bool:
        return is_admin(query().get("key", [""])[0])

    @reactive.effect
    def _poll():
        if "screen" in query() or paper():
            return
        reactive.invalidate_later(3)
        who = input.client_id() if "client_id" in input else None
        if who:
            # Value.set порівнює об'єкти за тотожністю, тож новий словник
            # щоразу перемальовував би форму й скидав повзунки.
            current = room.me(who)
            with reactive.isolate():
                changed = current != me_state()
            if changed:
                me_state.set(current)

    @output
    @render.ui
    def view():
        me = me_state()
        if me["status"] == "unknown":
            return form()
        if me["status"] == "waiting":
            return ui.TagList(
                ui.h1("Є! ✅"),
                ui.p(f"Відповідей у залі: {me['count']}. Двійника покажемо, коли всі закінчать."),
            )
        return result(me)

    @output(id="error")
    @render.ui
    def error_text():
        saved = paper_saved()
        message = error() or (f"Збережено анкет: {saved}" if saved else "")
        clear = ui.tags.script("twinClear()") if saved and not error() else None
        return ui.div(message, clear, class_="error")

    @reactive.effect
    @reactive.event(input.answer)
    def _send():
        who = uuid.uuid4().hex if paper() else input.client_id()
        sent = input.answer()
        try:
            room.answer(who, str(sent["name"]), [int(r) for r in sent["ratings"]])
        except ValueError as problem:
            error.set(str(problem))
            return
        error.set("")
        if paper():
            paper_saved.set(paper_saved() + 1)
        else:
            me_state.set(room.me(who))

    @output
    @render.ui
    def count():
        reactive.invalidate_later(2)
        return ui.HTML(f"Відповідей: <b>{len(room.people)}</b>")

    @output
    @render.ui
    def board():
        reactive.invalidate_later(2)
        return ui.HTML(svg(room.map()))

    @output
    @render.ui
    def names():
        if "names" not in query() or not admin():
            return None
        reactive.invalidate_later(2)
        return ui.div(*[ui.div(line) for line in room.pairs()], class_="names")

    @reactive.effect
    @reactive.event(lambda: input.reveal() if "reveal" in input else 0, ignore_init=True)
    def _reveal():
        if admin():
            room.revealed = True

    @reactive.effect
    @reactive.event(lambda: input.reset() if "reset" in input else 0, ignore_init=True)
    def _reset():
        if admin():
            room.reset()


app = App(app_ui, server)
