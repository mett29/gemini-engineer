import asyncio

from dotenv import load_dotenv
from nicegui import ui, app

from src.gemini_engineer import GeminiEngineer


load_dotenv()


@ui.page('/')
def main():

    cache = app.storage.client
    cache['talk_task'] = None
    cache['chat_task'] = None

    if not cache['chat_task']:
        gemini_engineer = GeminiEngineer(mode="TEXT")
        event_loop = asyncio.get_event_loop()
        chat_task = event_loop.create_task(gemini_engineer.chat())
        cache['chat_task'] = chat_task

    def start_talking():
        try:
            if cache['chat_task']:
                cache['chat_task'].cancel()
                cache['chat_task'] = None
                cache.update({'chat_task': None})
                ui.notify("Gemini chat task terminated.")
            if cache['talk_task']:
                talk_button.props("color='blue'")
                cache['talk_task'].cancel()
                cache.update({'talk_task': None})
                ui.notify("Gemini talk task terminated.")
                return
            talk_button.props("color='red'")
            mode = talk_mode.value
            gemini_engineer = GeminiEngineer(mode=mode)
            event_loop = asyncio.get_event_loop()
            talk_task = event_loop.create_task(gemini_engineer.talk(message_container))
            cache['talk_task'] = talk_task
            ui.notify("Gemini talk task started.")
        except Exception as ex:
            print(str(ex))
            ui.notify("Something went wrong connecting to Gemini, try again.")
            talk_button.props("color='blue'")
            if cache['talk_task']:
                cache['talk_task'].cancel()
            if cache['chat_task']:
                cache['chat_task'].cancel()

    async def send_message() -> None:
        user_message = user_input.value
        user_input.value = ''
        with message_container:
            ui.chat_message(text=user_message, name='You', sent=True)
            response_message = ui.chat_message(name='Gemini', sent=False)
        if gemini_engineer:
            await gemini_engineer.send_message(user_message, response_message)


    # FRONT-END TEMPLATE:
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
            placeholder = 'message'
            user_input = ui.input(placeholder=placeholder).props('rounded outlined input-class=mx-3') \
                .classes('w-full self-center').on('keydown.enter', send_message)
        ui.markdown('built with [NiceGUI](https://nicegui.io) and Gemini') \
            .classes('text-xs self-end mr-8 m-[-1em] text-primary')


ui.run(title='gemini-engineer')
