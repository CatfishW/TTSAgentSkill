#!/usr/bin/env python3
"""Text2SpeechSkill CLI - Agent skill for Qwen3-TTS text-to-speech operations"""

import argparse
import json
import requests
import sys
import os
from pathlib import Path
from typing import Optional, List, BinaryIO
import time
import base64

API_BASE = "https://mc.agaii.org/TTS/api/v1"
LOCAL_API = "http://localhost:24536/api/v1"


class Text2SpeechClient:
    """Client for Text2Speech (TTSWeb) API operations"""

    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def health_check(self) -> dict:
        """Check API health status"""
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=5)
            return resp.json()
        except Exception as e:
            return {"error": str(e), "status": "unavailable"}

    def get_speakers(self) -> List[dict]:
        """Get available preset speakers"""
        resp = self.session.get(f"{self.base_url}/meta/speakers")
        resp.raise_for_status()
        return resp.json()

    def get_languages(self) -> List[dict]:
        """Get supported languages"""
        resp = self.session.get(f"{self.base_url}/meta/languages")
        resp.raise_for_status()
        return resp.json()

    def get_models(self) -> List[dict]:
        """Get loaded models status"""
        resp = self.session.get(f"{self.base_url}/meta/models")
        resp.raise_for_status()
        return resp.json()

    def custom_voice(self, text: str, speaker: str, language: str = "Auto", instruct: Optional[str] = None) -> str:
        """Generate speech with preset speaker voice"""
        payload = {"text": text, "speaker": speaker, "language": language}
        if instruct:
            payload["instruct"] = instruct
        resp = self.session.post(f"{self.base_url}/tts/custom-voice", json=payload)
        resp.raise_for_status()
        return resp.json()["job_id"]

    def voice_design(self, text: str, instruct: str, language: str = "Auto") -> str:
        """Generate speech with natural language voice description"""
        payload = {"text": text, "instruct": instruct, "language": language}
        resp = self.session.post(f"{self.base_url}/tts/voice-design", json=payload)
        resp.raise_for_status()
        return resp.json()["job_id"]

    def voice_clone(self, text: str, audio_path: str, language: str = "Auto",
                    ref_text: Optional[str] = None, x_vector_only: bool = False,
                    instruct: Optional[str] = None) -> str:
        """Clone voice from reference audio"""
        with open(audio_path, 'rb') as f:
            files = {'audio': f}
            data = {
                'text': text,
                'language': language,
                'x_vector_only_mode': str(x_vector_only).lower(),
                'consent_acknowledged': 'true'
            }
            if ref_text:
                data['ref_text'] = ref_text
            if instruct:
                data['instruct'] = instruct
            resp = self.session.post(f"{self.base_url}/tts/voice-clone", files=files, data=data)
            resp.raise_for_status()
            return resp.json()["job_id"]

    def voice_clone_with_timbre(self, text: str, timbre_speaker: str, language: str = "Auto",
                                 instruct: Optional[str] = None) -> str:
        """Clone voice using preset timbre (no audio upload)"""
        payload = {
            "text": text,
            "speaker": timbre_speaker,
            "language": language,
            "mode": "clone"
        }
        if instruct:
            payload["instruct"] = instruct
        resp = self.session.post(f"{self.base_url}/tts/custom-voice", json=payload)
        resp.raise_for_status()
        return resp.json()["job_id"]

    def voice_design_clone(self, design_text: str, design_instruct: str,
                           clone_texts: List[str], design_language: str = "Auto",
                           clone_language: str = "Auto") -> str:
        """Design voice then clone to multiple texts"""
        payload = {
            "design_text": design_text,
            "design_instruct": design_instruct,
            "clone_texts": clone_texts,
            "design_language": design_language,
            "clone_language": clone_language
        }
        resp = self.session.post(f"{self.base_url}/tts/voice-design-clone", json=payload)
        resp.raise_for_status()
        return resp.json()["job_id"]

    def get_job_status(self, job_id: str) -> dict:
        """Get job status"""
        resp = self.session.get(f"{self.base_url}/jobs/{job_id}/status")
        resp.raise_for_status()
        return resp.json()

    def cancel_job(self, job_id: str):
        """Cancel a running job"""
        resp = self.session.post(f"{self.base_url}/jobs/{job_id}/cancel")
        resp.raise_for_status()

    def download_audio(self, audio_url: str, output_path: str):
        """Download audio file"""
        if audio_url.startswith('/'):
            audio_url = f"{self.base_url}{audio_url}"
        elif not audio_url.startswith('http'):
            audio_url = f"{self.base_url}/{audio_url}"
        resp = self.session.get(audio_url)
        resp.raise_for_status()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(resp.content)

    def wait_for_completion(self, job_id: str, poll_interval: float = 1.0, timeout: float = 300.0,
                           progress_callback=None) -> dict:
        """Wait for job completion"""
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_job_status(job_id)
            if progress_callback:
                progress_callback(status)
            if status["status"] in ["completed", "failed", "cancelled"]:
                return status
            time.sleep(poll_interval)
        raise TimeoutError(f"Job {job_id} timeout")

    def encode_audio(self, audio_path: str) -> dict:
        """Encode audio to tokens"""
        with open(audio_path, 'rb') as f:
            files = {'audio': f}
            resp = self.session.post(f"{self.base_url}/tokenizer/encode", files=files)
            resp.raise_for_status()
            return resp.json()

    def decode_tokens(self, tokens: List[int], output_path: str):
        """Decode tokens to audio"""
        resp = self.session.post(f"{self.base_url}/tokenizer/decode", json={"tokens": tokens})
        resp.raise_for_status()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(resp.content)


