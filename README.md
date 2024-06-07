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
Note: 'variant' means 'exam sheet' or just some list of problems.

- [x] Add problems to the database from the admin panel (mandatory parameters:
  text, number; optional parameters: solution, answer category, tag,
  difficulty)
- [x] Process text with markdown.
- [x] Generate two pages (variant and answers) via admin panel by listing
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
- [x] Add 'similar problems' field to admin panel
- [x] Add 'notes' field to admin panel for problems (not displayed on the site)
- [ ] In /variants/ add types ДВИ and ЕГЭ (show only ДВИ or ЕГЭ...)
- [ ] In /variants/ change 'Неизвестно' to '-------'
- [ ] Decide on 'difficulty' in /variants/.
  Full exam always has significantly lower 'difficulty' than its second part.
  Perhaps, calculate difficulty only for the 'second part' in a full exam sheet.
- [ ] Upload files up to 30 MB (now limit is ~5 MB)
- [ ] Add 'notes' field to admin panel for `flatpages`.
- [ ] Option to generate pdf when creating a 'variant'.
- [ ] Case-insensitive inexact search (possibly need to move db to Postgre)
- [ ] Rewrite 'similar problems' implementation using 'variants', allow user to
  see the list with all 'similar problems'
- [ ] Search id range (example: 1, 4, 8-13, 20-26). Important: users will be able to
  generate their own variants. Allow to generate page with solutions for chosen
  ids (probably need to limit number of problems up to 50 or so).
- [ ] Add *optional* caching for 'flatpages'.
  Set in admin panel whether to cache the page.
  Set time to store the cache in admin panel.
- [ ] Add field 'original number' in admin panel for problems. Use case: check
  whether the problem has already been added to the database. Warn user when he
  is trying to create a problem with the same 'source' and 'original_number'.
- [ ] Add search in solution and answer; in flatpages (for admin only).
- [ ] Remove 'edit' buttun from /tags/
- [ ] /problems/last/ redirects to the last problem
- [ ] https://phys.pro/problems/?page=last redirects to the last page
- [ ] Make inactive other fields when **id** is selected
- [ ] Change automatically variant complexity in /variants/ when complexity
  of a problem in the variant changes
- [ ] Pagination: show `1 2 3 ... n-1 n-2 n n+1 n+2 ... last-2 las -1 last`,
  where n stands for current page number
- [ ] Show second pager `choose page` (выберите страницу) in list only when there is
  more than 10 elements.
- [ ] In problem_detail link to next/previous problem doesn't appear if there 
  is no problem with id+1/id-1. (E.g. 750, 752).
- [ ] Check if the 'variant' is a full variant in `variants/admin.py`:
  change manual setting `NUMBER_OF_PROBLEMS = 26` to automatic (how?
  last type from `Second part`, ignoring next part
  `not in EGE of current year`).
  Same for descriptions in `templates/variants/variant_detail.html.`
- [ ] When total amount of types changes (happens nearly yearly), keep the
  order in old-structured variants unhanged.
- [ ] Don't allow to create two types with the same number
- [ ] Add field 'similar problems' in admin panel when adding a problem
- [ ] At /admin/problems/typeinege/ show max_score (and possibly id)
- [ ] Calculate 'variant' difficulty as (average_test+average_2_part)/2 to increase
  significance of the second part
- [ ] Add `<title>` tags for types
- [ ] Add checkbox "show max points" when adding a set of problems (useful when
  adding a non-EGE set such as olympiad etc.)
- [ ] Sort types in list when add problem (alphabetically or latest used?)
- [ ] Show which id is to assign to the problem when add it but haven't published
- [ ] When adding a problem, add button «add a plot to problem text» to paste
  `<img class='right mw150' src=/media/(future problem id)t.svg width=30%>`
- [ ] When adding a problem, add button «add solution» to paste
  `<img src=/media/(future problem id).svg width=100%>`
  (or possibly make it default value of the solution field)
- [ ] Update to the latest version of Django (4.2.3+ instead of 3.2.4).
- [ ] Update ziamath (including ziafont and latex2mathml, unreleased versions from git?)
- [ ] If the topic (раздел) is selected, show only appropritate subtopics
  (подразделы) in the list (both in admin panel and for filters on /problems,
  /types, /tags).
- [ ] «Drafts» for problems and variants (problem/variant is saved and can be
  edited and published but is not shown)
- [ ] Show only meaningful values in url when filter is applied (e.g.
  /problems/?&source=2 instead of
  /problems/?id=&text=&category=&subcategory=&source=2&part_ege=&complexity_min=&complexity_max=)
- [ ] Add groups for sources (join EGE-2013, EGE-2014, ... etc. in one group
  «EGE» + option to select year).
- [ ] Let users report typos (show page url)
- [ ] Inform registered users when typo reports have been processed
- [ ] Select id range when searching by id (i.e. 27, 30-36, 44, 88 returns selected
  problems). May be used as an easy way for users to generate and share variants.
- [ ] Copy problem/variant (useful when need to make similar problem/variant
  with a few changes). Perhaps, add a field "copy details from previous id / id=..."
- [ ] Add website logo to the svg file while uploading
- [ ] Trim the whitespace from the svg files while uploading
- [ ] Convert png to svg while uploading
- [ ] Use latex to generate PDF out of selected problems or full variant (pdf
  saved from the standard system print dialog is OK, css styles are adjusted
  for print)
- [ ] .print-new-page (PART 2) start from even page only when print
  two pages on sheet
- [ ] /variants/ order newest first by default
- [ ] User registration and user-generated content: generate pdf of selected
  problems etc.
- [ ] Store statistics for a user
- [ ] Pass the exam online and get points (note: answers 124 and 214 are both correct for
  types 10 etc)
- [ ] Generate 'variant' on user request (e.g., complete 'variant' with chosen difficulty)
- [ ] Upload several svg images at the same time (instead of one at a time)
- [ ] Add vim-like behavior to admin panel
- [ ] In admin panel show number of corresponding problems next to
  category/subcategory/tag
- [ ] For category change page in admin panel shows connected subcategories
- [ ] Don't allow to create (sub)category if name and/or slug already
  exists
- [ ] In /problems/ order categories in a list as follows:
  Mechanics → Heat → Electromagnetism → Optics → Quantum mechanics → Methods
- [ ] Generate Categories + subcategories tree for admin panel and on the site
