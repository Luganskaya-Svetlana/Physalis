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

## Configure the database
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
- [x] Add problems to the database from the admin panel (obligatory parameters: text, number; optional parameters: solution, answer category, tag, difficulty)
- [x] Generate two pages (exam sheet and answers) via admin panel by listing ids of selected problems. Different styling for full and incomplete exam according to the structure of Unified State Exam in Russia (ЕГЭ)
- [x] Upload images (including .svg) to problems
- [x] Filter problems by topic, difficulty, category, difficulty etc.
- [x] Pagination for 40+ elements in list
- [x] Client-side MathJax rendering of math (currently not used)
- [x] Server-side math rendering with [ziamath](https://github.com/cdelker/ziamath)
- [x] Cache pages containing a lot of math (problems_list, types, variant_detail, variant_answer) to reduce database requests and processing time
- [x] Use custom latex preamble to shorten latex formulae typing, see [ziamath_filter.py](https://github.com/Luganskaya-Svetlana/Physalis/blob/master/physalisproject/problems/templatetags/ziamath_filter.py)
- [x] Adjust CSS styles for print: pdf saved with the standard system print dialog looks OK
- [ ] Generate pdf automatically when generating exam sheets
- [ ] Add website logo to the svg file while uploading
- [ ] Trim the whitespace from the svg file while uploading
- [ ] Use latex to generate PDF out of selected problems or full variant (pdf saved from the standard system print dialog is OK, css styles are adjusted for print)
- [ ] User-generated exam sheets. E.g., return a page with a full exam of a desired difficulty
