from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from apps.marketplace.models import Collaboration, CollaborationApplication
from apps.api.serializers import CollaborationSerializer, CollaborationApplicationSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class CollaborationListCreateView(APIView):
    """
    GET /api/v1/marketplace/collaborations/ & /api/v1/opportunities/ (List open opportunities - Public)
    POST /api/v1/marketplace/collaborations/ & /api/v1/opportunities/ (Create opportunity - Requires auth)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        collaborations = Collaboration.objects.filter(status=Collaboration.Status.OPEN).select_related('creator', 'creator__profile').prefetch_related('required_skills__skill')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(collaborations, request)

        if page is not None:
            serializer = CollaborationSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = CollaborationSerializer(collaborations, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = CollaborationSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        collaboration = serializer.save(creator=request.user)
        response_serializer = CollaborationSerializer(collaboration, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CollaborationDetailView(APIView):
    """
    GET /api/v1/marketplace/collaborations/<id>/ & /api/v1/opportunities/<id>/
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, id, *args, **kwargs):
        collaboration = get_object_or_404(
            Collaboration.objects.select_related('creator', 'creator__profile').prefetch_related('required_skills__skill'),
            id=id
        )
        serializer = CollaborationSerializer(collaboration, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CollaborationApplyView(APIView):
    """
    POST /api/v1/marketplace/collaborations/<id>/apply/ & /api/v1/opportunities/<id>/apply/
    Apply to a collaboration opportunity. Requires authentication.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        collaboration = get_object_or_404(Collaboration, id=id)

        if collaboration.creator == request.user:
            return Response({"detail": "You cannot apply to your own project opportunity."}, status=status.HTTP_400_BAD_REQUEST)

        message = request.data.get('message', '').strip()
        if not message:
            return Response({"message": ["Application message is required."]}, status=status.HTTP_400_BAD_REQUEST)

        existing_app = CollaborationApplication.objects.filter(collaboration=collaboration, applicant=request.user).first()
        if existing_app:
            return Response({"detail": "You have already applied to this opportunity."}, status=status.HTTP_400_BAD_REQUEST)

        app = CollaborationApplication.objects.create(collaboration=collaboration, applicant=request.user, message=message)
        serializer = CollaborationApplicationSerializer(app, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyApplicationsListView(APIView):
    """
    GET /api/v1/marketplace/my-applications/ & /api/v1/opportunities/my-applications/
    List authenticated user's applications. Requires authentication.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        applications = CollaborationApplication.objects.filter(applicant=request.user).select_related('collaboration', 'applicant')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(applications, request)

        if page is not None:
            serializer = CollaborationApplicationSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = CollaborationApplicationSerializer(applications, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
