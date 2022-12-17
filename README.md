# Physalis
Django-powered website with modern database of physical problems. 

### Install the project
```bash 
git clone https://github.com/Luganskaya-Svetlana/Physalis
```

### Create a virtual environment
Linux / MacOS

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows

```bash
python -m venv venv
venv\Scripts\activate
```


### Install required libraries
```bash
pip install -r requirements.txt
```

### Run the project 
```bash
cd physalisproject
py manage.py runserver
```

### Configure .env
Confidential information is stored in the .env file.
In settings.py there are default values of SECRET_KEY, DEBUG and ALLOWED_HOSTS, so you can just run the project. But if you want to change default values, create .env file, copy text from env.example, paste it to .env and make desired changes.