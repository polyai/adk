"""WebRTC call session for poly call.

Handles WebSocket signaling, WebRTC peer connection, and bidirectional audio I/O.

System requirements: ffmpeg must be installed (brew install ffmpeg / apt install ffmpeg).
"""

import asyncio
import json
import logging
import queue
import uuid
from fractions import Fraction

import numpy as np
import sounddevice as sd
from aiortc import AudioStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.sdp import candidate_from_sdp
from av import AudioFrame
from websockets.asyncio.client import connect as ws_connect

logger = logging.getLogger(__name__)

SAMPLE_RATE = 48000
CHANNELS = 1
# aiortc AudioStreamTrack delivers 20ms frames at 48kHz → 960 samples
FRAME_SAMPLES = 960


class EchoCanceller:
    """Acoustic echo cancellation via speexdsp.

    The speaker callback feeds the reference signal (what was played);
    MicrophoneTrack.recv() runs each captured frame through process() to
    subtract the echo before it reaches the server.
    """

    # 320ms of echo history — enough for near-field laptop acoustics
    _FILTER_LENGTH = FRAME_SAMPLES * 16

    def __init__(self) -> None:
        try:
            import speexdsp
        except ImportError as exc:
            raise ImportError(
                "speexdsp is required for echo cancellation.\n"
                "Install with: uv pip install speexdsp\n"
                "(macOS may also need: brew install speexdsp)"
            ) from exc
        self._ec = speexdsp.EchoCanceller.create(FRAME_SAMPLES, self._FILTER_LENGTH, SAMPLE_RATE)
        self._ref_queue: queue.SimpleQueue[np.ndarray] = queue.SimpleQueue()

    def push_reference(self, ref_int16: np.ndarray) -> None:
        """Called from the speaker output callback with the frame that was just played."""
        self._ref_queue.put(ref_int16)

    def process(self, mic_int16: np.ndarray) -> np.ndarray:
        """Return echo-cancelled mic frame (int16 mono, same shape as input)."""
        try:
            ref = self._ref_queue.get_nowait()
        except queue.Empty:
            ref = np.zeros(FRAME_SAMPLES, dtype="int16")
        out = self._ec.process(mic_int16.tobytes(), ref.tobytes())
        return np.frombuffer(out, dtype="int16").copy()


class MicrophoneTrack(AudioStreamTrack):
    """Captures audio from the default microphone and yields AudioFrames."""

    kind = "audio"

    def __init__(self, aec: EchoCanceller | None = None) -> None:
        super().__init__()
        self._aec = aec
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
            callback=self._callback,
        )
        self._stream.start()
        self._pts = 0

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time,  # noqa: ANN001
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            logger.debug("sounddevice input status: %s", status)
        self._queue.put(indata.copy())

    async def recv(self) -> AudioFrame:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, self._queue.get)

        if self._aec is not None:
            data = self._aec.process(data.squeeze())

        frame = AudioFrame(format="s16", layout="mono", samples=FRAME_SAMPLES)
        frame.planes[0].update(data.tobytes())
        frame.sample_rate = SAMPLE_RATE
        frame.pts = self._pts
        frame.time_base = Fraction(1, 48000)
        self._pts += FRAME_SAMPLES
        return frame

    def stop(self) -> None:
        self._stream.stop()
        self._stream.close()
        super().stop()


class SpeakerSink:
    """Receives remote audio frames and plays them through the default speaker.

    Uses a callback-based OutputStream so playback never blocks the event loop.
    When an EchoCanceller is provided, the callback pushes each played frame as
    the AEC reference so the mic can subtract the echo.
    """

    def __init__(self, aec: EchoCanceller | None = None) -> None:
        self._queue: queue.SimpleQueue[np.ndarray] = queue.SimpleQueue()
        self._logged_format = False

        def _callback(
            outdata: np.ndarray,
            frames: int,
            time,  # noqa: ANN001
            status: sd.CallbackFlags,
        ) -> None:
            if status:
                logger.debug("sounddevice output status: %s", status)
            try:
                data = self._queue.get_nowait()
                n = min(len(data), frames)
                outdata[:n, 0] = data[:n]
                outdata[n:, 0] = 0.0
            except queue.Empty:
                outdata[:, 0] = 0.0

            if aec is not None:
                # Push what was ACTUALLY played (including silence) as the AEC reference.
                ref = (outdata[:, 0] * 32768.0).clip(-32768, 32767).astype("int16")
                aec.push_reference(ref)

        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=FRAME_SAMPLES,
            callback=_callback,
        )
        self._stream.start()

    def write(self, frame: AudioFrame) -> None:
        """Decode an incoming AudioFrame and enqueue it for playback."""
        fmt = frame.format.name
        n_channels = len(frame.layout.channels)
        if not self._logged_format:
            layout = frame.layout.name if hasattr(frame.layout, "name") else str(frame.layout)
            logger.warning(
                "first remote frame: format=%s layout=%s channels=%s sample_rate=%s samples=%s planar=%s",
                fmt,
                layout,
                n_channels,
                frame.sample_rate,
                frame.samples,
                frame.format.is_planar,
            )
            self._logged_format = True

        if "flt" in fmt:
            raw = np.frombuffer(bytes(frame.planes[0]), dtype="float32").copy()
            if not frame.format.is_planar and n_channels > 1:
                raw = raw[::n_channels]
        else:
            raw = np.frombuffer(bytes(frame.planes[0]), dtype="int16").astype("float32") / 32768.0
            if not frame.format.is_planar and n_channels > 1:
                raw = raw[::n_channels]

        if frame.sample_rate != SAMPLE_RATE:
            resampled_len = int(len(raw) * SAMPLE_RATE / frame.sample_rate)
            raw = np.interp(
                np.linspace(0, len(raw) - 1, resampled_len),
                np.arange(len(raw)),
                raw,
            ).astype("float32")

        self._queue.put(raw)

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()


