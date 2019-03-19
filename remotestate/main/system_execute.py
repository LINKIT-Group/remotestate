"""
Copyright (c) 2019 LINKIT, The Netherlands. All Rights Reserved.
Author(s): Anthony Potappel

This software may be modified and distributed under the terms of the
MIT license. See the LICENSE file for details.
"""

import asyncio


async def subprocess_reader(output, lines):
    """Parse stdout/ stderr output and store this into a list of lines"""
    while True:
        newline = await output.readline()
        if not newline:
            break
        lines.append(newline.strip().decode())


async def subprocess(command, pathname, stdout_lines, stderr_lines):
    """Wrap command into an async process to capture stdout and stderr separately"""
    process = await asyncio.create_subprocess_exec(*command,
                                                   cwd=pathname,
                                                   stdout=asyncio.subprocess.PIPE,
                                                   stderr=asyncio.subprocess.PIPE)

    await asyncio.wait([subprocess_reader(process.stdout, stdout_lines),
                        subprocess_reader(process.stderr, stderr_lines)])
    return await process.wait()


def system_call(command, pathname=".", verbose=False):
    """Execute a system call using subprocess module,
    return return_code (int), stdout (list of lines) and stderr (list of lines)"""
    if not isinstance(command, list) or False in [isinstance(item, str) for item in command]:
        raise ValueError('Expecting list of strings as input')

    if verbose is True:
        # output command to screen
        argument_string = ' '.join(['\"' + argument + '\"' for argument in command[1:]])
        print('executing: ' + (command[0] + ' ' + argument_string).strip())

    stdout_lines = []
    stderr_lines = []

    asyncio.set_event_loop(asyncio.new_event_loop())
    event_loop = asyncio.get_event_loop()
    return_code = event_loop.run_until_complete(subprocess(command,
                                                           pathname,
                                                           stdout_lines,
                                                           stderr_lines))
    event_loop.close()

    return (return_code, stdout_lines, stderr_lines)
