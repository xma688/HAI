"""Run a minimal mock avatar command sequence."""

import asyncio

from hai_avatar.avatar.mock_controller import MockAvatarController


async def main() -> None:
    avatar = MockAvatarController()
    await avatar.connect()
    await avatar.set_expression("soft_smile")
    await avatar.trigger_gesture("nod")
    await avatar.start_speaking()
    await avatar.stop_speaking()
    await avatar.reset_to_idle()


if __name__ == "__main__":
    asyncio.run(main())
