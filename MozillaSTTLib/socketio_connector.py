import logging
import uuid
from sanic import Blueprint, response
from sanic.request import Request
from socketio import AsyncServer
from typing import Optional, Text, Any, List, Dict, Iterable, Callable, Awaitable

from sanic.response import HTTPResponse

from rasa.core.channels.channel import InputChannel
from rasa.core.channels.channel import UserMessage, OutputChannel

import deepspeech
from deepspeech import Model
import scipy.io.wavfile as wav

import os
import sys
import io
import torch
import time
import numpy as np
from collections import OrderedDict
import urllib

import librosa

from TTS.models.tacotron import Tacotron
from TTS.layers import *
from TTS.utils.data import *
from TTS.utils.audio import AudioProcessor
from TTS.utils.generic_utils import load_config
from TTS.utils.text import text_to_sequence
from TTS.utils.synthesis import synthesis
from utils.text.symbols import symbols, phonemes
from TTS.utils.visual import visualize


logger = logging.getLogger(__name__)

def load_deepspeech_model():
    N_FEATURES = 25
    N_CONTEXT = 9
    BEAM_WIDTH = 500
    LM_ALPHA = 0.75
    LM_BETA = 1.85

    ds = Model('deepspeech-0.9.3-models.pbmm')
    return ds


def load_tts_model():

    MODEL_PATH = './tts_model/best_model.pth.tar'
    CONFIG_PATH = './tts_model/config.json'
    CONFIG = load_config(CONFIG_PATH)
    use_cuda = False

    num_chars = len(phonemes) if CONFIG.use_phonemes else len(symbols)
    model = Tacotron(num_chars, CONFIG.embedding_size, CONFIG.audio['num_freq'], CONFIG.audio['num_mels'], CONFIG.r, attn_windowing=False)


    num_chars = len(phonemes) if CONFIG.use_phonemes else len(symbols)
    model = Tacotron(num_chars, CONFIG.embedding_size, CONFIG.audio['num_freq'], CONFIG.audio['num_mels'], CONFIG.r, attn_windowing=False)

    # load the audio processor
    # CONFIG.audio["power"] = 1.3
    CONFIG.audio["preemphasis"] = 0.97
    ap = AudioProcessor(**CONFIG.audio)


    # load model state
    if use_cuda:
        cp = torch.load(MODEL_PATH)
    else:
        cp = torch.load(MODEL_PATH, map_location=lambda storage, loc: storage)

    # load the model
    model.load_state_dict(cp['model'])
    if use_cuda:
        model.cuda()


    #model.eval()
    model.decoder.max_decoder_steps = 1000
    return model, ap, MODEL_PATH, CONFIG, use_cuda

ds = load_deepspeech_model()
model, ap, MODEL_PATH, CONFIG, use_cuda  = load_tts_model()


class SocketBlueprint(Blueprint):
    def __init__(self, sio: AsyncServer, socketio_path, *args, **kwargs):
        self.sio = sio
        self.socketio_path = socketio_path
        super().__init__(*args, **kwargs)

    def register(self, app, options) -> None:
        self.sio.attach(app, self.socketio_path)
        super().register(app, options)


class SocketIOOutput(OutputChannel):

    @classmethod
    def name(cls) -> Text:
        return "socketio"

    def __init__(self, sio, sid, bot_message_evt, message):
        self.sio = sio
        self.sid = sid
        self.bot_message_evt = bot_message_evt
        self.message = message


    def tts(self, model, text, CONFIG, use_cuda, ap, OUT_FILE):
        import numpy as np
        waveform, alignment, spectrogram, mel_spectrogram, stop_tokens = synthesis(model, text, CONFIG, use_cuda, ap)
        ap.save_wav(waveform, OUT_FILE)
        wav_norm = waveform * (32767 / max(0.01, np.max(np.abs(waveform))))
        return alignment, spectrogram, stop_tokens, wav_norm


    def tts_predict(self, MODEL_PATH, sentence, CONFIG, use_cuda, OUT_FILE):

        align, spec, stop_tokens, wav_norm = self.tts(model, sentence, CONFIG, use_cuda, ap, OUT_FILE)
        return wav_norm


    async def _send_audio_message(self, socket_id, response,  **kwargs: Any):
        # type: (Text, Any) -> None
        """Sends a message to the recipient using the bot event."""

        ts = time.time()
        OUT_FILE = str(ts)+'.wav'
        link = "http://localhost:8888/"+OUT_FILE

        wav_norm = self.tts_predict(MODEL_PATH, response['text'], CONFIG, use_cuda, OUT_FILE)


        await self.sio.emit(self.bot_message_evt, {'text':response['text'], "link":link}, room=socket_id)



    async def send_text_message(self, recipient_id: Text, message: Text, **kwargs: Any) -> None:
        """Send a message through this channel."""

        await self._send_audio_message(self.sid, {"text": message})
        
    async def _send_message(self, socket_id: Text, response: Any) -> None:
        """Sends a message to the recipient using the bot event."""

        await self.sio.emit(self.bot_message_evt, response, room=socket_id)

    async def send_image_url(
        self, recipient_id: Text, image: Text, **kwargs: Any
    ) -> None:
        """Sends an image to the output"""

        message = {"attachment": {"type": "image", "payload": {"src": image}}}
        await self._send_message(recipient_id, message)

    async def send_text_with_buttons(
        self,
        recipient_id: Text,
        text: Text,
        buttons: List[Dict[Text, Any]],
        **kwargs: Any,
    ) -> None:
        """Sends buttons to the output."""

        # split text and create a message for each text fragment
        # the `or` makes sure there is at least one message we can attach the quick
        # replies to
        message_parts = text.strip().split("\n\n") or [text]
        messages = [{"text": message, "quick_replies": []} for message in message_parts]

        # attach all buttons to the last text fragment
        for button in buttons:
            messages[-1]["quick_replies"].append(
                {
                    "content_type": "text",
                    "title": button["title"],
                    "payload": button["payload"],
                }
            )

        for message in messages:
            await self._send_message(recipient_id, message)

    async def send_elements(
        self, recipient_id: Text, elements: Iterable[Dict[Text, Any]], **kwargs: Any
    ) -> None:
        """Sends elements to the output."""

        for element in elements:
            message = {
                "attachment": {
                    "type": "template",
                    "payload": {"template_type": "generic", "elements": element},
                }
            }

            await self._send_message(recipient_id, message)

    async def send_custom_json(
        self, recipient_id: Text, json_message: Dict[Text, Any], **kwargs: Any
    ) -> None:
        """Sends custom json to the output"""

        json_message.setdefault("room", recipient_id)

        await self.sio.emit(self.bot_message_evt, **json_message)

    async def send_attachment(
        self, recipient_id: Text, attachment: Dict[Text, Any], **kwargs: Any
    ) -> None:
        """Sends an attachment to the user."""
        await self._send_message(recipient_id, {"attachment": attachment})





