import os
import asyncio

from google import genai
from dotenv import load_dotenv
from nicegui import ui, app

from src.gemini_engineer import GeminiEngineer


load_dotenv()


@ui.page('/')
def main():

    cache = app.storage.client
    cache['is_talking'] = False
    cache['talk_task'] = None

    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'not-set')
    client = genai.Client(api_key=GOOGLE_API_KEY, http_options={"api_version": "v1alpha"})
    model_id = "gemini-2.0-flash-exp"
    config = {"response_modalities": ["TEXT"]}

    def start_talking():
        try:
            if cache['is_talking'] is True:
                cache['is_talking'] = False
                talk_button.props("color='blue'")
                talk_task = cache['talk_task']
                if talk_task:
                    talk_task.cancel()
                ui.notify("Gemini talk task terminated.")
                return
            cache['is_talking'] = True
            talk_button.props("color='red'")
            mode = talk_mode.value
            gemini_engineer = GeminiEngineer(mode=mode)
            event_loop = asyncio.get_event_loop()
            talk_task = event_loop.create_task(gemini_engineer.run(message_container))
            cache['talk_task'] = talk_task
            ui.notify("Gemini talk task started.")
        except Exception:
            ui.notify("Something went wrong connecting to Gemini, try again ...")
            talk_button.props("color='blue'")
            if talk_task:
                talk_task.cancel()

    async def send() -> None:
        question = user_input.value
        user_input.value = ''

        with message_container:
            ui.chat_message(text=question, name='You', sent=True)
            response_message = ui.chat_message(name='Gemini', sent=False)
            spinner = ui.spinner(type='dots')

        async with client.aio.live.connect(model=model_id, config=config) as session:
            message = question
            print("> ", message, "\n")
            await session.send(message, end_of_turn=True)

            response = ''
            async for chunk in session.receive():
                if chunk.text:
                    response += chunk.text
                response_message.clear()
                with response_message:
                    ui.html(content=response)
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
            message_container.remove(spinner)

    ui.add_css(r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}')

    ui.query('.q-page').classes('flex')
    ui.query('.nicegui-content').classes('w-full')

    with ui.tabs().classes('w-full') as tabs:
        chat_tab = ui.tab('Chat')
    with ui.tab_panels(tabs, value=chat_tab).classes('w-full max-w-2xl mx-auto flex-grow items-stretch'):
        message_container = ui.tab_panel(chat_tab).classes('items-stretch')

    with ui.footer().classes('bg-white'), ui.column().classes('w-full max-w-3xl mx-auto my-6'):
        with ui.row().classes('w-full no-wrap items-center'):
            talk_button = ui.button(on_click=start_talking, icon="mic").props("color='blue'")
            talk_mode = ui.select(options=['TEXT', 'AUDIO'], value="TEXT", label="mode")
            placeholder = 'message' if GOOGLE_API_KEY != 'not-set' else \
                'Please provide your Gemini API key in the Python script first!'
            user_input = ui.input(placeholder=placeholder).props('rounded outlined input-class=mx-3') \
                .classes('w-full self-center').on('keydown.enter', send)
        ui.markdown('built with [NiceGUI](https://nicegui.io) and Gemini') \
            .classes('text-xs self-end mr-8 m-[-1em] text-primary')


ui.run(title='gemini-engineer')