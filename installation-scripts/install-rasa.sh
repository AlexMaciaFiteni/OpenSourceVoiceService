# Install python
sudo apt update
sudo apt install python3-dev python3-pip

# This step is optional, but we strongly recommend isolating
# python projects using virtual environments. Tools like virtualenv
# and virtualenvwrapper provide isolated Python environments, which
# are cleaner than installing packages system-wide (as they prevent
# dependency conflicts). They also let you install packages without
# root privileges.
python3 -m venv ./venv
source ./venv/bin/activate

# Make sure your pip version is up to date
pip3 install -U pip

# Install Rasa
pip3 install rasa

# Install Rasa-X
pip3 install rasa-x --extra-index-url https://pypi.rasa.com/simple
