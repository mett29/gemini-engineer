import os
import base64
import asyncio
import traceback

from dotenv import load_dotenv
import numpy as np
import sounddevice as sd
from google import genai
from nicegui import ui


load_dotenv()


class GeminiEngineer:

    def __init__(self, mode: str = "AUDIO"):
        self.audio_stream = None
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.send_text_task = None
        self.receive_audio_task = None

        # Model settings
        self.mode = mode
        self.model = "models/gemini-2.0-flash-exp"
        self.model_config = {"generation_config": {"response_modalities": [self.mode]}}
        GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
        self.client = genai.Client(api_key=GOOGLE_API_KEY, http_options={"api_version": "v1alpha"})

        # Audio settings
        self.channels = 1
        self.chunk_size = 512
        self.send_sample_rate = 16000
        self.receive_sample_rate = 24000


    async def send_text(self):
        while True:
            text = await asyncio.to_thread(
                input,
                "message (enter 'q' to exit) > ",
            )
            if text.lower() == "q":
                break
            await self.session.send(text or ".", end_of_turn=True)


    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(msg)


    async def listen_audio(self):
        self.audio_stream = await asyncio.to_thread(
            sd.InputStream,
            samplerate=self.send_sample_rate,
            channels=self.channels,
            dtype=np.int16,
            blocksize=self.chunk_size
        )
        self.audio_stream.start()
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, self.chunk_size)
            encoded_data = base64.b64encode(data[0]).decode("utf-8")
            await self.out_queue.put({"data": encoded_data, "mime_type": "audio/pcm"})


    async def receive_audio(self, message_container = None):
        """
        Background task to reads from the websocket and write pcm chunks to the output queue.
        """
        while True:
            turn = self.session.receive()
            received_text = ''
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                    continue
                if text := response.text:
                    received_text += text
            if message_container:
                with message_container:
                    ui.markdown(content=received_text)
                    ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

            # If you interrupt the model, it sends a turn_complete.
            # For interruptions to work, we need to stop playback.
            # So empty out the audio queue because it may have loaded
            # much more audio than has played yet.
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()


    async def play_audio(self):
        stream = await asyncio.to_thread(
            sd.OutputStream,
            samplerate=self.receive_sample_rate,
            channels=self.channels,
            dtype=np.int16
        )
        stream.start()
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, np.frombuffer(bytestream, dtype=np.int16))


    async def talk(self, message_container = None):
        try:
            async with (
                self.client.aio.live.connect(model=self.model, config=self.model_config) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session

                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue()

                send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                tg.create_task(self.receive_audio(message_container))
                tg.create_task(self.play_audio())

                await send_text_task
                raise asyncio.CancelledError("User requested exit")

        except asyncio.CancelledError:
            pass
        except Exception as ex:
            if self.audio_stream:
                self.audio_stream.close()
            traceback.print_exception(ex)
        finally:
            if self.audio_stream:
                self.audio_stream.close()


    async def keep_session_alive(self):
        try:
            while True:
                await asyncio.sleep(1)
        except Exception as ex:
            print(f"Error during session: {ex}")


    async def chat(self):
        try:
            async with self.client.aio.live.connect(model=self.model, config=self.model_config) as session:
                self.session = session
                print("Connected to session.")
                await self.keep_session_alive()
        except Exception as ex:
            print(str(ex))
            raise asyncio.CancelledError("Cannot connect to session, try again.")


    async def send_message(self, text: str, response_message):
        if self.session:
            await self.session.send(text, end_of_turn=True)
            response = ''
            async for chunk in self.session.receive():
                if chunk.text:
                    response += chunk.text
                response_message.clear()
                with response_message:
                    ui.html(content=response)
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
        else:
            print("Session not initialized yet.")



if __name__ == "__main__":
    main = GeminiEngineer()
    asyncio.run(main.run())
