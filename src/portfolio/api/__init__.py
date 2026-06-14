def main() -> None:
    from portfolio.api.app import main as _main

    _main()


def __getattr__(name: str):
    if name == "app":
        from portfolio.api.app import app

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["app", "main"]