class CallSession:
    """Manages the full lifecycle of a poly call: signaling + WebRTC + audio."""

    def __init__(
        self,
        signaling_url: str,
        auth_payload: dict,
        account_id: str,
        project_id: str,
    ) -> None:
        self._signaling_url = signaling_url
        self._auth_payload = auth_payload
        self._account_id = account_id
        self._project_id = project_id
        # sessionId is assigned by the server in the answer; start empty like the browser does
        self._session_id: str = ""
        self._call_sid = f"LOCAL-{uuid.uuid4()}"

    async def run(self) -> None:
        """Connect to the signaling server, perform the WebRTC handshake, and stream audio."""
        aec = EchoCanceller()
        speaker = SpeakerSink(aec=aec)
        mic = MicrophoneTrack(aec=aec)
        pc = RTCPeerConnection()
        pc.addTrack(mic)

        @pc.on("track")
        def on_track(track):  # noqa: ANN001
            if track.kind == "audio":
                asyncio.ensure_future(self._drain_audio(track, speaker))

        try:
            async with ws_connect(self._signaling_url) as ws:
                offer = await pc.createOffer()
                await pc.setLocalDescription(offer)

                # Wait for ICE gathering to complete before sending the offer
                await self._wait_for_ice_gathering(pc)

                offer_msg = {
                    "type": "offer",
                    "sessionId": "",
                    "callSid": self._call_sid,
                    "caller": "adk-cli",
                    "accountId": self._account_id,
                    "projectId": self._project_id,
                    "data": {
                        "type": "offer",
                        "sdp": pc.localDescription.sdp,
                    },
                    **self._auth_payload,
                }
                await ws.send(json.dumps(offer_msg))

                async for raw in ws:
                    msg = json.loads(raw)
                    msg_type = msg.get("type")

                    if msg_type == "answer":
                        # Server assigns the sessionId; capture it for ICE and close messages
                        self._session_id = msg.get("sessionId", "")
                        sdp = msg.get("data", {}).get("sdp") or msg.get("sdp")
                        await pc.setRemoteDescription(RTCSessionDescription(type="answer", sdp=sdp))

                    elif msg_type == "ice-candidate":
                        candidate_data = msg.get("data") or msg
                        sdp_str = candidate_data.get("candidate", "")
                        if sdp_str:
                            # Strip leading "candidate:" prefix if present
                            sdp_str = sdp_str.removeprefix("candidate:")
                            candidate = candidate_from_sdp(sdp_str)
                            candidate.sdpMid = candidate_data.get("sdpMid")
                            candidate.sdpMLineIndex = candidate_data.get("sdpMLineIndex")
                            await pc.addIceCandidate(candidate)

                    elif msg_type == "error":
                        logger.error("Signaling error: %s", msg)
                        break

                    elif msg_type == "close":
                        break

        finally:
            mic.stop()
            speaker.close()
            await pc.close()

    @staticmethod
    async def _wait_for_ice_gathering(pc: RTCPeerConnection) -> None:
        if pc.iceGatheringState == "complete":
            return
        complete = asyncio.Event()

        @pc.on("icegatheringstatechange")
        def on_state_change():  # noqa: ANN001
            if pc.iceGatheringState == "complete":
                complete.set()

        await asyncio.wait_for(complete.wait(), timeout=10)

    @staticmethod
    async def _drain_audio(track, speaker: SpeakerSink) -> None:  # noqa: ANN001
        while True:
            try:
                frame = await track.recv()
                speaker.write(frame)
            except Exception:
                break
