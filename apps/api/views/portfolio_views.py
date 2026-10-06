from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from apps.portfolio.models import Project
from apps.api.serializers import ProjectSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class ProjectListCreateView(APIView):
    """
    GET /api/v1/portfolio/projects/ (Public projects accessible unauthenticated)
    POST /api/v1/portfolio/projects/ (Create project requires auth)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id')
        projects = Project.objects.select_related('owner', 'owner__profile').prefetch_related('technologies', 'images')

        if user_id:
            if request.user.is_authenticated and str(request.user.id) == str(user_id):
                projects = projects.filter(owner_id=user_id)
            else:
                projects = projects.filter(owner_id=user_id, visibility=Project.Visibility.PUBLIC)
        else:
            projects = projects.filter(visibility=Project.Visibility.PUBLIC)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(projects, request)

        if page is not None:
            serializer = ProjectSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = ProjectSerializer(projects, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = ProjectSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        project = serializer.save(owner=request.user)
        response_serializer = ProjectSerializer(project, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):
    """
    GET /api/v1/portfolio/projects/<id>/
    PATCH /api/v1/portfolio/projects/<id>/
    DELETE /api/v1/portfolio/projects/<id>/
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, project_id):
        return get_object_or_404(
            Project.objects.select_related('owner', 'owner__profile').prefetch_related('technologies', 'images'),
            id=project_id
        )

    def get(self, request, project_id, *args, **kwargs):
        project = self.get_object(project_id)
        if project.visibility == Project.Visibility.PRIVATE and project.owner != request.user:
            return Response({"detail": "You do not have permission to view this project."}, status=status.HTTP_403_FORBIDDEN)
        elif project.visibility == Project.Visibility.CONNECTIONS and project.owner != request.user:
            if not request.user.is_authenticated:
                return Response({"detail": "Authentication required to view this project."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ProjectSerializer(project, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, project_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        project = self.get_object(project_id)
        if project.owner != request.user:
            return Response({"detail": "You do not have permission to edit this project."}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProjectSerializer(project, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        response_serializer = ProjectSerializer(project, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, project_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        project = self.get_object(project_id)
        if project.owner != request.user:
            return Response({"detail": "You do not have permission to delete this project."}, status=status.HTTP_403_FORBIDDEN)

        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
