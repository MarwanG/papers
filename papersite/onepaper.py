### One paper
###############################
                  ##################
            ############
import os, re
from papersite import app
from papersite.db import (query_db, get_db, get_authors, get_domains,
                          get_keywords, get_comments,
                          get_insert_keyword, get_insert_author,
                          get_insert_domain, liked_by, likes,
                          delete_comment, delete_paper,
                          get_paper_w_uploader
)
from papersite.user import (get_user_id, is_super_admin, is_author_of_paper,
                            is_author_of_comment, user_authenticated, ANONYMOUS)
from werkzeug import secure_filename
from flask import render_template, request, flash, redirect, url_for
from papersite.notifications import (new_paper_was_added,
                                     comment_was_added)

### Frontend stuff
###############################

@app.template_filter('is_internal_pdf')
def is_internal_pdf(link):
    return re.match('^/static/memory/pdfs/(.*)\.pdf$', str(link))

@app.template_filter('can_delete_comment')
def can_delete_comment(commentid):
    ## currently anonymous cannot delete any comments
    userid = get_user_id()
    if (userid == ANONYMOUS):
        return False
    else:
        return is_super_admin(userid) or is_author_of_comment(userid, commentid)

@app.template_filter('can_delete_paper')
def can_delete_paper(paperid):
    ## currently anonymous cannot delete any comments
    userid = get_user_id()
    if (userid == ANONYMOUS):
        return False
    else:
        return is_super_admin(userid) or is_author_of_paper(userid, paperid)


### Delete comments, papers, est
###  Well actually we do not delete them from DB, just mark as deleted
###############################
                  ##################
            ############
@app.route('/delete-comment/<int:commentid>', methods=['GET'])
def delete_comment_with_check(commentid):
    if can_delete_comment(commentid):
        comment = query_db("select * from comments where commentid = ?",
                      [commentid], one=True)
        delete_comment(commentid)
        flash('You successfully removed the comment')
        return redirect(url_for('onepaper',
                                paperid=comment['paperid']))
    else:
        return "<h1>Forbidden</h1>", 403

@app.route('/delete-paper/<int:paperid>', methods=['GET'])
def delete_paper_with_check(paperid):
    if can_delete_paper(paperid):
        pap = query_db("select * from papers where paperid = ?",
                      [paperid], one=True)
        delete_paper(paperid)
        flash('You successfully removed the paper')
        return redirect(url_for('all'))
    else:
        return "<h1>Forbidden</h1>", 403


### Show paper, etc
###############################
                  ##################
            ############


@app.route('/paper/<int:paperid>', methods=['GET'])
@app.route('/paper/<int:paperid>/', methods=['GET'])
@app.route('/paper/<int:paperid>/<string:title>', methods=['GET'])
def onepaper(paperid, title = None):
    paper = get_paper_w_uploader(paperid)
    liked = query_db(
        "select count(*) as c            \
        from likes                       \
        where paperid=? and userid=?",
        [paperid,get_user_id()],
        one=True)['c']
    authors=get_authors(paperid)
    domains=get_domains(paperid)                       
    keywords=get_keywords(paperid)
    comments=get_comments(paperid)
    return render_template('paper/onepaper.html', 
                           entry=paper,
                           comments=comments,
                           authors=authors,
                           domains=domains,
                           keywords=keywords,
                           liked=liked,
                           liked_by=liked_by(paperid))


@app.route('/paper/<int:paperid>/<string:title>/add-comment',
           methods=['POST'])
def add_comment(paperid, title):
    con = get_db()
    error = None
    with con:
        con.execute('insert into comments \
        (comment,userid,paperid) \
        values (?,?,?)',
                        [
                            # here we do not escape, because we will
                            # do it in jinja
                            request.form['comment'],
                            get_user_id(),
                            paperid
                        ])
        con.execute('update papers set lastcommentat=datetime() \
                       where paperid = ?', [paperid])
        if user_authenticated(): 
            flash('You successfully commented the paper')
        else: 
            flash('You anonymously commented the paper')

    last_c_id=query_db("SELECT last_insert_rowid() as lid",
                       one=True)['lid']
    
    # notify user about new comment
    comment_was_added(paperid, last_c_id)
    return redirect(url_for('onepaper',paperid=paperid,
                                    title=title, error=error)
                    + "#comment-"
                    + str(last_c_id))


