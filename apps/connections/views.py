from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import get_user_model

from .models import Follow, ConnectionRequest, Connection
from apps.profiles.models import Skill
from apps.chat.models import Conversation

User = get_user_model()


class NetworkDiscoveryView(LoginRequiredMixin, View):
    template_name = 'connections/network.html'

    def get(self, request):
        # Exclude self, superusers, and inactive users
        users_list = User.objects.exclude(id=request.user.id).filter(
            is_active=True,
            is_superuser=False
        ).select_related('profile').order_by('-id')

        # --- Keyword Search Filter ---
        q = request.GET.get('q', '').strip()
        if q:
            users_list = users_list.filter(
                models.Q(first_name__icontains=q) |
                models.Q(last_name__icontains=q) |
                models.Q(username__icontains=q) |
                models.Q(profile__headline__icontains=q) |
                models.Q(profile__bio__icontains=q)
            )

        # --- Location Filter ---
        location_query = request.GET.get('location', '').strip()
        if location_query:
            users_list = users_list.filter(
                profile__location__icontains=location_query
            )

        # --- Account Type Filter ---
        account_type_query = request.GET.get('account_type', '').strip()
        if account_type_query:
            users_list = users_list.filter(
                account_type=account_type_query
            )

        # --- Paginate Discovery Results ---
        paginator = Paginator(users_list, 12)  # 12 cards per page
        page = request.GET.get('page')
        try:
            users = paginator.page(page)
        except PageNotAnInteger:
            users = paginator.page(1)
        except EmptyPage:
            users = paginator.page(paginator.num_pages)

        page_user_ids = [u.id for u in users]

        # --- Fetch current user's follow states ---
        following_ids = set(
            Follow.objects.filter(follower=request.user, following_id__in=page_user_ids).values_list('following_id', flat=True)
        )

        follower_counts = dict(
            Follow.objects.filter(following_id__in=page_user_ids)
            .values('following_id')
            .annotate(cnt=models.Count('id'))
            .values_list('following_id', 'cnt')
        )
        following_counts = dict(
            Follow.objects.filter(follower_id__in=page_user_ids)
            .values('follower_id')
            .annotate(cnt=models.Count('id'))
            .values_list('follower_id', 'cnt')
        )

        for u in users:
            u.is_following = u.id in following_ids
            u.followers_count = follower_counts.get(u.id, 0)
            u.following_count = following_counts.get(u.id, 0)

        return render(request, self.template_name, {
            'users': users,
            'page_obj': users,
            'query': q,
            'selected_location': location_query,
            'selected_account_type': account_type_query,
            'following_ids': following_ids,
        })


class FollowToggleView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        
        is_ajax = (
            request.headers.get('x-requested-with') == 'XMLHttpRequest'
            or 'application/json' in request.headers.get('accept', '')
            or request.content_type == 'application/json'
        )

        if target_user == request.user:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'You cannot follow yourself.'}, status=400)
            messages.error(request, 'You cannot follow yourself.')
            return redirect(request.META.get('HTTP_REFERER', 'connections:network'))

        follow = Follow.objects.filter(follower=request.user, following=target_user)
        if follow.exists():
            follow.delete()
            following = False
        else:
            Follow.objects.create(follower=request.user, following=target_user)
            following = True

        follower_count = Follow.objects.filter(following=target_user).count()
        following_count = Follow.objects.filter(follower=request.user).count()

        if is_ajax:
            return JsonResponse({
                'success': True,
                'following': following,
                'follower_count': follower_count,
                'following_count': following_count
            })
        
        messages.success(request, f"{'Followed' if following else 'Unfollowed'} {target_user.first_name}.")
        return redirect(request.META.get('HTTP_REFERER', 'connections:network'))


class SendRequestView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        receiver = get_object_or_404(User, id=user_id)
        if receiver == request.user:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'You cannot send a connection request to yourself.'}, status=400)
            messages.error(request, 'You cannot send a connection request to yourself.')
            return redirect(request.META.get('HTTP_REFERER', 'connections:network'))

        # Create or update to pending
        req, created = ConnectionRequest.objects.get_or_create(
            sender=request.user,
            receiver=receiver,
            defaults={'status': ConnectionRequest.Status.PENDING}
        )
        if not created and req.status != ConnectionRequest.Status.PENDING:
            req.status = ConnectionRequest.Status.PENDING
            req.save()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Connection request sent successfully!'
            })

        messages.success(request, f"Connection request sent to {receiver.first_name}.")
        return redirect(request.META.get('HTTP_REFERER', 'connections:network'))


class AcceptRequestView(LoginRequiredMixin, View):
    def post(self, request, pk):
        req = get_object_or_404(
            ConnectionRequest, pk=pk, receiver=request.user, status=ConnectionRequest.Status.PENDING
        )
        req.status = ConnectionRequest.Status.ACCEPTED
        req.save()

        # Create Connection (Ensure user1_id < user2_id order)
        u1, u2 = (req.sender, req.receiver) if req.sender.id < req.receiver.id else (req.receiver, req.sender)
        Connection.objects.get_or_create(user1=u1, user2=u2)

        # Automatically follow each other
        Follow.objects.get_or_create(follower=req.sender, following=req.receiver)
        Follow.objects.get_or_create(follower=req.receiver, following=req.sender)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        messages.success(request, f"You are now connected with {req.sender.first_name}!")
        return redirect('connections:requests')


