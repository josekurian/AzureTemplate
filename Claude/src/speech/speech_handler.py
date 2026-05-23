"""
speech_handler.py — Phase 7: Speech-to-Text and Text-to-Speech
===============================================================
AI-102 Skills:
  - Azure AI Speech STT: real-time and batch transcription
  - Azure AI Speech TTS: neural voices with SSML for luxury tone
  - Speech service is SEPARATE from Azure OpenAI Whisper — different endpoints
  - AI-102 Cost: STT billed per audio hour; TTS billed per million characters

Restaurant Use Cases:
  - Accessible ordering: visually impaired guests use voice interface
  - Voice sommelier: guests ask wine questions hands-free at the table
  - Kitchen transcription: chef announces daily specials, auto-transcribed for display
  - Accessibility: TTS reads menu aloud in guest's preferred language
"""

import logging
import os
from pathlib import Path

import azure.cognitiveservices.speech as speechsdk

from src.config import RestaurantAIConfig
from src.monitoring.telemetry import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

# Neural voice for luxury restaurant — warm, professional British accent
LUXURY_VOICE = "en-GB-SoniaNeural"
SSML_TEMPLATE = """
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-GB">
  <voice name="{voice}">
    <mstts:express-as style="customerservice" styledegree="1.5">
      <prosody rate="-5%" pitch="-2st">
        {text}
      </prosody>
    </mstts:express-as>
  </voice>
</speak>
"""


class RestaurantSpeechHandler:
    """
    Speech-to-Text and Text-to-Speech for restaurant voice interface.

    AI-102 Note: Speech SDK uses subscription key or token-based auth.
    For Managed Identity: obtain a token from Azure AD and pass as authorization_token.
    """

    def __init__(self, config: RestaurantAIConfig):
        self.config = config
        # Speech endpoint region derived from the resource name convention
        self.speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        self.speech_key = os.getenv("AZURE_SPEECH_KEY", "")  # Stored in Key Vault

    def _get_speech_config(self) -> speechsdk.SpeechConfig:
        """
        Build SpeechConfig.
        AI-102: If using Managed Identity, fetch auth token instead of key.
        """
        if self.speech_key:
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.speech_region,
            )
        else:
            # Token-based auth for Managed Identity scenarios
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential()
            token = credential.get_token("https://cognitiveservices.azure.com/.default").token
            speech_config = speechsdk.SpeechConfig(
                auth_token=f"aad#{os.getenv('AZURE_SPEECH_RESOURCE_ID', '')}#{token}",
                region=self.speech_region,
            )
        return speech_config

    def transcribe_from_microphone(self) -> str:
        """
        Real-time STT from microphone input.
        Restaurant use: voice ordering terminal at the table.
        """
        with tracer.start_as_current_span("speech_to_text_realtime"):
            speech_config = self._get_speech_config()
            speech_config.speech_recognition_language = "en-GB"
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )

            logger.info("Listening for voice input...")
            result = recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info(f"Transcribed: {result.text}")
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("No speech detected.")
                return ""
            else:
                logger.error(f"STT error: {result.reason}")
                return ""

    def transcribe_from_file(self, audio_file_path: str) -> str:
        """
        Batch STT from an audio file.
        Restaurant use: transcribe recorded daily specials announcement.
        """
        with tracer.start_as_current_span("speech_to_text_file") as span:
            span.set_attribute("audio.file", audio_file_path)
            speech_config = self._get_speech_config()
            audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)

            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )
            result = recognizer.recognize_once_async().get()
            return result.text if result.reason == speechsdk.ResultReason.RecognizedSpeech else ""

    def speak_response(self, text: str, output_file: str = "") -> bytes:
        """
        TTS synthesis with SSML for luxury voice quality.
        Restaurant use: AI assistant reads menu descriptions aloud to guests.

        AI-102: TTS cost = per million characters synthesised.
        Using SSML template wraps plain text with neural voice style settings.
        """
        with tracer.start_as_current_span("text_to_speech") as span:
            span.set_attribute("text.length", len(text))
            speech_config = self._get_speech_config()
            speech_config.speech_synthesis_voice_name = LUXURY_VOICE

            # Use file output or in-memory
            if output_file:
                audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
            else:
                audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )

            ssml = SSML_TEMPLATE.format(voice=LUXURY_VOICE, text=text)
            result = synthesizer.speak_ssml_async(ssml).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(f"TTS synthesis complete, {len(result.audio_data)} bytes")
                return result.audio_data
            else:
                cancellation = result.cancellation_details
                logger.error(f"TTS error: {cancellation.reason} — {cancellation.error_details}")
                return b""
