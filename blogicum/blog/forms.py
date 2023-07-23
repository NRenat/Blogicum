from django import forms
from .models import Post, User, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        widgets = {
            'pub_date': forms.DateInput(attrs={'type': 'date'})
        }
        exclude = ('created_at', 'author', 'is_published')


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name')


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text', )
