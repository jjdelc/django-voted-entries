# coding: utf-8

from django import template

register = template.Library()

@register.filter
def has_upvote(entry, entries_votes):
    states = ['inactive', 'voted']
    try:
        direction = entries_votes[entry.id]
        return states[direction == 1]
    except KeyError:
        return states[0]

@register.filter
def has_downvote(entry, entries_votes):
    states = ['inactive', 'voted']
    try:
        direction = entries_votes[entry.id]
        return states[direction == -1]
    except KeyError:
        return states[0]
