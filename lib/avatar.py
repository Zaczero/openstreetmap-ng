from io import BytesIO
from typing import Any

from anyio import Path
from PIL import Image

from lib.exceptions import raise_for
from limits import AVATAR_MAX_FILE_SIZE, AVATAR_MAX_MEGAPIXELS, AVATAR_MAX_RATIO
from models.user_avatar_type import UserAvatarType


class Avatar:
    @staticmethod
    def get_url(avatar_type: UserAvatarType, avatar_id: Any) -> str:
        """
        Get the url of the avatar image.
        """

        if avatar_type == UserAvatarType.default:
            return '/static/img/avatar.webp'
        elif avatar_type == UserAvatarType.gravatar:
            return f'/api/web/avatar/gravatar/{avatar_id}'
        elif avatar_type == UserAvatarType.custom:
            return f'/api/web/avatar/custom/{avatar_id}'
        else:
            raise NotImplementedError(f'Unsupported avatar type: {avatar_type!r}')

    @staticmethod
    async def get_default_image() -> bytes:
        """
        Get the default avatar image.
        """

        return await Path('static/img/avatar.webp').read_bytes()

    @staticmethod
    def normalize_image(data: bytes) -> bytes:
        """
        Normalize the avatar image.

        - Shape ratio: crop
        - Megapixels: downscale
        - File size: reduce quality
        """

        img = Image.open(BytesIO(data))

        # normalize shape ratio
        ratio = img.width / img.height
        if ratio > AVATAR_MAX_RATIO:
            width = int(img.height * AVATAR_MAX_RATIO)
            img = img.crop(((img.width - width) // 2, 0, (img.width + width) // 2, img.height))
        elif ratio < 1 / AVATAR_MAX_RATIO:
            height = int(img.width / AVATAR_MAX_RATIO)
            img = img.crop((0, (img.height - height) // 2, img.width, (img.height + height) // 2))

        # normalize megapixels
        mp_ratio = (img.width * img.height) / AVATAR_MAX_MEGAPIXELS
        if mp_ratio > 1:
            img.thumbnail((img.width // mp_ratio, img.height // mp_ratio))

        # normalize file size
        with BytesIO() as buffer:
            for quality in (95, 90, 80, 70, 60, 50):
                buffer.seek(0)
                buffer.truncate()

                img.save(buffer, format='WEBP', quality=quality)

                if buffer.tell() <= AVATAR_MAX_FILE_SIZE:
                    return buffer.getvalue()

        raise_for().avatar_too_big()