class SocketIOInput(InputChannel):
    """A socket.io input channel."""

    @classmethod
    def name(cls) -> Text:
        return "socketio"

    @classmethod
    def from_credentials(cls, credentials):
        credentials = credentials or {}
        return cls(credentials.get("user_message_evt", "user_uttered"),
                   credentials.get("bot_message_evt", "bot_uttered"),
                   credentials.get("namespace"),
                   credentials.get("session_persistence", False),
                   credentials.get("socketio_path", "/socket.io"),
                   )

    def __init__(self,
                 user_message_evt: Text = "user_uttered",
                 bot_message_evt: Text = "bot_uttered",
                 namespace: Optional[Text] = None,
                 session_persistence: bool = False,
                 socketio_path: Optional[Text] = '/socket.io'
                 ):
        self.bot_message_evt = bot_message_evt
        self.session_persistence = session_persistence
        self.user_message_evt = user_message_evt
        self.namespace = namespace
        self.socketio_path = socketio_path


    def get_output_channel(self) -> Optional["OutputChannel"]:
        if self.sio is None:
            rasa.shared.utils.io.raise_warning(
                "SocketIO output channel cannot be recreated. "
                "This is expected behavior when using multiple Sanic "
                "workers or multiple Rasa Open Source instances. "
                "Please use a different channel for external events in these "
                "scenarios."
            )
            return
        return SocketIOOutput(self.sio, self.bot_message_evt)

    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[Any]]
    ) -> Blueprint:
        # Workaround so that socketio works with requests from other origins.
        # https://github.com/miguelgrinberg/python-socketio/issues/205#issuecomment-493769183
        sio = AsyncServer(async_mode="sanic", cors_allowed_origins='*')
        socketio_webhook = SocketBlueprint(
            sio, self.socketio_path, "socketio_webhook", __name__
        )

        # make sio object static to use in get_output_channel
        self.sio = sio

        @socketio_webhook.route("/", methods=["GET"])
        async def health(_: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        @sio.on("connect", namespace=self.namespace)
        async def connect(sid: Text, _) -> None:
            logger.debug(f"User {sid} connected to socketIO endpoint.")

        @sio.on("disconnect", namespace=self.namespace)
        async def disconnect(sid: Text) -> None:
            logger.debug(f"User {sid} disconnected from socketIO endpoint.")

        @sio.on("session_request", namespace=self.namespace)
        async def session_request(sid: Text, data: Optional[Dict]):
            if data is None:
                data = {}
            if "session_id" not in data or data["session_id"] is None:
                data["session_id"] = uuid.uuid4().hex
            if self.session_persistence:
                sio.enter_room(sid, data["session_id"])
            await sio.emit("session_confirm", data["session_id"], room=sid)
            logger.debug(f"User {sid} connected to socketIO endpoint.")

        @sio.on(self.user_message_evt, namespace=self.namespace)
        async def handle_message(sid: Text, data: Dict) -> Any:
            output_channel = SocketIOOutput(sio, self.bot_message_evt)

            if data['message'] == "/get_started":
                message = data['message']
            else:
                ##receive audio
                received_file = 'output_'+sid+'.wav'

                urllib.request.urlretrieve(data['message'], received_file)
                path = os.path.dirname(__file__)

                fs, audio = wav.read("output_{0}.wav".format(sid))
                message = ds.stt(audio)

                await sio.emit(self.user_message_evt, {"text":message}, room=sid)


            message_rasa = UserMessage(message, output_channel, sid,
                                  input_channel=self.name())
            await on_new_message(message_rasa)

        return socketio_webhook
 
