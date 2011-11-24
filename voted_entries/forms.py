# coding: utf-8

from django import forms

def voted_entry_form_factory(voted_entry_class, voted_entry_vote_class,
    voted_entry_comment_class):

    class VotedEntryForm(forms.ModelForm):
        class Meta:
            model = voted_entry_class
            fields = ['body']

        def __init__(self, user, *args, **kwargs):
            super(VotedEntryForm, self).__init__(*args, **kwargs)
            self.user = user

        def save(self, **kwargs):
            instance = super(VotedEntryForm, self).save(commit=False)
            instance.user = self.user
            if kwargs:
                for k, v in kwargs.items():
                    setattr(instance, k, v)
            instance.save()
            return instance


    class VotedEntryVoteForm(forms.ModelForm):  
        class Meta:
            model = voted_entry_vote_class
            fields = ['direction']

        def __init__(self, voted_entry, user, *args, **kwargs):
            super(VotedEntryVoteForm, self).__init__(*args, **kwargs)
            self.voted_entry = voted_entry
            self.user = user

        def save(self):
            data = self.cleaned_data
            entry = self.voted_entry
            if entry.votes.filter(user=self.user).exists():
                instance = entry.votes.get(user=self.user)
                if instance.direction == data['direction']:
                    instance.delete()
                else:
                    instance.direction = data['direction']
                    instance.save()
            else:
                instance = super(VotedEntryVoteForm, self).save(commit=False)
                instance.user = self.user
                instance.entry = self.voted_entry
                instance.save()

            entry._calculate()
            return instance

    class VotedEntryCommentForm(forms.ModelForm):
        class Meta:
            model = voted_entry_comment_class
            fields = ['body']

        def __init__(self, voted_entry, user, *args, **kwargs):
            super(VotedEntryCommentForm, self).__init__(*args, **kwargs)
            self.user = user
            self.voted_entry = voted_entry

        def save(self):
            instance = super(VotedEntryCommentForm, self).save(commit=False)
            instance.user = self.user
            instance.entry = self.voted_entry
            instance.save()
            return instance

    return VotedEntryForm, VotedEntryVoteForm, VotedEntryCommentForm