def cmd_speak(text: str, speaker: str, output: str, language: str = "Auto", instruct: Optional[str] = None, **kwargs):
    """Text to speech with preset speaker"""
    client = Text2SpeechClient()
    print(f"Generating speech with speaker: {speaker}")
    print(f"Text: {text[:60]}...")

    job_id = client.custom_voice(text, speaker, language, instruct)
    print(f"Job ID: {job_id}")

    def show_progress(status):
        progress = status.get("progress", 0)
        if progress:
            print(f"  Progress: {int(progress * 100)}%", end="\r")

    status = client.wait_for_completion(job_id, progress_callback=show_progress)
    print()

    if status["status"] == "completed" and status.get("audio_url"):
        client.download_audio(status["audio_url"], output)
        print(f"✓ Saved: {output}")
    else:
        print(f"✗ Failed: {status.get('error', 'Unknown')}", file=sys.stderr)
        sys.exit(1)


def cmd_design(text: str, description: str, output: str, language: str = "Auto", **kwargs):
    """Design voice from description"""
    client = Text2SpeechClient()
    print(f"Designing voice: {description}")
    print(f"Text: {text[:60]}...")

    job_id = client.voice_design(text, description, language)
    print(f"Job ID: {job_id}")

    status = client.wait_for_completion(job_id)

    if status["status"] == "completed" and status.get("audio_url"):
        client.download_audio(status["audio_url"], output)
        print(f"✓ Saved: {output}")
    else:
        print(f"✗ Failed: {status.get('error', 'Unknown')}", file=sys.stderr)
        sys.exit(1)


def cmd_clone(audio: str, text: str, output: str, ref_text: Optional[str] = None,
              x_vector_only: bool = False, instruct: Optional[str] = None,
              timbre: Optional[str] = None, language: str = "Auto", **kwargs):
    """Clone voice from audio or timbre"""
    client = Text2SpeechClient()

    if timbre:
        print(f"Using timbre: {timbre}")
        job_id = client.voice_clone_with_timbre(text, timbre, language, instruct)
    else:
        print(f"Cloning from: {audio}")
        if not os.path.exists(audio):
            print(f"✗ Audio file not found: {audio}", file=sys.stderr)
            sys.exit(1)
        job_id = client.voice_clone(text, audio, language, ref_text, x_vector_only, instruct)

    print(f"Text: {text[:60]}...")
    print(f"Job ID: {job_id}")

    status = client.wait_for_completion(job_id)

    if status["status"] == "completed" and status.get("audio_url"):
        client.download_audio(status["audio_url"], output)
        print(f"✓ Saved: {output}")
    else:
        print(f"✗ Failed: {status.get('error', 'Unknown')}", file=sys.stderr)
        sys.exit(1)


