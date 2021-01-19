# UserChannels

By using this software you agree to the license conditions (MIT LICENSE).

## What it is:

TLDR: Unbannable/Unreportable bots copying posts from private channels to subscribers. 

# How to install:

### PLEASE NOTE PYTHON 3.9 WHICH IS DEFAULT NOWADAYS WILL NOT WORK, thus you have to use conda / docker / pyenv 

1. Create a telegram account, it must have a @username
2. Disable being added to groups / chats, tweak privacy settings
3. Go to my.telegram.org:
4. Login to your Telegram account with the phone number of the developer account to use.
5. Click under API Development tools.
6. A Create new application window will appear. Fill in your application details. There is no need to enter any URL, and only the first two fields (App title and Short name) can currently be changed later.
7. Click on Create application at the end. Remember that your API hash is secret and Telegram won’t let you revoke it. Don’t post it anywhere!
8. Rename .env_example to .env (dotfiles are usually hidden in the file explorer)
9. Paste API_ID and API_HASH right after '=' with no space

Below are listed three types of installation: PyEnv, Docker, and Conda
Use PyEnv if you want to quickly deploy / test. If you have problems with pyenv, try conda.
If you want to deploy it and know about docker, follow the docker install process.

## PyEnv 
10. Install pyenv, follow this tutorial: https://realpython.com/intro-to-pyenv/, below is TLDR:
11. Download pyenv on mac/linux: `curl https://pyenv.run | bash`, do not close the terminal, open your ~/.bashrc or ~/.zshrc in a text editor and paste what the installer tells you at the end.
11. On windows follow this installation: https://github.com/pyenv-win/pyenv-win
12. Close / reopen terminal
13. Install the requirered verion: `pyenv install -v 3.7.9`
14. Activate it while in the folder: `pyenv local 3.7.9`
15. Install deps: `pip install -r requirements.txt`
16. Run the application: `python .`
17. To run in background: 'python . &'

## Docker (WIP might not work yet) (Use this for serious deployment)
Attention: you have to be signed in to telegram in order to use docker. Run the application without docker first (i.e. with pyenv), it will ask you for credentials and create a .session file. After the file is created, you are good to go. 

10. Install docker, (Optionally reboot):
```
# ubuntu 
sudo apt-get install docker
# arch / manjaro
sudo pacman -S docker
# search for your own os:
https://docs.docker.com/get-docker/
```

11. Go to this folder in terminal (either 'open here' or use cd command)
12. Run the following: 
```
# build
docker build --tag userchannel:1.0 .
# run
docker run --publish 8080:8080 --detach --name bot userchannel:1.0
# see your container status/id
docker ps -a
# when you are done
docker kill {your-container-id}
```
13. (Optional) If you get this:
```
Got permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock:....
``` 
 Run:
```
sudo groupadd docker
sudo usermod -aG docker ${USER}
```
 Now reboot


## Conda (if you have it installed / like it)
10. Install anaconda from here (even on linux, download .sh): https://www.anaconda.com/products/individual
10. On mac/linux: `chmod 777 ~/Downloads/Anaconda.sh && ./Anaconda.sh`, note file name might differ
10. Create a conda environment: ` conda create -n userchan python=3.6 `
12. Cd to current directory
12. Install deps: `pip install -r requirements.txt`
13. Start the app: `python .`

# How to use:
1. Create a private channel, add your based admins and people who you trust
2. By default, the bot forwards everything from any channel it is subbed to. You can change .
the channel name with the `CHANNEL_NAME` in `.env` file.
Then it will forward from this specific channel
3. Add one or many bots to the channel, make them admins so they can send you notifications
4. Configure them inside the group, use /help command for starters
5. Start shitposting, the bots will forward all your posts. You can sub yourself to see
6. Use `/help` command while in the channel. It will not be broadcasted to the users.
Bot messages are also not broadcasted.

# Setting up multiple instances
1. Clone it multiple times
2. Ensure there are no overlapping logins
3. Go to each folder
4. Start the bot in background: `python . &`
5. In channel type `/mute @bot_user_name` for all the bots EXCEPT ONE. 
Only one bot should be unmuted, it will log verbose.

# Troubleshooting / FAQ

1. 
```
File "/home/.../python3.6/site-packages/telethon/sessions/sqlite.py", line 194, in _update_session_table
    c.execute('delete from sessions')
sqlite3.OperationalError: database is locked
```
There is another instance running somewhere, kill it or reboot the pc