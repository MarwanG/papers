### Main list of papers
###############################
                  ##################
            ############
from papersite import app
from papersite.db import (query_db, get_authors, get_domains,
                          get_keywords, get_comments)
from flask import redirect, url_for, render_template, abort
from math import ceil
from papersite.user import get_user_id




def previews(seq):
    """ for a sequence of papers, i.e. 'select * from papers',
        we extract additional info about comments, authors, etc.
        In order to render the list of previews <paper|comments>.
        We use this at main page and also at sites of users
    """
    likes = {}
    liked = {}
    commentsHead = {}
    commentsTail = {}
    for paper in seq:
        likes[paper['paperid']] = query_db(
                         "select count(*) as c                   \
                          from likes                             \
                          where paperid=?",
            [paper['paperid']],
            one=True)['c']

        liked[paper['paperid']] = query_db(
            "select *                        \
            from likes                       \
            where paperid=? and userid=?",
            [paper['paperid'],get_user_id()],
            one=True)


        commentsHead[paper['paperid']] = query_db(
                       "                                         \
                          select                                 \
                          c.commentid, c.comment, c.userid,      \
                                           c.createtime,         \
                          u.username                             \
                          from comments as c, users as u         \
                          where                                  \
                                c.userid = u.userid and          \
                                c.paperid = ?                    \
                          order by c.commentid                   \
                         limit 2                                 \
                       ",
            [paper['paperid']]);

        # construct a list of comments ids
        
        
        ids_in_head=[  str(c['commentid']) for c in 
                   commentsHead[paper['paperid']]]

        good_injection='(' + ','.join(ids_in_head) + ')';
        
        # donot cosider a comments with id from the list head
        # we cannot bind into 'in (?)', therefore we inject!
        commentsTail[paper['paperid']] = query_db(
                "select * from                            \
                  (                                       \
                   select                                 \
                   c.commentid, c.comment, c.userid,      \
                   c.createtime,                          \
                   u.username                             \
                  from comments as c, users as u          \
                  where                                          \
                   c.userid = u.userid and                       \
                   c.commentid not in " + good_injection + " and \
                   c.paperid = ?                                 \
                  order by c.commentid desc                      \
                  limit 2)                                       \
                 order by commentid                              \
                       ",
            [paper['paperid']]);

    return (commentsTail, commentsHead, likes, liked)

@app.route('/all/')
@app.route('/all/page/<int:page>')
def all(page=1):

    count=query_db("select count(*) as c from papers",one=True)['c']
    # how many papers on page?
    onpage = 5
    maxpage = int(ceil(float(count)/onpage))

    seq=query_db("select *                                       \
                    from papers as p                             \
                  order by p.lastcommentat DESC                  \
                  limit ?, ?", [(page-1)*onpage,onpage])

    commentsTail, commentsHead, likes, liked = previews(seq)

    return render_template('main-list.html', seq=seq,
                           commentsTail=commentsTail,
                           commentsHead=commentsHead,
                           likes=likes,liked=liked,
                           maxpage=maxpage, curpage=page,
                           headurl=app.config['APPLICATION_ROOT'] + '/all')


@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    # if user_authenticated():
    #     return "home page (/username + friend's posts) of user under id " + str(get_user_id()),200
    # else:
    #     return redirect(url_for('all'))
    return redirect(url_for('all'))



### Main list of papers liked or uploaded by user
###############################
                  ##################
            ############

@app.route('/<string:username>')
@app.route('/<string:username>/page/<int:page>')
def usersite(username,page=1):
    """ Generate previews of papers uploaded/liked by specified user """
    u=query_db("select * from users where username = ?",
                      [username],one=True)
    if not u: abort(404)
    # count the paper uploaded/liked by this user
    count = query_db("select count(distinct p.paperid) as c        \
                      from papers as p, likes as l                 \
                      where                                        \
                         p.userid = ? or                           \
                         (p.paperid = l.paperid and l.userid = ?)  \
                     ", [u['userid'],u['userid']], one=True)['c']
    # how many papers on page?
    onpage = 3
    maxpage = int(ceil(float(count)/onpage))
    # todo. some papers ... are bad
    seq=query_db("select *, lastcommentat as sorttime             \
                    from papers                                   \
                    where userid = ?                              \
                  union                                           \
                  select p.*, CASE                                \
                              WHEN l.liketime > p.lastcommentat   \
                              THEN l.liketime                     \
                              ELSE p.lastcommentat END as sorttime\
                    from papers as p, likes as l                  \
                    where p.paperid = l.paperid and l.userid = ?  \
                  order by sorttime DESC                          \
                  limit ?, ?", [u['userid'],u['userid'],
                                (page-1)*onpage,onpage])

    commentsTail, commentsHead, likes, liked = previews(seq)

    return render_template('usersite.html', seq=seq,
                           user=u,
                           commentsTail=commentsTail,
                           commentsHead=commentsHead,
                           likes=likes,liked=liked,
                           maxpage=maxpage, curpage=page,
                           headurl=app.config['APPLICATION_ROOT']+'/'+username)
