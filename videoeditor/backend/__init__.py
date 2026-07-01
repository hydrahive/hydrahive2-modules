from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
