from papersite.config import appc
from flask import Flask

app = Flask(__name__,
            static_folder='../static',
            template_folder='../templates')
app.config.update(appc)

import papersite.db
import papersite.user
import papersite.main_list_of_papers
import papersite.onepaper
import papersite.catalog
import papersite.pseudostatic

