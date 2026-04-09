savedcmd_crypto_chat_driver.mod := printf '%s\n'   crypto_chat_driver.o | awk '!x[$$0]++ { print("./"$$0) }' > crypto_chat_driver.mod
