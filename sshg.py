#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Sun Jan 29 2023 15:55:06 by codeskyblue

Clone of [sshw](https://github.com/yinheli/sshw) written in Python

Refs:
- https://python-prompt-toolkit.readthedocs.io/en/master/
- sshpass in python https://gist.github.com/jlinoff/bdd346ffadc226337949
"""

import argparse
import dataclasses
import fcntl
import getpass
import pathlib
import pty
import signal
import struct
import termios
import time
import typing
from dataclasses import dataclass

import yaml
from dataclasses_json import DataClassJsonMixin
from dataclasses_json import config as dconfig
from marshmallow import fields
from pexpect import pxssh
from prompt_toolkit import HTML, Application, print_formatted_text
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

__version__ = "0.1.0"

def make_field(field_name: str = None,
               mm_field=None,
               decorder: typing.Callable = None,
               default=dataclasses.MISSING,
               default_factory=dataclasses.MISSING, **kwargs) -> dataclasses.field:
    return dataclasses.field(metadata=dconfig(field_name=field_name,
                                              mm_field=mm_field, decoder=decorder),
                             default=default,
                             default_factory=default_factory, **kwargs)

def password_decorder(value: typing.Union[str, int]) -> typing.Optional[str]:
    if value is None:
        return None
    return str(value)


def get_console_winsize():
    '''
    Get the console winsize.
    '''
    for fdn in [pty.STDIN_FILENO, pty.STDOUT_FILENO]:
        try:
            packed_data = struct.pack('HHHH', 0, 0, 0, 0)
            packed_winsize = fcntl.ioctl(fdn, termios.TIOCGWINSZ, packed_data)
            winsize = struct.unpack('HHHH', packed_winsize)
            return winsize[0], winsize[1]
        except IOError:
            pass
    return None


def update_window_size(child):
    """Sync window size to child process"""
    winsize = get_console_winsize()
    if winsize:
        rows, cols = winsize
        child.setwinsize(rows, cols)

@dataclass
class CallbackShell(DataClassJsonMixin):
    cmd: str
    delay: typing.Optional[int] = 0


@dataclass
class HostConfig(DataClassJsonMixin):
    name: typing.Optional[str] = None
    user: typing.Optional[str] = None
    port: int = 22
    host: typing.Optional[str] = None
    keypath: typing.Optional[str] = None
    password: typing.Optional[typing.Union[int, str]] = make_field(decorder=password_decorder, default=None)
    callback_shells: typing.Optional[typing.List[CallbackShell]] = make_field(field_name="callback-shells", default=None)
    children: typing.Optional[typing.List["HostConfig"]] = make_field(mm_field=fields.Field(), default=None)
    # url: typing.Optional[str] = None
    via: typing.Optional["HostConfig"] = make_field(mm_field=fields.Field(), default=None)
    _parent: typing.Optional["HostConfig"] = make_field(mm_field=fields.Field(), default=None, init=False, repr=False)

    def post_load(self):
        if self._parent:
            if not self.user:
                self.user = self._parent.user
            if not self.host:
                self.host = self._parent.host
            if not self.port:
                self.port = self._parent.port
            if not self.keypath:
                self.keypath = self._parent.keypath
            if not self.password:
                self.password = self._parent.password
            if not self.callback_shells:
                self.callback_shells = self._parent.callback_shells
            if not self.via:
                self.via = self._parent.via
        
        if not self.name:
            self.name = self.host
        if self.user is None:
            self.user = getpass.getuser()
        for child in self.children or []:
            child._parent = self
            child.post_load()

    def build_cmdargs(self) -> typing.List[str]:
        cmds = ["ssh"]
        if self.port != 22:
            cmds.extend(["-p", str(self.port)])
        if self.keypath:
            cmds.extend(["-i", self.keypath])
        cmds.extend([f"{self.user}@{self.host}"])
        return cmds

    def spawn_ssh(self):
        # https://pexpect.readthedocs.io/en/stable/api/pxssh.html
        if self.via:
            s = spawn_ssh(self.via, reset_prompt=True)
            s.prompt()
            s = spawn_ssh(self, is_local=False, ssh_client=s)
            s.sendline()

            def output_filter(line):
                if line.endswith(b'[PEXPECT]$ '): # quit when back to gateway server
                    s.close()
                    return b""
                return line

            s.interact(output_filter=output_filter)
            print_formatted_text(HTML("<gray>END OF INTERACT</gray>"))
        else:
            s = spawn_ssh(self)
            s.interact()


def spawn_ssh(host_config: HostConfig, is_local: bool = True, ssh_client: pxssh.pxssh = None, reset_prompt: bool = None) -> pxssh.pxssh:
    # https://pexpect.readthedocs.io/en/stable/api/pxssh.html
    cmdargs = host_config.build_cmdargs()
    cmdline = " ".join(cmdargs)
    print_formatted_text(HTML(f"<name>{host_config.name}</name> {cmdline}"), style=style)
        
    s = ssh_client or pxssh.pxssh(ignore_sighup=False)
    keypath = None
    if host_config.keypath:
        keypath = pathlib.Path(host_config.keypath).expanduser()
        if keypath.stat().st_mode & 0o077 != 0:
            print("Warning: keypath mode change to 0600")
            keypath.chmod(0o600)

    s.SSH_OPTS += " -o StrictHostKeyChecking=no"
    if reset_prompt is None:
        reset_prompt = False

    if is_local:
        s.login(host_config.host,
                username=host_config.user,
                password=host_config.password,
                port=host_config.port,
                ssh_key=keypath,
                quiet=False,
                sync_original_prompt=False,
                auto_prompt_reset=reset_prompt)
    else:
        s.login(host_config.host,
                username=host_config.user,
                password=host_config.password,
                port=host_config.port,
                ssh_key=keypath,
                quiet=False,
                auto_prompt_reset=False,
                spawn_local_ssh=False)

    if is_local:
        def sigwinch_passthrough(sig, data):
            p = s.ptyproc
            if not p.closed:
                update_window_size(p)

        signal.signal(signal.SIGWINCH, sigwinch_passthrough)
        update_window_size(s.ptyproc)

    for shell in host_config.callback_shells or []:
        if shell.delay:
            time.sleep(shell.delay)
        s.sendline(shell.cmd)
    return s


# The style sheet.
style = Style.from_dict({
    'active': 'red',
    'name': 'cyan',
    'bbb': '#44ff00 italic',
})

kb = KeyBindings()

@kb.add('q')
@kb.add('c-c')
def exit_(event: KeyPressEvent):
    """
    Pressing Ctrl-Q will exit the user interface.

    Setting a return value means: quit the event loop that drives the user
    interface and return this value from the `Application.run()` call.
    """
    event.app.exit()

class SelectContainer(HSplit):
    def __init__(self, host_configs: typing.List[HostConfig]):
        self._host_configs = host_configs
        self._active_index = 0
        super().__init__(self._gen_host_windows())

    def _gen_host_windows(self):
        host_windows = []
        for index, config in enumerate(self._host_configs):
            prefix = "" if config.children else f" <gray>{config.user}@{config.host}</gray>"
            name = config.name
            if config.children:
                name = f"+ {name}({len(config.children)})"
            if self._active_index == index:
                html_text = "  ➤ " + f"<name>{name}</name>" + prefix
            else:
                html_text = "    " + f"<gray>{name}</gray>" + prefix
            if config.children:
                html_text = f"<b>{html_text}</b>"
            host_windows.append(Window(content=FormattedTextControl(HTML(html_text)), height=1))
        return host_windows

    def _up_hook(self, event: KeyPressEvent):
        index = self.get_active_index()
        self.set_active_index(index - 1)

    def _down_hook(self, event: KeyPressEvent):
        index = self.get_active_index()
        self.set_active_index(index + 1)

    def _enter_hook(self, event: KeyPressEvent):
        index = self.get_active_index()
        config = self._host_configs[index]
        if config.children:
            if config.name == "-parent-":
                self._host_configs = config.children
            else:
                parent = HostConfig(name="-parent-", children=self._host_configs[:])
                self._host_configs = [parent] + config.children
            self.set_active_index(0)
        else:
            event.app.exit(config)

    def get_active_index(self):
        return self._active_index

    def set_active_index(self, index):
        self._active_index = index % len(self.children)
        self._update_active()

    def _update_active(self):
        self.children = self._gen_host_windows()

    def register_key_bindings(self, kb: KeyBindings):
        for key in ['up', 'k']:
            kb.add(key)(self._up_hook)
        for key in ['down', 'j']:
            kb.add(key)(self._down_hook)
        kb.add(Keys.Enter)(self._enter_hook)


def load_config(files: typing.List[str]) -> typing.List[HostConfig]:
    for file in files:
        p = pathlib.Path(file).expanduser()
        if p.exists():
            host_configs = HostConfig.schema().load(yaml.safe_load(p.read_bytes()), many=True)
            for config in host_configs:
                config.post_load()
            return host_configs


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--version", action="store_true")
    parser.add_argument("-c", "--conf", help="config file")
    args = parser.parse_args()
    if args.version:
        print(__version__)
        return

    config_files = ["~/.sshg.yml", "~/.sshx.yml", "~/.sshx.yaml", "~/.sshw.yml", "~/.sshw.yaml"]
    if args.conf:
        config_files = [args.conf]
    host_configs = load_config(config_files)
    hosts_container = SelectContainer(host_configs) #[mymac, pc001, pc002])
    hosts_container.register_key_bindings(kb)

    # <gray>Use the arrow keys to navigate: ↓ ↑ → ←  and / toggles search</gray>
    root_container = HSplit([
        Window(content=FormattedTextControl(HTML('<gray>Use the arrow keys to navigate (support vim style): ↓ ↑ </gray>')), height=1),
        Window(content=FormattedTextControl(HTML('<lightgreen>✨ Select host</lightgreen>')), height=1),
        hosts_container,
    ])

    layout = Layout(root_container)

    app = Application(layout=layout, style=style, key_bindings=kb, full_screen=True)
    host_config: HostConfig = app.run()
    if host_config:
        host_config.spawn_ssh()


if __name__ == '__main__':
    main()
