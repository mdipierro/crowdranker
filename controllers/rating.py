# coding: utf8

import util
import ranker
import gluon.contrib.simplejson as simplejson

@auth.requires_login()
def accept_review():
    """Asks a user whether the user is willing to accept a rating task for a contest,
    and if so, picks a task and adds it to the set of tasks for the user."""
    # Checks the permissions.
    c = db.contest(request.args[0]) or redirect('default', 'index')
    props = db(db.user_properties.email == auth.user.email).select(db.user_properties.contests_can_rate).first()
    if props == None:
        redirect('closed', args=['permission'])
    c_can_rate = util.get_list(props.contests_can_rate)
    if not (c.rate_constraint == None or c.id in c_can_rate):
        redirect('closed', args=['permission'])
    t = datetime.utcnow()
    if not (c.is_active and c.rate_open_date <= t and c.rate_close_date >= t):
        redirect('closed', args=['deadline'])
    # The user can rate the contest.
    contest_form = SQLFORM(db.contest, record=c, readonly=True)
    # Gets any previous ratings for the contest.
    confirmation_form = FORM.confirm(T('Accept'),
        {T('Decline'): URL('default', 'index')})
    if confirmation_form.accepted:
        # Reads the most recent ratings given by the user.
        # TODO(luca): we should really poll the rating system for this; that's what
        # should keep track of these things.
        previous_ratings = db((db.comparison.author == auth.user_id) 
            & (db.comparison.contest_id == c.id)).select(orderby=~db.comparison.date).first()
        if previous_ratings == None:
            old_items = []
            new_item = ranker.get_item(db, c.id, auth.user_id, [])
        else:
            old_items = util.get_list(previous_ratings.ratings)
            new_item = ranker.get_item(db, c.id, auth.user_id, old_items)
        # Creates a reviewing task.
        db.task.insert(submission_id = new_item, contest_id = c.id)
        db.commit()
        session.flash = T('A review has been added to your review assignments.')
        redirect(URL('task_index', args=[new_item]))
    return dict(contest_form=contest_form, confirmation_form=confirmation_form)

            
def closed():
    if args[0] == 'deadline':
        msg = T('The rating deadline has passed.')
    else:
        msg = T('You do not have permission to rate submissions to this contest.')
    return dict(msg=msg)


@auth.requires_login()
def task_index():
    if not request.args(0):
        redirect(URL('default', 'index'))
    mode = request.args(0)
    if mode == 'completed':
        q = ((db.task.user_id == auth.user_id) & (db.task.completed_date < datetime.utcnow()))
    elif mode == 'all':
        q = (db.task.user_id == auth.user_id)
    elif mode == 'open':
        q = ((db.task.user_id == auth.user_id) & (db.task.completed_date > datetime.utcnow()))
    else:
        # The mode if a specific item.
        q = (db.task.id == mode)
    grid = SQLFORM.grid(q,
        args=request.args[:1],
        field_id=db.task.id,
        create=False, editable=False, deletable=False, csv=False,
        links=[
            dict(header='Contest', 
                body = lambda r: A(T('Contest'), _href=URL('contests', 'view_contest', args=[r.contest_id]))),
            dict(header='Submission', 
                body = lambda r: A(T('view'), _href=URL('submission', 'view_submission', args=[r.id]))),
            dict(header='Review', body = review_link),],
        )
    return dict(grid=grid)

       
def review_link(r):
    if r.completed_date > datetime.utcnow():
        return A(T('Enter review'), _href=URL('review', args=[r.id]))
    else:
        # TODO(luca): Allow resubmitting a review.
        return T('Completed on ') + str(r.completed_date)


@auth.requires_login()        
def review():
    """Enters the review, and comparisons, for a particular task."""
    t = db.task(request.args(0)) or redirect(URL('default', 'index'))
    if t.user_id != auth.user_id:
        redirect(URL('default', 'index'))
    # Ok, the task belongs to the user. 
    # Gets the last reviewing task done for the same contest.
    last_comparison = db((db.comparison.author == auth.user_id)
        & (db.comparison.contest_id == t.contest_id)).select(orderby=~db.comparison.date).first()
    if last_comparison == None:
        last_ordering = []
    else:
        last_ordering = util.get_list(last_comparison.ordering)
    # Reads any comments previously given by the user on this submission.
    previous_comments = db((db.comment.author == auth.user_id) 
        & (db.comment.submission_id == t.submission_id)).select(orderby=~db.comment.date).first()
    if previous_comments == None:
        previous_comment_text = ''
    else:
        previous_comment_text = previous_comments.content
    # TODO(luca): fix this code.
    form = SQLFORM.factory(
        Field('comments', 'text', default=previous_comment_text),
        hidden=dict(order=simplejson.dumps(last_ordering))
        )
    if form.process(onvalidate=decode_order_json).accepted:
        # Creates a new comparison in the db.
        comparison_id = db.comparison.insert(
            contest_id = t.contest_id,
            feature_it = form.vars.feature_it,
            ordering = form.vars.order)
        # Marks the task as done.
        t.update_record(completed_date=datetime.utcnow())
        # Adds the comment to the comments for the submission, over-writing any previous
        # comments.
        if previous_comments == None:
            db.comment.insert(submission_id = t.submission_id,
                content = form.vars.comments)
        else:
            previous_comments.update_record(content = form.vars.comments)
        # TODO(luca): put it in a queue of things that need processing.
        # All updates done.
        db.commit()
        redirect(URL('task_index', args=['open']))
    return dict(form=form, task=t)
        
        
def decode_order_json(form):
    try:
        decoded_order = simplejson.loads(form.vars.order)
        form.vars.order = decoded_order
    except ValueError:
        form.errors.order = T('Error in the received ranking')
        form.vars.order = []
