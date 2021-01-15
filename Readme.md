# How to use:
1. Create a telegram account
2. Disable being added to groups / chats, tweak privacy settings
3. Go to my.telegram.org:
4. Login to your Telegram account with the phone number of the developer account to use.
5. Click under API Development tools.
6. A Create new application window will appear. Fill in your application details. There is no need to enter any URL, and only the first two fields (App title and Short name) can currently be changed later.
7. Click on Create application at the end. Remember that your API hash is secret and Telegram won’t let you revoke it. Don’t post it anywhere!
8. Rename .env_example to .env (dotfiles are usually hidden in the file explorer)
9. Paste API_ID and API_HASH after '='
10. (Optional: create and activate virtual env)
11. Make sure you have recent version of python (python>=3.7)
12. Run!