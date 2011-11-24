# coding: utf-8

from django.db import models
from django.contrib.auth.models import User

from django_extensions.db.fields import (CreationDateTimeField,
    ModificationDateTimeField)

class BaseVotedEntry(models.Model):
    """
    Subclass and add extra attributes, each of these represent a votable
    entry.
    Ideally your subclass will have a FK to a grouper model (ie. Question)
    where all the child voted entries represent possible answers
    """
    class Meta:
        abstract = True
    
    created_at = CreationDateTimeField()
    modified_at = ModificationDateTimeField()
    user_updated = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)
    
    up_votes = models.PositiveIntegerField(default=0)
    down_votes = models.PositiveIntegerField(default=0)
    result_votes = models.IntegerField(default=0)

    body = models.TextField()

    subscribed_users = models.ManyToManyField(User, 
        related_name='%(class)s_subscriptions')

    def get_total_votes(self):
        return self.up_votes + self.down_votes

    def get_comments(self):
        return self.comments.all()

    def _calculate(self, commit=True):
        self.up_votes = self.votes.filter(direction=1).count()
        self.down_votes = self.votes.filter(direction=-1).count()
        self.result_votes = self.up_votes - self.down_votes
        if commit:
            self.save()

    def save(self, *args, **kwargs):
        self._calculate(commit=False)
        super(BaseVotedEntry, self).save(*args, **kwargs)


class BaseVotedEntryComment(models.Model):
    """
    Inherit and make sure to add a FK to the VotedEntry subclass named entry
        entry = models.ForeignKey(VotedEntry, related_name='comments')
    """
    class Meta:
        abstract = True

    body = models.TextField()
    created_at = CreationDateTimeField()
    user = models.ForeignKey(User)

    # Must be defined on subclass
    # entry = models.ForeignKey(VotedEntry, related_name='comments')
    
    def get_absolute_url(self):
        return self.entry.get_absolute_url() + '#comment-%s' % self.id


class BaseVotedEntryVote(models.Model):
    """
    Inherit and make sure to add a FK to the VotedEntry subclass named entry
        entry = models.ForeignKey(VotedEntry, related_name='votes')
    """
    class Meta:
        abstract = True
    
    UP_VOTE = 1
    DOWN_VOTE = -1
    VOTE_CHOICES = [
        (UP_VOTE, u'Up vote'),
        (DOWN_VOTE, u'Down vote'),
    ]

    direction = models.SmallIntegerField(choices=VOTE_CHOICES) 
    created_at = CreationDateTimeField()
    user = models.ForeignKey(User)

    def delete(self, *args, **kwargs):
        super(BaseVotedEntryVote, self).delete(*args, **kwargs)
        self.entry._calculate()

    # Must be defined on subclass
    # entry = models.ForeignKey(VotedEntry, related_name='votes')
    
    def get_absolute_url(self):
        return self.entry.get_absolute_url()