def cmd_batch_speak(input_dir: str, output_dir: str, speaker: str,
                    language: str = "Auto", instruct: Optional[str] = None, **kwargs):
    """Batch convert text files to speech"""
    client = Text2SpeechClient()
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    text_files = sorted(input_path.glob("*.txt"))
    print(f"Found {len(text_files)} files to process")

    results = []
    for i, txt_file in enumerate(text_files, 1):
        print(f"\n[{i}/{len(text_files)}] {txt_file.name}")
        text = txt_file.read_text(encoding='utf-8').strip()
        if not text:
            print("  ⚠ Empty file")
            continue

        try:
            job_id = client.custom_voice(text, speaker, language, instruct)
            print(f"  → {job_id}")
            status = client.wait_for_completion(job_id)

            if status["status"] == "completed" and status.get("audio_url"):
                out_file = output_path / f"{txt_file.stem}.wav"
                client.download_audio(status["audio_url"], str(out_file))
                print(f"  ✓ {out_file.name}")
                results.append({"file": txt_file.name, "status": "success", "output": str(out_file)})
            else:
                error = status.get("error", "Unknown")
                print(f"  ✗ {error}")
                results.append({"file": txt_file.name, "status": "failed", "error": error})
        except Exception as e:
            print(f"  ✗ {e}")
            results.append({"file": txt_file.name, "status": "error", "error": str(e)})

    report_file = output_path / "batch_report.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)

    success = sum(1 for r in results if r["status"] == "success")
    print(f"\nComplete: {success}/{len(results)} successful")
    print(f"Report: {report_file}")


def cmd_batch_clone(input_dir: str, output_dir: str, reference_audio: str,
                    ref_text: Optional[str] = None, language: str = "Auto", **kwargs):
    """Batch clone voice for multiple text files"""
    client = Text2SpeechClient()
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(reference_audio):
        print(f"✗ Reference audio not found: {reference_audio}", file=sys.stderr)
        sys.exit(1)

    text_files = sorted(input_path.glob("*.txt"))
    print(f"Cloning voice from: {reference_audio}")
    print(f"Processing {len(text_files)} files")

    results = []
    for i, txt_file in enumerate(text_files, 1):
        print(f"\n[{i}/{len(text_files)}] {txt_file.name}")
        text = txt_file.read_text(encoding='utf-8').strip()
        if not text:
            print("  ⚠ Empty file")
            continue

        try:
            job_id = client.voice_clone(text, reference_audio, language, ref_text)
            print(f"  → {job_id}")
            status = client.wait_for_completion(job_id)

            if status["status"] == "completed" and status.get("audio_url"):
                out_file = output_path / f"{txt_file.stem}.wav"
                client.download_audio(status["audio_url"], str(out_file))
                print(f"  ✓ {out_file.name}")
                results.append({"file": txt_file.name, "status": "success"})
            else:
                error = status.get("error", "Unknown")
                print(f"  ✗ {error}")
                results.append({"file": txt_file.name, "status": "failed", "error": error})
        except Exception as e:
            print(f"  ✗ {e}")
            results.append({"file": txt_file.name, "status": "error", "error": str(e)})

    success = sum(1 for r in results if r["status"] == "success")
    print(f"\nComplete: {success}/{len(results)} successful")


def cmd_encode(audio: str, output: Optional[str] = None, **kwargs):
    """Encode audio to tokens"""
    client = Text2SpeechClient()
    print(f"Encoding: {audio}")

    result = client.encode_audio(audio)
    print(f"✓ Tokens: {result['count']}")

    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Saved: {output}")
    else:
        print(json.dumps(result, indent=2))


def cmd_decode(tokens_file: str, output: str, **kwargs):
    """Decode tokens to audio"""
    client = Text2SpeechClient()
    print(f"Decoding: {tokens_file}")

    with open(tokens_file) as f:
        data = json.load(f)

    tokens = data.get("tokens", data) if isinstance(data, dict) else data
    client.decode_tokens(tokens, output)
    print(f"✓ Saved: {output}")


def cmd_status(**kwargs):
    """Check service status"""
    client = Text2SpeechClient()
    health = client.health_check()

    print("=== Text2Speech Service Status ===")
    print(f"API: {API_BASE}")
    print(f"Status: {health.get('status', 'unknown')}")
    print(f"Version: {health.get('version', 'unknown')}")
    print(f"GPU: {health.get('gpu_available', False)}")
    print(f"Mock Mode: {health.get('mock_mode', False)}")

    if health.get('status') == 'ok':
        try:
            speakers = client.get_speakers()
            print(f"\nSpeakers ({len(speakers)}):")
            for s in speakers[:5]:
                print(f"  - {s['name']}: {s['description'][:50]}...")
            if len(speakers) > 5:
                print(f"  ... and {len(speakers) - 5} more")

            models = client.get_models()
            print(f"\nModels:")
            for m in models:
                status = "✓" if m['loaded'] else "○"
                print(f"  {status} {m['name']}")
        except Exception as e:
            print(f"\nError fetching metadata: {e}")


