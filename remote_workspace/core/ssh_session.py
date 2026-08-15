from __future__ import annotations

import os
import posixpath
import socket
import stat
import threading

import paramiko
from PySide6.QtCore import QObject, Signal, Slot

from .models import ConnectionProfile


class SSHSession(QObject):
    output = Signal(str)
    connected = Signal()
    disconnected = Signal()
    error = Signal(str)

    remote_listing = Signal(str, object)
    sftp_error = Signal(str)

    transfer_started = Signal(str)
    transfer_progress = Signal(str, int, int)
    transfer_finished = Signal(str, str)
    transfer_failed = Signal(str)

    remote_mutation_finished = Signal(str, str)

    def __init__(self, profile, password, known_hosts_file, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.password = password
        self.known_hosts_file = known_hosts_file

        self._client = None
        self._channel = None
        self._sftp = None
        self._reader_thread = None
        self._stopping = threading.Event()
        self._lock = threading.Lock()

    @Slot()
    def connect(self):
        try:
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            try:
                client.load_host_keys(self.known_hosts_file)
            except OSError:
                pass

            if self.profile.trust_new_hosts:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())

            kwargs = {
                "hostname": self.profile.host,
                "port": self.profile.port,
                "username": self.profile.username or None,
                "timeout": 12,
                "auth_timeout": 12,
                "banner_timeout": 12,
                "allow_agent": True,
                "look_for_keys": self.profile.auth_type == "key",
            }

            if self.profile.auth_type == "password":
                kwargs["password"] = self.password or None
                kwargs["look_for_keys"] = False
            else:
                if self.profile.key_path:
                    kwargs["key_filename"] = self.profile.key_path
                if self.password:
                    kwargs["passphrase"] = self.password

            client.connect(**kwargs)

            if self.profile.trust_new_hosts:
                try:
                    client.save_host_keys(self.known_hosts_file)
                except OSError:
                    pass

            channel = client.invoke_shell(term="xterm-256color", width=120, height=36)
            channel.settimeout(0.2)

            with self._lock:
                self._client = client
                self._channel = channel

            self._stopping.clear()
            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                name=f"ssh-reader-{self.profile.id}",
                daemon=True,
            )
            self._reader_thread.start()
            self.connected.emit()

        except paramiko.BadHostKeyException as exc:
            self.error.emit(
                f"Host key mismatch for {exc.hostname}. "
                "The server key does not match the saved key."
            )
            self._cleanup()
        except paramiko.AuthenticationException:
            self.error.emit("Authentication failed. Check the username and credentials.")
            self._cleanup()
        except paramiko.SSHException as exc:
            msg = str(exc)
            if "known_hosts" in msg.lower():
                msg = (
                    "This host is not trusted yet. Edit the connection and enable "
                    "'Trust new host keys' for the first connection if you trust it."
                )
            self.error.emit(f"SSH error: {msg}")
            self._cleanup()
        except (socket.error, OSError) as exc:
            self.error.emit(f"Connection error: {exc}")
            self._cleanup()
        except Exception as exc:
            self.error.emit(f"Unexpected error: {exc}")
            self._cleanup()

    def _reader_loop(self):
        try:
            while not self._stopping.is_set():
                with self._lock:
                    channel = self._channel
                if channel is None:
                    break
                if channel.recv_ready():
                    data = channel.recv(65535)
                    if not data:
                        break
                    self.output.emit(data.decode("utf-8", errors="replace"))
                    continue
                if channel.closed:
                    break
                self._stopping.wait(0.03)
        except Exception as exc:
            if not self._stopping.is_set():
                self.error.emit(f"Session read error: {exc}")
        finally:
            self._cleanup()
            self.disconnected.emit()

    def _get_sftp(self):
        if self._sftp is not None:
            return self._sftp
        with self._lock:
            client = self._client
        if client is None:
            raise RuntimeError("SSH session is not connected.")
        self._sftp = client.open_sftp()
        return self._sftp

    @Slot(str)
    def list_remote(self, path):
        try:
            sftp = self._get_sftp()
            normalized = sftp.normalize(path or ".")
            entries = []
            for attr in sftp.listdir_attr(normalized):
                entries.append({
                    "name": attr.filename,
                    "is_dir": stat.S_ISDIR(attr.st_mode),
                    "size": int(attr.st_size or 0),
                    "mtime": int(attr.st_mtime or 0),
                    "mode": int(attr.st_mode or 0),
                })
            entries.sort(key=lambda x: (not x["is_dir"], x["name"].casefold()))
            self.remote_listing.emit(normalized, entries)
        except Exception as exc:
            self.sftp_error.emit(f"Could not list remote directory: {exc}")

    def _ensure_remote_dir(self, sftp, path):
        parts = []
        current = path
        while current not in ("", "/"):
            parts.append(current)
            current = posixpath.dirname(current)
        for target in reversed(parts):
            try:
                sftp.stat(target)
            except IOError:
                sftp.mkdir(target)

    def _local_tree_stats(self, local_path):
        if os.path.isfile(local_path):
            return os.path.getsize(local_path), 1
        total = 0
        count = 0
        for base, _, files in os.walk(local_path):
            for name in files:
                fp = os.path.join(base, name)
                try:
                    total += os.path.getsize(fp)
                    count += 1
                except OSError:
                    pass
        return total, count

    def _remote_tree_stats(self, sftp, remote_path):
        attrs = sftp.stat(remote_path)
        if not stat.S_ISDIR(attrs.st_mode):
            return int(attrs.st_size or 0), 1
        total = 0
        count = 0
        stack = [remote_path]
        while stack:
            current = stack.pop()
            for attr in sftp.listdir_attr(current):
                child = posixpath.join(current, attr.filename)
                if stat.S_ISDIR(attr.st_mode):
                    stack.append(child)
                else:
                    total += int(attr.st_size or 0)
                    count += 1
        return total, count

    @Slot(str, str)
    def upload_path(self, local_path, remote_dir):
        try:
            sftp = self._get_sftp()
            remote_dir = sftp.normalize(remote_dir or ".")
            total_bytes, file_count = self._local_tree_stats(local_path)
            label = f"Uploading {os.path.basename(local_path)}"
            self.transfer_started.emit(label)

            transferred_total = 0

            def upload_file(src, dst):
                nonlocal transferred_total
                base_before = transferred_total

                def cb(done, _total):
                    self.transfer_progress.emit(
                        label,
                        base_before + done,
                        max(1, total_bytes),
                    )
                sftp.put(src, dst, callback=cb, confirm=True)
                transferred_total += os.path.getsize(src)
                self.transfer_progress.emit(label, transferred_total, max(1, total_bytes))

            if os.path.isfile(local_path):
                remote_path = posixpath.join(remote_dir, os.path.basename(local_path))
                upload_file(local_path, remote_path)
            else:
                root_name = os.path.basename(local_path.rstrip(os.sep))
                remote_root = posixpath.join(remote_dir, root_name)
                self._ensure_remote_dir(sftp, remote_root)
                for base, dirs, files in os.walk(local_path):
                    rel = os.path.relpath(base, local_path)
                    rel = "" if rel == "." else rel.replace(os.sep, "/")
                    current_remote = remote_root if not rel else posixpath.join(remote_root, rel)
                    self._ensure_remote_dir(sftp, current_remote)
                    for d in dirs:
                        self._ensure_remote_dir(sftp, posixpath.join(current_remote, d))
                    for name in files:
                        upload_file(
                            os.path.join(base, name),
                            posixpath.join(current_remote, name),
                        )

            self.transfer_finished.emit(
                f"Uploaded {os.path.basename(local_path)} ({file_count} file(s))",
                remote_dir,
            )
        except Exception as exc:
            self.transfer_failed.emit(f"Upload failed: {exc}")

    @Slot(str, str)
    def download_path(self, remote_path, local_dir):
        try:
            sftp = self._get_sftp()
            local_dir = os.path.abspath(local_dir)
            os.makedirs(local_dir, exist_ok=True)

            total_bytes, file_count = self._remote_tree_stats(sftp, remote_path)
            name = posixpath.basename(remote_path.rstrip("/")) or "download"
            label = f"Downloading {name}"
            self.transfer_started.emit(label)

            transferred_total = 0

            def download_file(src, dst):
                nonlocal transferred_total
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                attrs = sftp.stat(src)
                file_size = int(attrs.st_size or 0)
                base_before = transferred_total

                def cb(done, _total):
                    self.transfer_progress.emit(
                        label,
                        base_before + done,
                        max(1, total_bytes),
                    )
                sftp.get(src, dst, callback=cb)
                transferred_total += file_size
                self.transfer_progress.emit(label, transferred_total, max(1, total_bytes))

            attrs = sftp.stat(remote_path)
            if stat.S_ISDIR(attrs.st_mode):
                local_root = os.path.join(local_dir, name)
                os.makedirs(local_root, exist_ok=True)
                stack = [(remote_path, local_root)]
                while stack:
                    current_remote, current_local = stack.pop()
                    for attr in sftp.listdir_attr(current_remote):
                        src = posixpath.join(current_remote, attr.filename)
                        dst = os.path.join(current_local, attr.filename)
                        if stat.S_ISDIR(attr.st_mode):
                            os.makedirs(dst, exist_ok=True)
                            stack.append((src, dst))
                        else:
                            download_file(src, dst)
            else:
                download_file(remote_path, os.path.join(local_dir, name))

            self.transfer_finished.emit(
                f"Downloaded {name} ({file_count} file(s))",
                local_dir,
            )
        except Exception as exc:
            self.transfer_failed.emit(f"Download failed: {exc}")

    @Slot(str, str)
    def remote_rename(self, old_path, new_path):
        try:
            sftp = self._get_sftp()
            sftp.rename(old_path, new_path)
            self.remote_mutation_finished.emit(
                "Renamed remote item",
                posixpath.dirname(new_path) or "/",
            )
        except Exception as exc:
            self.sftp_error.emit(f"Rename failed: {exc}")

    @Slot(str)
    def remote_mkdir(self, path):
        try:
            sftp = self._get_sftp()
            sftp.mkdir(path)
            self.remote_mutation_finished.emit(
                "Created remote folder",
                posixpath.dirname(path) or "/",
            )
        except Exception as exc:
            self.sftp_error.emit(f"Create folder failed: {exc}")

    def _remote_remove_recursive(self, sftp, path):
        attrs = sftp.stat(path)
        if stat.S_ISDIR(attrs.st_mode):
            for attr in sftp.listdir_attr(path):
                self._remote_remove_recursive(
                    sftp,
                    posixpath.join(path, attr.filename),
                )
            sftp.rmdir(path)
        else:
            sftp.remove(path)

    @Slot(str)
    def remote_delete(self, path):
        try:
            sftp = self._get_sftp()
            self._remote_remove_recursive(sftp, path)
            self.remote_mutation_finished.emit(
                "Deleted remote item",
                posixpath.dirname(path) or "/",
            )
        except Exception as exc:
            self.sftp_error.emit(f"Delete failed: {exc}")

    @Slot(str)
    def send(self, data):
        with self._lock:
            channel = self._channel
        if channel and not channel.closed:
            try:
                channel.send(data)
            except Exception as exc:
                self.error.emit(f"Send error: {exc}")

    @Slot(int, int)
    def resize(self, columns, rows):
        with self._lock:
            channel = self._channel
        if channel and not channel.closed:
            try:
                channel.resize_pty(width=max(20, columns), height=max(5, rows))
            except Exception:
                pass

    @Slot()
    def disconnect(self):
        self._stopping.set()
        self._cleanup()
        self.disconnected.emit()

    def _cleanup(self):
        sftp = self._sftp
        self._sftp = None
        with self._lock:
            channel = self._channel
            client = self._client
            self._channel = None
            self._client = None

        for obj in (sftp, channel, client):
            if obj is not None:
                try:
                    obj.close()
                except Exception:
                    pass
