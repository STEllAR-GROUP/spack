# Copyright 2013-2020 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import subprocess

import pytest

import spack.cmd
import spack.main
from spack.cmd.commands import _positional_to_subroutine

commands = spack.main.SpackCommand('commands')

parser = spack.main.make_argument_parser()
spack.main.add_all_commands(parser)


def test_commands_by_name():
    """Test default output of spack commands."""
    out1 = commands()
    assert out1.strip().split('\n') == sorted(spack.cmd.all_commands())

    out2 = commands('--format=names')
    assert out1 == out2


def test_subcommands():
    """Test subcommand traversal."""
    out = commands('--format=subcommands')
    assert 'spack mirror create' in out
    assert 'spack buildcache list' in out
    assert 'spack repo add' in out
    assert 'spack pkg diff' in out
    assert 'spack url parse' in out
    assert 'spack view symlink' in out


def test_rst():
    """Do some simple sanity checks of the rst writer."""
    commands('--format=rst')


def test_rst_with_input_files(tmpdir):
    filename = tmpdir.join('file.rst')
    with filename.open('w') as f:
        f.write('''
.. _cmd-spack-fetch:
cmd-spack-list:
.. _cmd-spack-stage:
_cmd-spack-install:
.. _cmd-spack-patch:
''')

    out = commands('--format=rst', str(filename))
    for name in ['fetch', 'stage', 'patch']:
        assert (':ref:`More documentation <cmd-spack-%s>`' % name) in out

    for name in ['list', 'install']:
        assert (':ref:`More documentation <cmd-spack-%s>`' % name) not in out


def test_rst_with_header(tmpdir):
    fake_header = 'this is a header!\n\n'

    filename = tmpdir.join('header.txt')
    with filename.open('w') as f:
        f.write(fake_header)

    out = commands('--format=rst', '--header', str(filename))
    assert out.startswith(fake_header)

    with pytest.raises(spack.main.SpackCommandError):
        commands('--format=rst', '--header', 'asdfjhkf')


def test_rst_update(tmpdir):
    update_file = tmpdir.join('output')

    # not yet created when commands is run
    commands('--update', str(update_file))
    assert update_file.exists()
    with update_file.open() as f:
        assert f.read()

    # created but older than commands
    with update_file.open('w') as f:
        f.write('empty\n')
    update_file.setmtime(0)
    commands('--update', str(update_file))
    assert update_file.exists()
    with update_file.open() as f:
        assert f.read() != 'empty\n'

    # newer than commands
    with update_file.open('w') as f:
        f.write('empty\n')
    commands('--update', str(update_file))
    assert update_file.exists()
    with update_file.open() as f:
        assert f.read() == 'empty\n'


def test_update_with_header(tmpdir):
    update_file = tmpdir.join('output')

    # not yet created when commands is run
    commands('--update', str(update_file))
    assert update_file.exists()
    with update_file.open() as f:
        assert f.read()
    fake_header = 'this is a header!\n\n'

    filename = tmpdir.join('header.txt')
    with filename.open('w') as f:
        f.write(fake_header)

    # created, newer than commands, but older than header
    commands('--update', str(update_file), '--header', str(filename))

    # newer than commands and header
    commands('--update', str(update_file), '--header', str(filename))


def test_no_pipe_error():
    """Make sure we don't see any pipe errors when piping output."""

    proc = subprocess.Popen(
        ['spack', 'commands', '--format=rst'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Call close() on stdout to cause a broken pipe
    proc.stdout.close()
    returncode = proc.wait()
    stderr = proc.stderr.read().decode('utf-8')

    assert 'Broken pipe' not in stderr


def test_bash_completion():
    """Test the bash completion writer."""
    out = commands('--format=bash')

    # Make sure header not included
    assert '_bash_completion_spack () {' not in out
    assert '_all_packages () {' not in out

    # Make sure subcommands appear
    assert '_spack_remove () {' in out
    assert '_spack_compiler_find () {' in out

    # Make sure aliases appear
    assert '_spack_rm () {' in out
    assert '_spack_compiler_add () {' in out

    # Make sure options appear
    assert '-h --help' in out

    # Make sure subcommands are called
    for function in _positional_to_subroutine.values():
        assert '"$(_{0})"'.format(function) in out
