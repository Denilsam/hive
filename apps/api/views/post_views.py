from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from apps.posts.models import Post, Like, Comment, SavedPost
from apps.connections.models import Connection, Follow
from apps.api.serializers import PostSerializer, CommentSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class PostListCreateView(APIView):
    """
    GET /api/v1/posts/ (Paginated feed - Public posts visible to unauthenticated, personalized to authenticated)
    POST /api/v1/posts/ (Create post - Requires authentication)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            following_ids = list(Follow.objects.filter(follower=user).values_list('following_id', flat=True))
            connected_ids_1 = list(Connection.objects.filter(user1=user).values_list('user2_id', flat=True))
            connected_ids_2 = list(Connection.objects.filter(user2=user).values_list('user1_id', flat=True))
            network_ids = set(following_ids + connected_ids_1 + connected_ids_2 + [user.id])

            posts = Post.objects.filter(
                Q(visibility=Post.Visibility.PUBLIC) |
                Q(author=user) |
                Q(visibility=Post.Visibility.CONNECTIONS, author_id__in=network_ids)
            )
        else:
            posts = Post.objects.filter(visibility=Post.Visibility.PUBLIC)

        posts = posts.select_related('author', 'author__profile').annotate(
            likes_count_annotated=Count('likes', distinct=True),
            comments_count_annotated=Count('comments', distinct=True)
        ).order_by('-created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(posts, request)

        if page is not None:
            if user.is_authenticated:
                page_post_ids = [p.id for p in page]
                user_likes = set(Like.objects.filter(post_id__in=page_post_ids, user=user).values_list('post_id', flat=True))
                user_saves = set(SavedPost.objects.filter(post_id__in=page_post_ids, user=user).values_list('post_id', flat=True))

                for post in page:
                    post._prefetched_user_likes = {user.id} if post.id in user_likes else set()
                    post._prefetched_user_saves = {user.id} if post.id in user_saves else set()

            serializer = PostSerializer(page, many=True, context={'request': request, 'request_user': user})
            return paginator.get_paginated_response(serializer.data)

        serializer = PostSerializer(posts, many=True, context={'request': request, 'request_user': user})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = PostSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        post = serializer.save(author=request.user)
        response_serializer = PostSerializer(post, context={'request': request, 'request_user': request.user})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    """
    GET /api/v1/posts/<id>/ (View post detail)
    PATCH /api/v1/posts/<id>/ (Edit post - Author only)
    DELETE /api/v1/posts/<id>/ (Delete post - Author only)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, post_id):
        return get_object_or_404(
            Post.objects.select_related('author', 'author__profile').annotate(
                likes_count_annotated=Count('likes', distinct=True),
                comments_count_annotated=Count('comments', distinct=True)
            ),
            id=post_id
        )

    def get(self, request, post_id, *args, **kwargs):
        post = self.get_object(post_id)
        # Check visibility
        if post.visibility == Post.Visibility.PRIVATE and post.author != request.user:
            return Response({"detail": "You do not have permission to view this post."}, status=status.HTTP_403_FORBIDDEN)
        elif post.visibility == Post.Visibility.CONNECTIONS and post.author != request.user:
            if not request.user.is_authenticated:
                return Response({"detail": "Authentication required to view this post."}, status=status.HTTP_401_UNAUTHORIZED)
            # Check connection
            is_connected = Connection.objects.filter(
                Q(user1=request.user, user2=post.author) | Q(user1=post.author, user2=request.user)
            ).exists() or Follow.objects.filter(follower=request.user, following=post.author).exists()
            if not is_connected:
                return Response({"detail": "You do not have permission to view this post."}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostSerializer(post, context={'request': request, 'request_user': request.user})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, post_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        post = self.get_object(post_id)
        if post.author != request.user:
            return Response({"detail": "You do not have permission to edit this post."}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostSerializer(post, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        response_serializer = PostSerializer(post, context={'request': request, 'request_user': request.user})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, post_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        post = self.get_object(post_id)
        if post.author != request.user:
            return Response({"detail": "You do not have permission to delete this post."}, status=status.HTTP_403_FORBIDDEN)

        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id, *args, **kwargs):
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(post=post, user=request.user)

        if not created:
            like.delete()
            is_liked = False
        else:
            is_liked = True

        like_count = post.likes.count()
        return Response({
            "is_liked": is_liked,
            "like_count": like_count
        }, status=status.HTTP_200_OK)


class PostSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id, *args, **kwargs):
        post = get_object_or_404(Post, id=post_id)
        saved, created = SavedPost.objects.get_or_create(post=post, user=request.user)

        if not created:
            saved.delete()
            is_saved = False
        else:
            is_saved = True

        return Response({
            "is_saved": is_saved
        }, status=status.HTTP_200_OK)


class PostCommentListCreateView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request, post_id, *args, **kwargs):
        post = get_object_or_404(Post, id=post_id)
        comments = Comment.objects.filter(post=post).select_related('user', 'user__profile')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(comments, request)

        if page is not None:
            serializer = CommentSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, post_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        post = get_object_or_404(Post, id=post_id)
        content = request.data.get('content', '').strip()

        if not content:
            return Response({"content": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        comment = Comment.objects.create(post=post, user=request.user, content=content)
        serializer = CommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
