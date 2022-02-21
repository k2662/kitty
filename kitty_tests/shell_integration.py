#!/usr/bin/env python
# License: GPLv3 Copyright: 2022, Kovid Goyal <kovid at kovidgoyal.net>


import os
import shutil
import unittest
from contextlib import contextmanager
from tempfile import TemporaryDirectory

from kitty.constants import terminfo_dir
from kitty.fast_data_types import CURSOR_BEAM
from kitty.shell_integration import setup_zsh_env

from . import BaseTest


def safe_env_for_running_shell(home_dir, rc='', shell='zsh'):
    ans = {
        'PATH': os.environ['PATH'],
        'HOME': home_dir,
        'TERM': 'xterm-kitty',
        'TERMINFO': terminfo_dir,
        'KITTY_SHELL_INTEGRATION': 'enabled',
    }
    if shell == 'zsh':
        ans['ZLE_RPROMPT_INDENT'] = '0'
        with open(os.path.join(home_dir, '.zshenv'), 'w') as f:
            print('unset GLOBAL_RCS', file=f)
        with open(os.path.join(home_dir, '.zshrc'), 'w') as f:
            print(rc, file=f)
        setup_zsh_env(ans)
    return ans


class ShellIntegration(BaseTest):

    @contextmanager
    def run_shell(self, shell='zsh', rc=''):
        with TemporaryDirectory() as home_dir:
            pty = self.create_pty(f'{shell} -il', cwd=home_dir, env=safe_env_for_running_shell(home_dir, rc))
            i = 10
            while i > 0 and not pty.screen_contents().strip():
                pty.process_input_from_child()
                i -= 1
            yield pty

    @unittest.skipUnless(shutil.which('zsh'), 'zsh not installed')
    def test_zsh_integration(self):
        ps1, rps1 = 'left>', '<right'
        with self.run_shell(
            rc=f'''
PS1="{ps1}"
RPS1="{rps1}"
''') as pty:
            self.ae(pty.callbacks.titlebuf, '~')
            q = ps1 + ' ' * (pty.screen.columns - len(ps1) - len(rps1)) + rps1
            self.ae(pty.screen_contents(), q)
            pty.wait_till(lambda: pty.screen.cursor.shape == CURSOR_BEAM)
            pty.send_cmd_to_child('mkdir test && ls -a')
            pty.wait_till(lambda: pty.screen_contents().count('left>') == 2)
            self.ae(pty.last_cmd_output(), str(pty.screen.line(1)))
