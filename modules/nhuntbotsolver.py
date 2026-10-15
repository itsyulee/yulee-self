# This file is part of NeuraSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# NeuraSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with NeuraSelf-UwU. If not, see <https://www.gnu.org/licenses/>.


"""
Author: Routo
NeuraSelf-UwU - https://github.com/routo-loop/neura-self
"""


import numpy as np
import io
from PIL import Image
import base64


# priorty and encoded images(avoiding I-O for speed) idea taken from owo-dusk

class NeuraSolver:
    PRIORITY_LEVELS = [
        list("abdegkmpqstvwxyz"),
        list("fho"),              
        list("cnru"),           
        list("jl"),              
        list("i"),                
    ]

    MASKS = {
        "a": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAARElEQVQoFWN0mv3/PwOJgIlE9WDlZGliJNYmZG+QZxOyCcTaSpZNZGliQXbSvlRGnAGD7A2ybGJENgHZVnxssmwiSxMARF4PhclsgWMAAAAASUVORK5CYII=",
        "b": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAASCAYAAACAa1QyAAAAO0lEQVQoFWN0mv3/PwMU7EtlZISx8dFM+CRxyQ1yTYzIAYHLD+ji9PMTC7LV+OIJ2Rv0c95wtGmQpwgAPGAN2uSjSi0AAAAASUVORK5CYII=",
        "c": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAALklEQVQoFWN0mv3/PwOJgIlE9WDlZGliQbZpXyojIzIfF5ssm0Y1QYOTcXCnCADdtQb2r0ES3wAAAABJRU5ErkJggg==",
        "d": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAASCAYAAACAa1QyAAAAOUlEQVQoFWNkIBI4zf7/H6aUCcYghR7kmhiRPUisv+jnJxZkJ+1LZWRE5iOzkb1BP+cNR5sGeYoAAJVGDLX7Igd2AAAAAElFTkSuQmCC",
        "e": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAP0lEQVQoFWN0mv3/PwOJgIlE9WDlZGliQbZpXyojIzIfmY3sDbJsYkQ2AdlkfGyybCJLE9EBgexcsmwa5AEBAB/ZDdI5nuFXAAAAAElFTkSuQmCC",
        "f": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAMUlEQVQoFWN0mv3/PwOJgIlE9WDlZGliQbZpXyojIzIfF5ssmxhHAwISnmSFHv00AQDzrwgdUIeJDgAAAABJRU5ErkJggg==",
        "g": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAR0lEQVQoFWN0mv3/PwOJgIlE9WDlZGliQbZpXyojIzIfF5tym2AmEwocsmwiSxNKQMCchy1AkJ1Mlk2MyCbAbCJEk2UTWZoA7Z4N1XlVX20AAAAASUVORK5CYII=",
        "h": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAASCAYAAACAa1QyAAAAPUlEQVQoFWN0mv3/PwMU7EtlZISx8dFM+CRxyQ1yTYzIAYHLD+ji9PMTC7LV+OIJ2Rv0c96oTdD4oV9AAAB/TQsAYy1MLwAAAABJRU5ErkJggg==",
        "i": "iVBORw0KGgoAAAANSUhEUgAAAAkAAAANCAYAAAB7AEQGAAAAIklEQVQYGWNkQAJOs///h3H3pTIywthMMAY+elQRw2AMAgBW+wQa/q56owAAAABJRU5ErkJggg==",
        "j": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAN0lEQVQoFWNkIBI4zf7/H6aUCcYghR7VBA0tsgKCBTn896UyMhIT9GTZxIhsEzG2gNSQZRNZmgAmfgnRpvfItgAAAABJRU5ErkJggg==",
        "k": "iVBORw0KGgoAAAANSUhEUgAAAAwAAAANCAYAAACdKY9CAAAAaklEQVQoFYWR0Q3AIAhES0frLp2qu3Q1zSW95rhA8EeU94BoXM9ax7feO4Kx7+ROT1RnwsiNgsKj4DBGbjtUcNuhg0vBYUC60kgTDDEJWkljLVQKeA3/RErBgBU7kPnUwWFAfvcLnmBFlzY0ejHPkHfW8AAAAABJRU5ErkJggg==",
        "l": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAL0lEQVQoFWN0mv3/PwMU7EtlZISx8dFM+CRxyY1qgobMIA8IRuQUgSsy0cXp5ycAj5sG9B8JGsEAAAAASUVORK5CYII=",
        "m": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAMElEQVQoFWN0mv3/PwOJgIlE9WDllGval8rICMLItmMTo9wmZBvwsUdtgoYO/QICANPkB4nFxDDlAAAAAElFTkSuQmCC",
        "n": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAL0lEQVQoFWN0mv3/PwOJgIlE9WDlZGliQbZpXyojIzIfmY3sDbJsGtUEDc5BHhAAj7kG91sA1sEAAAAASUVORK5CYII=",
        "o": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAN0lEQVQoFWN0mv3/PwOJgIlE9WDlZGliQbZpXyojIzIfmY3sDbJsGtUEDU5G5KBEDmJ8bPqFHgBMzAnR80GexgAAAABJRU5ErkJggg==",
        "p": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAASCAYAAACAa1QyAAAAQklEQVQoFWN0mv3/PwOJgIlE9WDlZGliQbZpXyojIzIfmY3sDbJsGtUEDU5G5KBEDmJ8bPqFHtEpAtm59HMe/WwCAJ8UCwJWTpYsAAAAAElFTkSuQmCC",
        "q": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAASCAYAAACAa1QyAAAATUlEQVQoFWN0mv3/PwOJgIlE9WDlZGliQbZpXyojIzIfmY3sDbJsGtUEDU5G5KBEDmJ8bPqFHtYUgOxkbKmELOcRtAkWIMg2kmUTWZoAQwMR2VhDl78AAAAASUVORK5CYII=",
        "r": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAALUlEQVQoFWN0mv3/PwOJgIlE9WDlZGliQbZpXyojIzIfF5ssm0Y1QYNzkAcEACCxBBxWW3qwAAAAAElFTkSuQmCC",
        "s": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAANElEQVQoFWN0mv3/PwOJgIlE9WDlZGliQbZpXyojIzIfF5ssmxgHd0AQ5XFQgCB7YzgGBAAHzQyqIIdwIAAAAABJRU5ErkJggg==",
        "t": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAALUlEQVQoFWN0mv3/PwOJgIlE9WDlZGlixGYTspP3pTJiqCHLplFN0KAe5AEBAKu7BvTrMd81AAAAAElFTkSuQmCC",
        "u": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAMUlEQVQoFWN0mv3/PwMU7EtlZISx0WlkdUzoksTwRzVBQ2mQBwQjckwTE7EgNfTzEwDExgnPrPJ4NwAAAABJRU5ErkJggg==",
        "v": "iVBORw0KGgoAAAANSUhEUgAAAAwAAAANCAYAAACdKY9CAAAAd0lEQVQoFYWQAQ6AIAwDGfFl/sVX+Re+htSkpBssLDE09tqhpYy5397xQGdD3ygAtsdsF1CmKqCGvldds1ZCWgLWbQCkgGoW/IHTFsBkLib13DXTd38lA9mO0PINbMpOtwFQ3KLt8JcNEQCkswTUPIUnG681jSE+XwMvgvKD3yEAAAAASUVORK5CYII=",
        "w": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAALUlEQVQoFWN0mv3/PwMU7EtlZAQxCYkxwTSQQo9qgobWIA8IRuTYJzaC6ecnACGvDc/Z7HB/AAAAAElFTkSuQmCC",
        "x": "iVBORw0KGgoAAAANSUhEUgAAAAwAAAANCAYAAACdKY9CAAAAgklEQVQoFZWSiw2AIAxEi6PpKm6lqzgbesRnygVNJMGW3gcaG7XWmLfre8WvDacoiXsdaxTyHJc9Hs70BlDPZNUmd82EnGPQbnARoEfxihpljRzBMO0EAl0EEeH/plG6M3XFjLUbcgGiPwVO9+NGZIhgXQ8qurOf2/xoPJiVt3kCPwGLgnhJFhDySgAAAABJRU5ErkJggg==",
        "y": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAASCAYAAACAa1QyAAAAPklEQVQoFWN0mv3/PwMU7EtlZISx0WlkdUzoksTwRzVBQ2mQBwQjckwTE7EgNfTzE9YEiuxkbImYfs6jn00ArlAN2LER5EoAAAAASUVORK5CYII=",
        "z": "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAT0lEQVQoFWN0mv3/PwOJgIlE9WDlZGliJGQTuvP3pTIy4tWETQPIEpyacGnAqQmfBqyaCGnA0ESMBhRNxGqAa0LXAJLABxhJ1QAyjKwUAQA6fySifLwVygAAAABJRU5ErkJggg=="
    }

    def __init__(self):
        self.check_data = []
        self._initialize_masks()

    def _initialize_masks(self):
        for group in self.PRIORITY_LEVELS:
            for char in group:
                if char in self.MASKS:
                    img = Image.open(io.BytesIO(base64.b64decode(self.MASKS[char])))
                    mask = np.array(img)
                    self.check_data.append((mask, mask.shape[:2], char))

    async def solve(self, image_input, session=None, confidence=0.95):
        try:
            if isinstance(image_input, str) and image_input.startswith("http"):
                if not session: return ""
                async with session.get(image_input) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        captcha_img = Image.open(io.BytesIO(image_data))
                    else: return ""
            else:
                captcha_img = image_input if isinstance(image_input, Image.Image) else Image.open(image_input)

            captcha_img = captcha_img.convert("RGBA")
            large_array = np.array(captcha_img)
            matches = []

            for mask_array, (h, w), char in self.check_data:

                alpha_mask = mask_array[:, :, 3] > 0
                for y in range(large_array.shape[0] - h + 1):
                    for x in range(large_array.shape[1] - w + 1):
                        segment = large_array[y : y + h, x : x + w]

                        if np.array_equal(segment[alpha_mask], mask_array[alpha_mask]):

                            if not any(
                                (m[0] - w < x < m[0] + w) and (m[1] - h < y < m[1] + h)
                                for m in matches
                            ):
                                matches.append((x, y, char))

            matches.sort(key=lambda m: m[0])
            return "".join([m[2] for m in matches])

        except Exception:
            return ""

async def solveHbCaptcha(captcha_url, session):
    solver = NeuraSolver()
    return await solver.solve(captcha_url, session)
