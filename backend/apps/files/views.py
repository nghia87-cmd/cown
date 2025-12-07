from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from .models import UploadedFile
from .serializers import UploadedFileSerializer, FileUploadSerializer


class UploadedFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing file uploads
    
    Endpoints:
    - GET /api/files/ - List user's uploaded files
    - POST /api/files/ - Upload a new file
    - GET /api/files/{id}/ - Get file details
    - DELETE /api/files/{id}/ - Delete a file
    - POST /api/files/upload/ - Alternative upload endpoint
    """
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Get files uploaded by current user"""
        if getattr(self, 'swagger_fake_view', False):
            return UploadedFile.objects.none()
        
        user = self.request.user
        queryset = UploadedFile.objects.filter(uploaded_by=user)
        
        # Filter by file type
        file_type = self.request.query_params.get('file_type')
        if file_type:
            queryset = queryset.filter(file_type=file_type)
        
        # Search by filename
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(original_filename__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Upload a file"""
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uploaded_file = serializer.validated_data['file']
        file_type = serializer.validated_data['file_type']
        description = serializer.validated_data.get('description', '')
        is_public = serializer.validated_data.get('is_public', False)
        
        # Create UploadedFile instance
        file_obj = UploadedFile.objects.create(
            uploaded_by=request.user,
            file=uploaded_file,
            file_type=file_type,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            mime_type=uploaded_file.content_type,
            description=description,
            is_public=is_public
        )
        
        # Return file details
        response_serializer = UploadedFileSerializer(file_obj, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Alternative endpoint for uploading files"""
        return self.create(request)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Get download URL for a file"""
        file_obj = self.get_object()
        return Response({
            'url': request.build_absolute_uri(file_obj.file.url),
            'filename': file_obj.original_filename,
            'size': file_obj.file_size,
            'type': file_obj.mime_type
        })
    
    @action(detail=False, methods=['get'])
    def resumes(self, request):
        """Get all resume files for current user"""
        resumes = UploadedFile.objects.filter(
            uploaded_by=request.user,
            file_type='RESUME'
        ).order_by('-uploaded_at')
        
        serializer = self.get_serializer(resumes, many=True)
        return Response(serializer.data)
