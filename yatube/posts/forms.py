from django.forms import ModelForm

from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ["text", "group", "image"]
        lables = {"text": "текст поста", }
        help_text = {
            "text": "Текст",
            "group": "Группа",
            "image": "Картинка"
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
