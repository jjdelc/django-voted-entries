# coding: utf-8

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.utils.decorators import classonlymethod
from django.views.generic.list import MultipleObjectMixin
from django.http import HttpResponseBadRequest, HttpResponseRedirect

try:
    from notification import models as notification
except ImportError:
    notification = None

from voted_comments.forms import voted_entry_form_factory

class BaseVotedEntryListView(MultipleObjectMixin, TemplateView):
    voted_entry_class = None
    voted_entry_comment_class = None
    voted_entry_vote_class = None
    voted_entry_form_class = None
    voted_entry_vote_form_class = None
    voted_entry_comment_form_class = None

    voted_entry_url_pattern = 'voted_entry_id'
    RELATED_ENTRY_FK = None

    ADD_VOTED_ENTRY_SUCCESS_MSG = ''
    THANKS_FOR_VOTING = ''
    CONSIDER_LEAVING_MESSAGE = ''
    UNSUBSCRIBED_MSG = ''
    NEW_REVIEW_COMMENT = ''

    UP_VOTE_NOTIFICATION_TYPE = ''
    DOWN_VOTE_NOTIFICATION_TYPE = ''
    COMMENT_NOTIFICATION_TYPE = ''
    COMMENT_OWNER_NOTIFICATION_TYPE = ''
    VOTED_ENTRY_NEW_COMMENT_NOTIFICATION = ''

    ACTIONS = {
        'add': '_add_voted_entry',
        'vote': '_voted_entry_vote',
        'comment': '_voted_entry_comment',
        'unsubscribe': '_unsubscribe_user',
    }

    @classonlymethod
    def as_view(cls, **initkwargs):
        # Set related form classes
        (_voted_entry_form_class, _voted_entry_vote_form_class,
        _voted_entry_comment_form_class) = voted_entry_form_factory(
        cls.voted_entry_class, cls.voted_entry_vote_class,
        cls.voted_entry_comment_class
        )

        if not cls.voted_entry_form_class:
            cls.voted_entry_form_class = _voted_entry_form_class

        if not cls.voted_entry_vote_form_class:
            cls.voted_entry_vote_form_class = _voted_entry_vote_form_class

        if not cls.voted_entry_comment_form_class:
            cls.voted_entry_comment_form_class = _voted_entry_comment_form_class
        
        return super(BaseVotedEntryListView, cls).as_view(**initkwargs)
        

    def _unsubscribe_user(self, request, *args, **kwargs):
        self.voted_entry.subscribed_users.remove(request.user)
        messages.success(request, self.UNSUBSCRIBED_MSG)
        return HttpResponseRedirect(self.voted_entry.get_absolute_url()
            + self.get_entry_hash(self.voted_entry))

    def get_entry_hash(self, voted_entry):
        return '#' + voted_entry.id

    def _voted_entry_comment(self, request, *args, **kwargs):
        form = self.voted_entry_comment_form_class(self.voted_entry, 
            request.user, data=request.POST)

        if form.is_valid():
            comment = form.save()
            messages.success(request, self.NEW_REVIEW_COMMENT)

            # Notify subscribed users
            if notification:
                notification.send([cuser 
                    for cuser in self.voted_entry.subscribed_users.all() 
                    if cuser not in (request.user, self.voted_entry.user)],
                    self.COMMENT_NOTIFICATION_TYPE, {
                        'voted_entry': self.voted_entry,
                        'comment': comment,
                    })

                # Notify sugestion owner in case she isn't the one commenting
                if request.user != self.voted_entry.user:
                    notification.send([self.voted_entry.user],
                        self.VOTED_ENTRY_NEW_COMMENT_NOTIFICATION, {
                            'voted_entry': self.voted_entry,
                            'comment': comment,
                        })

                self._send_comment_extra_notification(request, comment)

            # Subscribe the commenteer, if already subscribed nothing should 
            # happen 
            self.voted_entry.subscribed_users.add(request.user)

            return HttpResponseRedirect(self.voted_entry.get_absolute_url()
                + self.get_entry_hash(self.voted_entry))

        context = self.get_context_data(comment_form=form)
        return self.render_to_response(context)

    def _voted_entry_vote(self, request, *args, **kwargs):
        form = self.voted_entry_vote_form_class(self.voted_entry, request.user,
            data=request.POST)
        if form.is_valid():
            vote = form.save()
            messages.success(request, self.THANKS_FOR_VOTING)
            notification_type = self.UP_VOTE_NOTIFICATION_TYPE
            if vote.direction == self.voted_entry_vote_class.DOWN_VOTE:
                messages.info(request, self.CONSIDER_LEAVING_MESSAGE)
                notification_type = self.DOWN_VOTE_NOTIFICATION_TYPE

            if notification and vote.user != self.voted_entry.user:
                notification.send([self.voted_entry.user], notification_type, {
                    'vote': vote,
                    'voted_entry': self.voted_entry,
                })

            # Subscribe the voter, if already subscribed nothing should 
            # happen 
            self.voted_entry.subscribed_users.add(request.user)

            return HttpResponseRedirect(self.voted_entry.get_absolute_url()
                + self.get_entry_hash(self.voted_entry))

        context = self.get_context_data(vote_form=form)
        return self.render_to_response(context)

    def _notify_on_add(self, request):
        pass

    def _send_comment_extra_notification(self, request):
        pass

    def _add_voted_entry(self, request, *args, **kwargs):
        form = self.voted_entry_form_class(request.user, data=request.POST, 
            instance=self.voted_entry)
        if form.is_valid():
            kwargs = {}
            if self.RELATED_ENTRY_FK:
                kwargs = {
                    self.RELATED_ENTRY_FK: self.get_object()
                }

            voted_entry = form.save(**kwargs)
            self.voted_entry = voted_entry
            messages.success(request, self.ADD_VOTED_ENTRY_SUCCESS_MSG)
            self._notify_on_add(request)

            return HttpResponseRedirect(voted_entry.get_absolute_url()
                + self.get_entry_hash(self.voted_entry))

        context = self.get_context_data(entry_form=form)
        return self.render_to_response(context)


    def get_voted_entry(self):
        voted_entry = None
        if not hasattr(self, '_ve') and 'voted_entry_id' in self.request.POST:
            voted_entry = get_object_or_404(self.voted_entry_class,
                pk=self.request.POST[self.voted_entry_url_pattern])
            setattr(self, '_ve', voted_entry)
        elif 'voted_entry_id' not in self.request.POST:
            voted_entry = None
            setattr(self, '_ve', voted_entry)

        self.voted_entry = self._ve
        return self._ve
        

    def post(self, request, *args, **kwargs):
        if request.user.is_anonymous():
            return HttpResponseBadRequest()

        self.voted_entry = self.get_voted_entry()
        try:
            action_name = request.POST['action']
            view = getattr(self, self.ACTIONS[action_name])
            return view(request, *args, **kwargs)
        except KeyError:
            # Must have defined an action
            return HttpResponseBadRequest()

    def get_subscribed_entries(self, user):
        return getattr(user, '%(class)s_subscriptions' % {
            'class': self.voted_entry_class.__name__.lower(),
        }).values_list('pk', flat=True)

    def get_context_data(self, **kwargs):
        user = self.request.user
        if user.is_anonymous():
            kwargs.update({
                'entry_form': None,
                'entries_votes': {},
            })
            return super(BaseVotedEntryListView, self).get_context_data(
                **kwargs)

        if 'entry_form' not in kwargs:
            kwargs['entry_form'] = self.voted_entry_form_class(user)

        kwargs['entries_votes'] = dict([t 
            for t in self.get_queryset().filter(votes__user=user).values_list(
                'pk', 'votes__direction') if t[1] is not None])

        # A user is subscribed to those entries where he has either
        # voted or commented
        kwargs['subscribed_entries'] = self.get_subscribed_entries(user)
        
        return super(BaseVotedEntryListView, self).get_context_data(**kwargs)

