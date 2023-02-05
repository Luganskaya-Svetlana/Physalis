# Physalis
Django-powered website with modern database of physical problems. 

## Workflow status
![workflow](https://github.com/Luganskaya-Svetlana/Physalis/actions/workflows/python-package.yml/badge.svg)

## Install the project
```bash 
git clone https://github.com/Luganskaya-Svetlana/Physalis
```

## Create a virtual environment
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

## Install required libraries
```bash
pip install -r requirements.txt
```

## Configure DataBase
Committed db is just an example. 
For loading data to a new db use:
```bash
cd physalisproject
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py loaddata problems/fixtures/data.json (it will be later)
```
For creating superuser (to get access to the admin panel) use:
```bash
cd physalisproject
python3 manage.py createsuperuser
```

## Run the project 
```bash
cd physalisproject
python3 manage.py runserver
```

## Configure .env
Confidential information is stored in the .env file.
In settings.py there are default values of SECRET_KEY, DEBUG and ALLOWED_HOSTS, so you can just run the project. But if you want to change default values, create .env file, copy text from env.example, paste it to .env and make desired changes.

## Features
- [x] Add problems to the database from the admin panel (obligatory parameters: text, number;optional parameters: solution, answer category, tag, difficulty).
- [x] Add plots to problems, solutions, answers
- [ ] Add 4 types of test problems (number with measurement units; 2 or 3 out of 5; changing of 2 values (table); graphic/text to text/formulae match).
- [ ] Filter problems by topic, difficulty, category etc.
- [x] Client-side mathjax rendering
- [ ] Server-side mathjax rendering
- [ ] Use custom latex preamble to shorten latex formulae typing
- [ ] Use latex to generate PDF out of selected problems or full variant
- [ ] Return a page with a full variant of desired difficulty. Checkboxes or text fields for test answers and points for each number.
- [ ] Add/update problems from terminal via ssh from text file
