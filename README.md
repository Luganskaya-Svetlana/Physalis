# Physalis
Django-powered website https://phys.pro (Russian language) with a unique
selection of physics problems, structured in accordance with the Russian
Unified State Exam (EGE).

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
For loading data to a new db do:
```bash
cd physalisproject
python3 manage.py makemigrations
python3 manage.py migrate
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
In settings.py there are default values of SECRET_KEY, DEBUG and ALLOWED_HOSTS,
so you can just run the project. But if you want to change the default values,
create .env file, copy text from env.example, paste it to .env and make desired
changes.

## Developement and production
For developement, set
```
DEBUG = True
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'), ]
```
in `settings.py`.

For production, configure your web-server and set
```
DEBUG = False
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
```
Otherwise static files such as css sheets won't be served properly.


## Features
- [x] Add problems to the database from the admin panel (obligatory parameters:
  text, number; optional parameters: solution, answer category, tag,
  difficulty)
- [x] Generate two pages (exam sheet and answers) via admin panel by listing
  ids of selected problems. Different styling for full and incomplete exam
  according to the structure of Unified State Exam in Russia (ЕГЭ)
- [x] Upload images (including .svg) to problems
- [x] Filter problems by topic, difficulty, category, difficulty etc.
- [x] Pagination for 40+ elements in list
- [x] Client-side MathJax rendering of math (currently not used)
- [x] Server-side math rendering with
  [ziamath](https://github.com/cdelker/ziamath)
- [x] Use custom latex preamble to shorten latex formulae typing, see
  [ziamath_filter.py](https://github.com/Luganskaya-Svetlana/Physalis/blob/master/physalisproject/problems/templatetags/ziamath_filter.py)
- [x] Cache pages containing a lot of math (problems_list, types,
  variant_detail, variant_answer, tags) to reduce database requests and
  processing time
- [x] Adjust CSS styles for print: good-loking pdf saved with the standard
  system print dialog
- [x] Generate sitemap.xml
- [ ] If the topic (раздел) is selected, show only appropritate subtopics
  (подразделы) in the list (both in admin panel and for filters on /problems,
  /types, /tags).
- [ ] «Drafts» for problems and variants (problem/variant is saved and can be
  edited and published but is not shown)
- [ ] Let users report typos (show page url)
- [ ] Inform registered users that typo reports have been processed
- [ ] Copy problem/variant (useful when need to make similar problem/variant
  with a few changes)
- [ ] Generate pdf automatically when generating exam sheets
- [ ] Case-insensitive inexact search
- [ ] Add website logo to the svg file while uploading
- [ ] Trim the whitespace from the svg files while uploading
- [ ] Convert png to svg while uploading
- [ ] Use latex to generate PDF out of selected problems or full variant (pdf
  saved from the standard system print dialog is OK, css styles are adjusted
  for print)
- [ ] User registration and user-generated content: generate pdf of selected
  problems etc.
- [ ] Store statistics for a user
- [ ] Pass exam online and get a mark
- [ ] Generate exam sheet on user request (e.g., full exam with chosen difficulty)
