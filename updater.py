from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path
from shutil import rmtree
from urllib.request import Request as HttpRequest, urlopen


class Updater:
	def __init__(self, server_path: Path, platform: str, arch: str):
		self.server_path = server_path
		self.platform = platform
		self.arch = arch

	def download_binary(self, desired_version: str) -> bool:
		if not desired_version:
			raise RuntimeError()
		if desired_version == "none":
			return False
		
		self.server_path.mkdir(exist_ok=True)

		version = desired_version if desired_version != "latest" else self.available_version()
		try:
			with contextlib.closing(urlopen(self.download_url(version))) as response:
				with open(self.server_file(), "wb") as out:
					while True:
						block = response.read(5 * 1024 * 1024)
						if not block:
							break
						out.write(block)

			os.chmod(self.server_file(), 0o755)
			self.save_metadata(True, version)
		except:
			return False
		# write update cookie
		return True

	def needs_update(self, desired_version: str) -> bool:
		if desired_version == "none":
			return False

		is_upgrade = self.server_file().is_file()

		if is_upgrade:
			next_update_check, version = self.load_metadata()
		else:
			next_update_check, version = 0, ""

		if desired_version == "latest":
			if int(time.time()) >= next_update_check:
				try:
					available_version = self.available_version()
					if available_version != version:
						version = available_version
						return True
				except BaseException:
					self.save_metadata(False, version)

			return False

		return desired_version != version

	def available_version(self):
		# response url ends with latest available version tag, e.g. "v2026.08.03"
		request = HttpRequest(url=f"{self.repo_url()}/releases/latest", method="HEAD")
		with contextlib.closing(urlopen(request)) as response:
			return response.url.rstrip("/").rsplit("/", 1)[1]

	def remove_server_path(self):
		path = self.server_path
		# Enable long path support on on Windows
		# to avoid errors when cleaning up paths with more than 256 chars.
		# see: https://stackoverflow.com/a/14076169/4643765
		if self.platform == "windows":
			path = Rf"\\?\{self.server_path}"

		rmtree(path, ignore_errors=True)

	def repo_url(self) -> str:
		return "https://github.com/JFryy/systemd-lsp"

	def download_url(self, version: str) -> str:
		# systemd-lsp only ships prebuilt binaries for these targets, see
		# https://github.com/JFryy/systemd-lsp/releases
		release_assets = {
			"osx-arm64": "systemd-lsp-aarch64-apple-darwin",
			"osx-x64": "systemd-lsp-x86_64-apple-darwin",
			"windows-x64": "systemd-lsp-x86_64-pc-windows-msvc.exe",
			"linux-x64": "systemd-lsp-x86_64-unknown-linux-gnu",
		}
		platform_arch = f"{self.platform}-{self.arch}"
		try:
			asset = release_assets[platform_arch]
		except KeyError:
			raise RuntimeError(f"LspSystemd: no prebuilt systemd-lsp binary available for {platform_arch}")
		return f"{self.repo_url()}/releases/download/{version}/{asset}"

	def server_file(self) -> Path:
		binary_name = "systemd-lsp.exe" if self.platform == "windows" else "systemd-lsp"
		return self.server_path / binary_name

	def metadata_file(self) -> Path:
		return self.server_path / "update.json"

	def load_metadata(self) -> tuple[int, str]:
		try:
			data = json.loads(self.metadata_file().read_text(encoding='utf-8'))
			return int(data["timestamp"]), data["version"]
		except (FileNotFoundError, KeyError, TypeError, ValueError):
			return 0, ""

	def save_metadata(self, success: bool, version: str) -> bool:
		next_run_delay = (7 * 24 * 60 * 60) if success else (6 * 60 * 60)
		try:
			self.metadata_file().write_text(
				json.dumps(
					{
						"timestamp": int(time.time()) + next_run_delay,
						"version": version,
					},
				)
			)
			return True
		except:
			return False
