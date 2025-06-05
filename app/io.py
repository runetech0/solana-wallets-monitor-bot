from typing import List, Generator, Optional
import itertools
import os
import random
import aiofiles
import asyncio
from typing import List, Optional


class AioWriterTextFile:
    def __init__(
        self,
        file: str,
        asyncio_lock: Optional[asyncio.Lock] = None,
        encoding: str = "UTF-8",
    ) -> None:
        self.encoding = encoding
        if not os.path.exists(file):
            with open(file, "w", encoding=self.encoding) as _:
                pass
        self.file = file
        if asyncio_lock is None:
            self.lock = asyncio.Lock()
        else:
            self.lock = asyncio_lock

    async def overwrite(self, string: str) -> None:
        async with self.lock:
            async with aiofiles.open(self.file, "w", encoding=self.encoding) as f:
                await f.write(string)

    async def append(self, text: str) -> None:
        async with self.lock:
            text = f"\n{text}"
            async with aiofiles.open(self.file, mode="a", encoding=self.encoding) as f:
                await f.write(text)

    async def append_list(self, string_list: List[str]) -> None:
        text = "\n".join(string_list)
        text = f"\n{text}"
        return await self.append(text)

    async def overwrite_with_list(self, string_list: List[str]) -> None:
        text = "\n".join(string_list)
        return await self.overwrite(text)

    async def file_text(self) -> str:
        async with self.lock:
            async with aiofiles.open(self.file, mode="r", encoding=self.encoding) as f:
                return await f.read()


def write_list_to_txt(file: str, string_list: List[str]) -> None:
    with open(file, "w", encoding="utf-8") as f:
        f.write("\n".join(string_list))


def append_to_txt_file(file: str, text: str) -> None:
    if not os.path.exists(file):
        with open(file, "w", encoding="UTF-8") as f:
            pass
    else:
        text = f"\n{text}"

    with open(file, "a", encoding="UTF-8") as f:
        f.write(text)


def files_in_folder(folder: str) -> List[str]:
    path: str = "./"
    filenames: list[str] = []
    for path, _, filenames in os.walk(folder):
        break
    return [f"{path}/{filename}" for filename in filenames]


def read_txt_lines(filename: str) -> List[str]:
    raw = open(filename, encoding="utf-8").read().splitlines()
    return [r.strip() for r in raw if r.strip() != ""]


class TextLineReader:
    def __init__(self, text_file: str, shuffle_lines: bool = False):
        self._text_file = text_file
        self._lines = read_txt_lines(text_file)
        if shuffle_lines:
            random.shuffle(self._lines)
        self._lines_gen = self.__line_gen()
        self._lines_gen_rotating = self.__line_gen(cycle=True)
        self._used: List[str] = []

    @property
    def total_lines(self) -> int:
        return len(self._lines)

    def __line_gen(self, cycle: bool = False) -> Generator[str, None, None]:
        if cycle:
            for line in itertools.cycle(self._lines):
                yield line
        else:
            for line in self._lines:
                yield line

    def next_line(self) -> str:
        line = next(self._lines_gen)
        self._used.append(line)
        return line

    def next_line_rotating(self) -> str:
        return next(self._lines_gen_rotating)

    def write_back_remaining(self) -> None:
        """Write the unused lines"""
        unused = [line for line in self._lines if line not in self._used]
        with open(self._text_file, "w", encoding="UTF-8") as f:
            f.write("\n".join(unused))

    def get_random(self, default: Optional[str] = None) -> Optional[str]:
        try:
            return random.choice(self._lines)

        except IndexError:
            return default
