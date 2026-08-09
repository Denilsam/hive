from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse

from .models import Post, Like, Comment, SavedPost
from .forms import PostForm, CommentForm


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

class FeedView(LoginRequiredMixin, View):
    template_name = 'posts/feed.html'

    def get(self, request):
        # Retrieve all posts with optimized selects and prefetches
        posts_list = Post.objects.all().select_related(
            'author', 'author__profile'
        ).prefetch_related(
            'likes', 'comments', 'saved_by'
        )
        
        # Pagination (10 posts per page)
        paginator = Paginator(posts_list, 10)
        page = request.GET.get('page')
        try:
            posts = paginator.page(page)
        except PageNotAnInteger:
            posts = paginator.page(1)
        except EmptyPage:
            posts = paginator.page(paginator.num_pages)
        
        # User liked and saved post sets for UI states
        liked_post_ids = set(request.user.likes.values_list('post_id', flat=True))
        saved_post_ids = set(request.user.saved_posts.values_list('post_id', flat=True))
        
        post_form = PostForm()
        comment_form = CommentForm()

        return render(request, self.template_name, {
            'posts': posts,
            'page_obj': posts,
            'liked_post_ids': liked_post_ids,
            'saved_post_ids': saved_post_ids,
            'post_form': post_form,
            'comment_form': comment_form
        })


class PostCreateView(LoginRequiredMixin, View):
    template_name = 'posts/create_post.html'

    def get(self, request):
        form = PostForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Your post has been shared successfully!")
            return redirect('posts:feed')
        return render(request, self.template_name, {'form': form})


class PostDetailView(DetailView):
    model = Post
    template_name = 'posts/post_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        
        # Engagement context
        context['comments'] = post.comments.select_related('user', 'user__profile').all()
        context['comment_form'] = CommentForm()
        
        # Check if user is authenticated and gather liked/saved info
        if self.request.user.is_authenticated:
            context['liked_post_ids'] = set(self.request.user.likes.values_list('post_id', flat=True))
            context['saved_post_ids'] = set(self.request.user.saved_posts.values_list('post_id', flat=True))
        else:
            context['liked_post_ids'] = set()
            context['saved_post_ids'] = set()
            
        return context


# --- AJAX Views responding in JSON ---

class PostLikeToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
            
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': post.likes.count()
        })


class PostSaveToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        saved_post, created = SavedPost.objects.get_or_create(user=request.user, post=post)
        
        if not created:
            saved_post.delete()
            saved = False
        else:
            saved = True
            
        return JsonResponse({
            'success': True,
            'saved': saved
        })


class CommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        form = CommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.save()
            
            avatar_url = comment.user.profile.profile_image.url if comment.user.profile.profile_image else ""
            
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'author_name': f"{comment.user.first_name} {comment.user.last_name}",
                    'author_username': comment.user.username,
                    'author_avatar': avatar_url,
                    'content': comment.content,
                    'created_at': comment.created_at.strftime('%b %d, %Y, %I:%M %p'),
                    'delete_url': reverse('posts:comment_delete', kwargs={'pk': comment.pk})
                }
            })
            
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })


class CommentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk, user=request.user)
        comment.delete()
        return JsonResponse({
            'success': True
        })


class PostDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk, author=request.user)
        post.delete()
        messages.success(request, "Post deleted successfully!")
        return redirect('posts:feed')
