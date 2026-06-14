from src.infrastructure.external.telegram.message_builder import TelegramMessageBuilder


def main() -> None:
    builder = TelegramMessageBuilder()
    message = builder.build_welcome_message()
    print(message)


if __name__ == "__main__":
    main()