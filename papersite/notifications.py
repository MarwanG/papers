### Notifications
###############################
                  ##################
            ############

from papersite.email import send_mail
from papersite.db import (query_db, get_paper_w_uploader,
                          get_authors, get_comment)
from flask import url_for

## TODO: store notifs in db

## We notify users liked this paper
## It's different from papersite.db.liked_by, caz here we want
## all user props, not only their names
def users_to_notify(paperid):
  return query_db(
    "select u.*                             \
    from likes as l, users as u             \
    where l.userid = u.userid and           \
    l.paperid = ?",
    [paperid])

## Currently, we notify users that liked at least one paper
## from the same uploader
## This behavior will change in the near future:
## user will follow other user, author, etc.
def users_to_notify_about_new_paper(paperid):
  return query_db(
    "select users.*                         \
    from users as users,                    \
         likes as likes,                    \
         papers as papers_by_uploader,      \
         papers as newpapers,               \
         users as uploaders                 \
    where                                   \
         likes.userid = users.userid and    \
         likes.paperid = papers_by_uploader.paperid and \
         papers_by_uploader.userid = uploaders.userid and  \
         uploaders.userid = newpapers.userid   and  \
         newpapers.paperid = ?",
    [paperid])

def review_was_changed(paperid, reviewid):
  template = "Hello %s,\n\n"
  users = users_to_notify(paperid)
  for u in users:
    msg = template % (u['username'],
                        paper['title'],
                        authors,
                        paper['username'],
                        url)
      # todo save message to notifs table
    send_mail(u['email'], msg)


def comment_was_added(paperid, commentid):
  # TODO: transform latex to smth more human readable
  url = url_for('onepaper', paperid=paperid, _external=True)
  url = url + '#comment-' + str(commentid)
  template = "Aloha %s,\n\n\
User %s just commented a paper you liked.\n\
Paper title: %s\n\
Comment:\n\
%s\n\
Url: %s\n\n\
Have a nice day,\n\
Papers' team"
  paper = get_paper_w_uploader(paperid)
  users = users_to_notify(paperid)
  comment = get_comment(commentid)
  print (users)
  for u in users:
    msg = template % (u['username'],
                      comment['username'],
                      paper['title'],
                      comment['comment'],
                      url)
    # todo save message to notifs table
    send_mail(u['email'], msg, 'New comment for paper: %s' % (paper['title']))


def new_paper_was_added(paperid):
  url = url_for('onepaper', paperid=paperid, _external=True)
  paper = get_paper_w_uploader(paperid)
  authors = ", ".join([a['fullname'] for a in get_authors(paperid)])
  template = "Hello %s,\n\n\
a new paper was added to Papersˠ. The paper may interests you.\n\
Title:    %s\n\
Authors:  %s\n\
Uploader: %s\n\
Url: %s\n\n\
Have a good day,\n\
Papers' team"
  users = users_to_notify_about_new_paper(paperid)
  for u in users:
    msg = template % (u['username'],
                      paper['title'],
                      authors,
                      paper['username'],
                      url)
    # todo save message to notifs table
    send_mail(u['email'], msg, 'New paper: %s' % (paper['title']))
