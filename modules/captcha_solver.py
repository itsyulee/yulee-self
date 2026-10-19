# This file is part of YuleeSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# YuleeSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with YuleeSelf-UwU. If not, see <https://www.gnu.org/licenses/>.


"""
Author: Routo
YuleeSelf-UwU - https://github.com/itsyulee/yulee-self
"""



import os
import io
import asyncio
import threading
import aiohttp
import numpy as np
from PIL import Image

try:
    import onnxruntime
except ImportError:
    onnxruntime = None


# Credit to Owo-Dusk for onnxmodel https://github.com/owo-dusk/owo-dusk/blob/main/utils/captcha_solver/best.onnx

# Process-local cache: workers never share customer configuration or API keys.
_MODEL_SESSIONS = {}
_MODEL_LOCK = threading.Lock()


class CaptchaSolver:
    """
    uses local onnx models to solve 'letterword' security captchas.
    """
    def __init__(self, bot):
        self.bot = bot
        self.model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "best.onnx")
        self.onnx_session = None
        self.classes = "abcdefghijklmnopqrstuvwxyz"
        self.conf_threshold = 0.3
        self.img_size = 384
        
        if onnxruntime is None:
            self.bot.log("SYS", "onnxruntime not installed. AI Solver disabled.")

    def _load_model(self):
        if self.onnx_session is not None or onnxruntime is None:
            return
        if not os.path.exists(self.model_path):
            self.bot.log("ERROR", f"AI Model not found at {self.model_path}")
            return

        try:
            model_path = os.path.realpath(self.model_path)
            with _MODEL_LOCK:
                session = _MODEL_SESSIONS.get(model_path)
                if session is None:
                    session = onnxruntime.InferenceSession(
                        model_path,
                        providers=["CPUExecutionProvider"]
                    )
                    _MODEL_SESSIONS[model_path] = session
                self.onnx_session = session
            self.bot.log("SYS", "AI Captcha Solver initialized.")
        except Exception as e:
            self.bot.log("ERROR", f"Failed to load AI model: {e}")

    def _letterbox(self, img_array, new_size=384, color=(114, 114, 114)):
        """resize image with padding to maintain aspect ratio."""
        img = Image.fromarray(img_array)
        w, h = img.size
        scale = min(new_size / w, new_size / h)
        nw, nh = int(w * scale), int(h * scale)
        img_resized = img.resize((nw, nh), Image.Resampling.BILINEAR)
        
        new_img = Image.new("RGB", (new_size, new_size), color)
        paste_x = (new_size - nw) // 2
        paste_y = (new_size - nh) // 2
        new_img.paste(img_resized, (paste_x, paste_y))
        
        return np.array(new_img)

    async def solve_image(self, url, letter_count=5):
        """
        downloads a captcha image from a url and predicts the letters.
        """
        if self.onnx_session is None:
            self._load_model()
        if self.onnx_session is None:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.read()
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    img_array = np.array(img)
        except Exception as e:
            self.bot.log("ERROR", f"Failed to download captcha image: {e}")
            return None

        return self.predict_image(img_array, letter_count)

    def predict_image(self, img_array, letter_count=5):
        """Predict an RGB image array using the same pipeline as URL challenges."""
        if not 1 <= letter_count <= 26:
            raise ValueError("letter_count must be between 1 and 26")
        if self.onnx_session is None:
            self._load_model()
        if self.onnx_session is None:
            return None

        img = self._letterbox(img_array, self.img_size)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1)) 
        img = np.expand_dims(img, axis=0) 

        input_name = self.onnx_session.get_inputs()[0].name
        outputs = self.onnx_session.run(None, {input_name: img})[0]
        detections_raw = outputs[0]

        detections = []
        for det in detections_raw:
            x1, y1, x2, y2, conf, cls_id = det
            if conf < self.conf_threshold:
                continue
            
            detections.append({
                "char": self.classes[int(cls_id)],
                "conf": float(conf),
                "cx": float((x1 + x2) / 2)
            })

        if len(detections) > letter_count:
            detections.sort(key=lambda d: d["conf"], reverse=True)
            detections = detections[:letter_count]
        detections.sort(key=lambda d: d["cx"])
        
        result = "".join(d["char"] for d in detections)
        if len(result) != letter_count:
            self.bot.log("ERROR", f"AI detected {len(result)} letters; expected {letter_count}.")
            return None
        self.bot.log("SECURITY", f"AI Solver Predicted: {result}")
        return result

def setup_solver(bot):
    return CaptchaSolver(bot)