### Add paper
###############################
                  ##################
            ############


ALLOWED_EXTENSIONS = set(['pdf','PDF'])
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def parse_list(list):
    return map(str.strip, list.rstrip(', ').split(','))


@app.route('/paper/add', methods=['GET','POST'])
def add_paper():
    error = None
    if request.method == 'POST':
        paper_file = request.files['pdf']
        if not paper_file or not allowed_file(paper_file.filename):
            error = 'Please choose a pdf file'
        elif request.form['title'] == "":
            error = 'Please add a title'
        elif request.form['domains'] == "":
            error = 'Please specify at least one domain'
        elif request.form['authors'] == "":
            error = 'Please add some authors'
        elif request.form['keywords'] == "":
            error = 'Please add some keywords'
        else:
            con = get_db()
            # todo: lock db?
            with con:
              con.execute('insert into papers(title,userid)         \
                             values (?,?)',
                             [request.form['title'], get_user_id()])

              paperid = con.execute("SELECT last_insert_rowid() as lid"
                                    ).fetchone()['lid']

              authors_ids = map(get_insert_author,
                                parse_list(request.form['authors']))
              for authorid in authors_ids:
                  con.execute('insert into papers_authors             \
                              (paperid, authorid)                     \
                              values(?,?)',[paperid, authorid])

              domains_ids = map(get_insert_domain,
                               parse_list(request.form['domains']))
              for domainid in domains_ids:
                  con.execute('insert into papers_domains             \
                               (paperid, domainid)                    \
                               values(?,?)',[paperid, domainid])

              keywords_ids = map(get_insert_keyword,
                               parse_list(request.form['keywords']))
              for keywordid in keywords_ids:
                  con.execute('insert into papers_keywords            \
                            (paperid, keywordid)                      \
                            values(?,?)',[paperid, keywordid])

              filename_pdf = str(paperid) + "-" +                       \
                             secure_filename(paper_file.filename)
              ppdf = os.path.join(app.config['UPLOAD_FOLDER'],filename_pdf)
              paper_file.save(ppdf)
              ## this is just a hack.
              ## In order to generate first page
              filename_png = str(paperid) + ".png"
              ppng = os.path.join(app.config['PREVIEW_FOLDER'],filename_png)
              os.system('papersite/gen.sh ' + ppdf +  ' ' + ppng)
              # end of hack

              ## Sometimes authors provide a url to their paper
              ## in this case we don't store a full paper, we use the url instead
              if request.form['url'] != "":
                  os.remove(ppdf)
                  con.execute("update papers set getlink = ?             \
                               where paperid=?",
                              [request.form['url'], paperid])
              else:
                  con.execute("update papers set getlink = ?             \
                               where paperid=?",
                              ['/static/memory/pdfs/'+filename_pdf, paperid])

              ## notify some users by email about this paper
              new_paper_was_added(paperid)
              
              flash('You successfully upload the paper')
              return redirect(url_for('onepaper',
                                    paperid=paperid,
                                    title=request.form['title']))
    return render_template('paper/add.html', 
                           error=error,
                           domains=query_db ("select * from domains"),
                           keywords=query_db ("select * from keywords"),
                           authors=query_db ("select * from authors"))


### Like a paper
###############################
                  ##################
            ############


@app.route('/paper/<int:paperid>/<string:title>/like', methods=['GET'])
def like_paper(paperid,title):
    if not user_authenticated():
        return "<h1>Forbidden (anonymous cannot like)</h1>", 403
    con = get_db()
    with con:
        con.execute('insert into likes (paperid,userid) values (?,?)',
                    [paperid, get_user_id()])
    return str(likes(paperid))

@app.route('/paper/<int:paperid>/<string:title>/unlike', methods=['GET'])
def unlike_paper(paperid,title):
    if not user_authenticated():
        return "<h1>Forbidden (anonymous cannot unlike)</h1>", 403
    con = get_db()
    with con:
        con.execute('delete from likes where \
                     paperid = ? and userid=?',
                    [paperid, get_user_id()])
    return str(likes(paperid))




