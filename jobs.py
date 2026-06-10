async def remind_unpaid(app):
    try:
        logger.info("Запуск remind_unpaid")
        unpaid = get_unpaid_players()
        logger.info(f"Неоплатившие: {unpaid}")
        if not unpaid:
            logger.info("Все оплатили — напоминать некому")
            return

        mentions = []
        for player in unpaid:
            username = str(player.get("username", "")).strip()
            if not username:
                continue
            if not username.startswith("@"):
                username = "@" + username
            mentions.append(username)

        if not mentions:
            logger.info("Нет юзернеймов для упоминания")
            return

        text = (
            f"💰 {' '.join(mentions)}\n\n"
            f"Напоминаю об оплате за поле в этом месяце.\n"
            f"Скиньте деньги как можно скорее 🙏"
        )
        await app.bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info(f"Напомнили об оплате: {mentions}")
    except Exception as e:
        logger.error(f"Ошибка при напоминании об оплате: {e}", exc_info=True)