def cmd_speakers(**kwargs):
    """List available speakers"""
    client = Text2SpeechClient()
    speakers = client.get_speakers()

    print("=== Available Speakers ===")
    for s in speakers:
        print(f"\n{s['name']}")
        print(f"  Description: {s['description']}")
        print(f"  Languages: {', '.join(s['languages'])}")


def cmd_languages(**kwargs):
    """List supported languages"""
    client = Text2SpeechClient()
    languages = client.get_languages()

    print("=== Supported Languages ===")
    for lang in languages:
        print(f"  {lang['code']}: {lang['name']}")


def main():
    parser = argparse.ArgumentParser(description="Text2SpeechSkill - Qwen3-TTS CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # speak - Custom voice
    speak_parser = subparsers.add_parser("speak", help="Text to speech with preset speaker")
    speak_parser.add_argument("text", help="Text to speak (or @file.txt)")
    speak_parser.add_argument("-s", "--speaker", default="vivian", help="Speaker name")
    speak_parser.add_argument("-l", "--language", default="Auto", help="Language")
    speak_parser.add_argument("-i", "--instruct", help="Style instruction")
    speak_parser.add_argument("-o", "--output", required=True, help="Output file")

    # design - Voice design
    design_parser = subparsers.add_parser("design", help="Design voice from description")
    design_parser.add_argument("text", help="Text to speak")
    design_parser.add_argument("-d", "--description", required=True, help="Voice description")
    design_parser.add_argument("-l", "--language", default="Auto", help="Language")
    design_parser.add_argument("-o", "--output", required=True, help="Output file")

    # clone - Voice clone
    clone_parser = subparsers.add_parser("clone", help="Clone voice")
    clone_parser.add_argument("text", help="Text to speak")
    clone_parser.add_argument("-a", "--audio", help="Reference audio file")
    clone_parser.add_argument("-t", "--timbre", help="Use preset timbre instead of audio")
    clone_parser.add_argument("-r", "--ref-text", help="Reference transcript")
    clone_parser.add_argument("-x", "--x-vector-only", action="store_true", help="X-vector only mode")
    clone_parser.add_argument("-i", "--instruct", help="Style instruction")
    clone_parser.add_argument("-l", "--language", default="Auto", help="Language")
    clone_parser.add_argument("-o", "--output", required=True, help="Output file")

    # batch-speak
    batch_speak_parser = subparsers.add_parser("batch-speak", help="Batch text to speech")
    batch_speak_parser.add_argument("input_dir", help="Directory with .txt files")
    batch_speak_parser.add_argument("output_dir", help="Output directory")
    batch_speak_parser.add_argument("-s", "--speaker", default="vivian", help="Speaker")
    batch_speak_parser.add_argument("-l", "--language", default="Auto", help="Language")
    batch_speak_parser.add_argument("-i", "--instruct", help="Style instruction")

    # batch-clone
    batch_clone_parser = subparsers.add_parser("batch-clone", help="Batch voice cloning")
    batch_clone_parser.add_argument("input_dir", help="Directory with .txt files")
    batch_clone_parser.add_argument("output_dir", help="Output directory")
    batch_clone_parser.add_argument("-a", "--audio", required=True, help="Reference audio")
    batch_clone_parser.add_argument("-r", "--ref-text", help="Reference transcript")
    batch_clone_parser.add_argument("-l", "--language", default="Auto", help="Language")

    # encode
    encode_parser = subparsers.add_parser("encode", help="Encode audio to tokens")
    encode_parser.add_argument("audio", help="Audio file")
    encode_parser.add_argument("-o", "--output", help="Output JSON file")

    # decode
    decode_parser = subparsers.add_parser("decode", help="Decode tokens to audio")
    decode_parser.add_argument("tokens_file", help="JSON file with tokens")
    decode_parser.add_argument("-o", "--output", required=True, help="Output audio file")

    # status
    subparsers.add_parser("status", help="Check service status")

    # speakers
    subparsers.add_parser("speakers", help="List speakers")

    # languages
    subparsers.add_parser("languages", help="List languages")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Handle @file.txt syntax
    if hasattr(args, 'text') and args.text.startswith('@'):
        file_path = args.text[1:]
        args.text = Path(file_path).read_text(encoding='utf-8').strip()

    # Route commands
    commands = {
        "speak": cmd_speak,
        "design": cmd_design,
        "clone": cmd_clone,
        "batch-speak": cmd_batch_speak,
        "batch-clone": cmd_batch_clone,
        "encode": cmd_encode,
        "decode": cmd_decode,
        "status": cmd_status,
        "speakers": cmd_speakers,
        "languages": cmd_languages,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(**vars(args))
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
