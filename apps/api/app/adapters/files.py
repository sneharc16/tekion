"""Server-owned binary storage; replace this boundary for object storage."""

from pathlib import Path
import re


class LocalImageStore:
    def __init__(self, root="data/uploads"):
        self.root = Path(root)

    def path(self, id):
        if not re.fullmatch(r"[a-f0-9]{64}", id):
            raise ValueError("Invalid attachment identity")
        return self.root / (id + ".jpg")

    def save(self, id, image):
        self.root.mkdir(parents=True, exist_ok=True)
        image.save(self.path(id), format="JPEG")


images = LocalImageStore()
