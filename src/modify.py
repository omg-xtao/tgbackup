import asyncio
import datetime
import random
from asyncio import subprocess, create_subprocess_exec
from pathlib import Path
from tempfile import NamedTemporaryFile

import PIL
from PIL import Image
from moviepy.config import FFMPEG_BINARY

from config import global_logger


async def ffmpeg_run(
    input,
    output,
    pipe_stdin=False,
    pipe_stdout=False,
    pipe_stderr=False,
    quiet=False,
):
    stdin_stream = subprocess.PIPE if pipe_stdin else None
    stdout_stream = subprocess.PIPE if pipe_stdout or quiet else None
    stderr_stream = subprocess.PIPE if pipe_stderr or quiet else None
    cmd = [
        FFMPEG_BINARY,
        "-i",
        input,
        # "-vf",
        # '"tpad=stop_mode=clone:stop_duration=1, drawbox=color=black:t=fill"',
        "-c",
        "copy",
        "-metadata",
        f'title={datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        "-y",
        output,
    ]
    global_logger.debug(cmd)
    p = await create_subprocess_exec(
        *cmd, stdin=stdin_stream, stdout=stdout_stream, stderr=stderr_stream
    )
    ffmpeg_out, err = await p.communicate()


async def modify_pic(img_path: Path):
    img = Image.open(img_path)
    # Get the image dimensions
    width, height = img.size

    # Randomly select a pixel coordinate
    x = random.randint(0, width - 1)
    y = random.randint(0, height - 1)

    # Get the current pixel value
    pixel_value = img.getpixel((x, y))

    await asyncio.sleep(0)
    # Randomly change the pixel value (e.g., to a random RGB value)
    new_pixel_value = tuple(a + 1 if a < 255 else a - 1 for a in pixel_value)
    # Set the new pixel value
    img.putpixel((x, y), new_pixel_value)
    img.save(img_path)
    return img_path


async def modify_video(video: Path, tempdir=None):
    output = tempdir + "/" + Path(video).stem + "_" + Path(video).suffix
    await ffmpeg_run(input=video, output=output)
    return output
