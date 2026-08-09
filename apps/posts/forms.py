from django import forms
from django.core.exceptions import ValidationError
from .models import Post, Comment


from apps.common.file_validation import validate_uploaded_image

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image', 'video']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all resize-none',
                'placeholder': 'Share your latest project, achievement, or thoughts with the community...',
                'rows': 4
            }),
            'post_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'
            }),
            'visibility': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'
            }),
            'image': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'post-image-input',
                'accept': 'image/*'
            }),
            'video': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'post-video-input',
                'accept': 'video/*'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'post_type' in self.fields:
            self.fields['post_type'].required = False
        if 'visibility' in self.fields:
            self.fields['visibility'].required = False

    def clean_image(self):
        img = self.cleaned_data.get('image')
        if img:
            validate_uploaded_image(img)
        return img

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        image = cleaned_data.get('image')
        video = cleaned_data.get('video')

        if not content and not image and not video:
            raise ValidationError("You must provide either text content, an image, or a video.")
        return cleaned_data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'w-full pl-4 pr-12 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all text-sm',
                'placeholder': 'Write a comment...',
                'autocomplete': 'off'
            })
        }
