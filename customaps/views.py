from rest_framework import viewsets, status
from rest_framework.viewsets import mixins 
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Folder, Map
from .serializers import FolderSerializer, MapSerializer,SingleFolderSerializer


class FolderViewSet(viewsets.GenericViewSet,mixins.RetrieveModelMixin,mixins.CreateModelMixin,mixins.UpdateModelMixin):
    serializer_class = SingleFolderSerializer
    permission_classes = [AllowAny]
    queryset=Folder.objects.all()
    username=""
  

    def get_queryset(self):
        self.username=self.request.query_params.get('username')
        return Folder.objects.filter(username=self.username)
  
    def retrieve(self, request, pk):
        ''' spec , si pk == -1 : on charge le folder root du user, nommé root. si pas de root, on le crée        
        '''        
        self.username=self.request.query_params.get('username')
        pkey=int(pk)
        print(f"received customaps folder query to retreive folder: {pk} for user {self.username}")
        if not  self.username:
            return Response({'error': 'Invalid username'}, status=status.HTTP_400_BAD_REQUEST)
        if pkey == -1:
           try:
                instance=Folder.objects.get(username=self.username,name='root')
                return Response(FolderSerializer(instance).data, status=status.HTTP_201_CREATED)
           except:
               newUserFolder=Folder(name='root',username=self.username)
               newUserFolder.save()
               return Response(FolderSerializer(newUserFolder).data, status=status.HTTP_201_CREATED)   
        else:
            try:
                instance=Folder.objects.get(username=self.username,id=pkey)
                return Response(FolderSerializer(instance).data, status=status.HTTP_201_CREATED)
            except:
                return Response({'error': 'Invalid folder id'}, status=status.HTTP_400_BAD_REQUEST)
    def create(self, request, *args, **kwargs):   
        result= super().create(request, *args, **kwargs)
        if result.status_code == status.HTTP_201_CREATED:
            parent=Folder.objects.get(id=result.data["parent"])
            
            result.data["parent"]=FolderSerializer(parent).data
            return Response(data=result.data,status=status.HTTP_201_CREATED)
        else:
            return result
    def destroy(self, request, *args, **kwargs): 
        instance = self.get_object()
        
        depth=0
        self.too_deep = False
        def recurse_remove_folder_and_maps(dad,depth):
            if depth > 5:
                self.too_deep=True
                return 
            sub_folders=Folder.objects.filter(parent=dad.id)
            if sub_folders.count() >0:
                for sub in sub_folders.all():
                    recurse_remove_folder_and_maps(sub,depth+1)
            Map.objects.filter(folder=dad.id).delete()
            if not self.too_deep:
                indent=""
                for i in range(0,depth):
                    indent=f"{indent}    "
                print(f"{indent} removing folder: {dad.name}")
                dad.delete()   
        if instance is not None:
            recurse_remove_folder_and_maps(instance,depth+1)
            folder=Folder.objects.get(id=instance.parent.id)
            if not self.too_deep:
                return Response(data=FolderSerializer(folder).data,status=status.HTTP_201_CREATED)
            else:
                return Response(data={"error":"too deep sub folder tree (<4) , please clean before removing all"},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(data={"error":"Target Folder Not Found"},status=status.HTTP_400_BAD_REQUEST)

   

class MapViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Map CRUD operations based on username.
    """
    serializer_class = MapSerializer
    permission_classes = [AllowAny]  # a changer
    queryset=Map.objects.all()
    username=""
    def get_queryset(self):
        self.username=self.request.query_params.get('username')
        if not self.username:
            return Map.objects.none() 
        return Map.objects.filter(username=self.username)
    def create(self, request, *args, **kwargs):   
        result= super().create(request, *args, **kwargs)
        if result.status_code == status.HTTP_201_CREATED:
            folder=Folder.objects.get(id=result.data["folder"])
            return Response(data=FolderSerializer(folder).data,status=status.HTTP_201_CREATED)
        else:
            return result
    def update(self, request, *args, **kwargs):   
        result= super().update(request, *args, **kwargs)
        if result.status_code in [ status.HTTP_200_OK,status.HTTP_201_CREATED]:
            folder=Folder.objects.get(id=result.data["folder"])
            return Response(data=FolderSerializer(folder).data,status=status.HTTP_201_CREATED)
        else:
            return result
    def destroy(self, request, *args, **kwargs): 
        instance = self.get_object()  
        if instance is not None:
            result= super().destroy(request, *args, **kwargs)
            if result.status_code in [ status.HTTP_200_OK,status.HTTP_201_CREATED,status.HTTP_204_NO_CONTENT]:
                folder=Folder.objects.get(id=instance.folder.id)
                return Response(data=FolderSerializer(folder).data,status=status.HTTP_201_CREATED)
            else:
                return result
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    