class RejectRequestView(LoginRequiredMixin, View):
    def post(self, request, pk):
        req = get_object_or_404(
            ConnectionRequest, pk=pk, receiver=request.user, status=ConnectionRequest.Status.PENDING
        )
        req.status = ConnectionRequest.Status.REJECTED
        req.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        messages.info(request, "Connection request ignored.")
        return redirect('connections:requests')


class CancelRequestView(LoginRequiredMixin, View):
    def post(self, request, pk):
        req = get_object_or_404(
            ConnectionRequest, pk=pk, sender=request.user, status=ConnectionRequest.Status.PENDING
        )
        req.status = ConnectionRequest.Status.CANCELLED
        req.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        messages.info(request, "Connection request cancelled.")
        return redirect('connections:requests')


class RemoveConnectionView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        target = get_object_or_404(User, id=user_id)
        u1, u2 = (request.user, target) if request.user.id < target.id else (target, request.user)
        
        Connection.objects.filter(user1=u1, user2=u2).delete()

        # Remove follow relationships
        Follow.objects.filter(follower=request.user, following=target).delete()
        Follow.objects.filter(follower=target, following=request.user).delete()

        # Update ConnectionRequest status to cancelled so they can request again
        ConnectionRequest.objects.filter(
            models.Q(sender=request.user, receiver=target) |
            models.Q(sender=target, receiver=request.user)
        ).update(status=ConnectionRequest.Status.CANCELLED)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        messages.success(request, f"Removed connection with {target.first_name}.")
        return redirect('connections:network')


class FollowersListView(LoginRequiredMixin, View):
    template_name = 'connections/followers.html'

    def get(self, request, username=None):
        if username:
            profile_user = get_object_or_404(User, username=username)
        else:
            profile_user = request.user

        follows = Follow.objects.filter(following=profile_user, follower__is_superuser=False).select_related('follower', 'follower__profile')
        followers = [f.follower for f in follows]
        
        # Prepopulate relationship checks relative to request.user (the logged-in viewer!)
        following_ids = set(
            Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        )
        follower_counts = dict(
            Follow.objects.filter(following_id__in=[u.id for u in followers])
            .values('following_id').annotate(cnt=models.Count('id')).values_list('following_id', 'cnt')
        )
        following_counts = dict(
            Follow.objects.filter(follower_id__in=[u.id for u in followers])
            .values('follower_id').annotate(cnt=models.Count('id')).values_list('follower_id', 'cnt')
        )

        for u in followers:
            u.is_following = u.id in following_ids
            u.followers_count = follower_counts.get(u.id, 0)
            u.following_count = following_counts.get(u.id, 0)

        return render(request, self.template_name, {
            'profile_user': profile_user,
            'followers': followers,
            'is_own_list': (request.user == profile_user)
        })


class FollowingListView(LoginRequiredMixin, View):
    template_name = 'connections/following.html'

    def get(self, request, username=None):
        if username:
            profile_user = get_object_or_404(User, username=username)
        else:
            profile_user = request.user

        follows = Follow.objects.filter(follower=profile_user, following__is_superuser=False).select_related('following', 'following__profile')
        following = [f.following for f in follows]
        
        # Prepopulate relationship checks relative to request.user (the logged-in viewer!)
        following_ids = set(
            Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        )
        follower_counts = dict(
            Follow.objects.filter(following_id__in=[u.id for u in following])
            .values('following_id').annotate(cnt=models.Count('id')).values_list('following_id', 'cnt')
        )
        following_counts = dict(
            Follow.objects.filter(follower_id__in=[u.id for u in following])
            .values('follower_id').annotate(cnt=models.Count('id')).values_list('follower_id', 'cnt')
        )

        for u in following:
            u.is_following = u.id in following_ids
            u.followers_count = follower_counts.get(u.id, 0)
            u.following_count = following_counts.get(u.id, 0)

        return render(request, self.template_name, {
            'profile_user': profile_user,
            'following': following,
            'is_own_list': (request.user == profile_user)
        })


class RequestsListView(LoginRequiredMixin, View):
    template_name = 'connections/requests.html'

    def get(self, request):
        received_requests = ConnectionRequest.objects.filter(
            receiver=request.user, status=ConnectionRequest.Status.PENDING
        ).select_related('sender', 'sender__profile')
        
        sent_requests = ConnectionRequest.objects.filter(
            sender=request.user, status=ConnectionRequest.Status.PENDING
        ).select_related('receiver', 'receiver__profile')

        return render(request, self.template_name, {
            'received_requests': received_requests,
            'sent_requests': sent_requests
        })
