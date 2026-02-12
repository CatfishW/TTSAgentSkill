#!/usr/bin/env python3
"""Setup for Text2Speech Skill"""

from setuptools import setup, find_packages

with open("SKILL.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="text2speech-skill",
    version="1.0.0",
    author="Text2Speech Team",
    description="Agent skill for Qwen3-TTS text-to-speech operations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CatfishW/TTSAgentSkill",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "text2speech=text2speech_skill.cli:main",
            "t2s=text2speech_skill.cli:main",
        ],
    },
)
