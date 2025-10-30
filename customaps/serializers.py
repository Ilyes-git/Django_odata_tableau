from rest_framework import serializers
from rest_framework.serializers import ALL_FIELDS
from rest_flex_fields import FlexFieldsModelSerializer

from .models import Folder, Map


class MapSerializer(FlexFieldsModelSerializer):
    type=serializers.ReadOnlyField(default='userMap')
    class Meta:
        model = Map
        fields = ['id', 'name', 'data', 'folder' ,'username','type', 'created_at','updated_at']
    '''    
    def create(self, validated_data):
        print(validated_data)
        pass
    '''
        
class SingleFolderSerializer(FlexFieldsModelSerializer):
    type=serializers.ReadOnlyField(default='folder')
    class Meta:
        model = Folder
        fields = ['id', 'name', 'parent', 'username','type', 'created_at','updated_at']  





class FolderSerializer(FlexFieldsModelSerializer):
    path= serializers.SerializerMethodField()
    type=serializers.ReadOnlyField(default='folder')
    class Meta:
        model = Folder
        fields = ALL_FIELDS
        expandable_fields = {
            'subfolders': (SingleFolderSerializer, {'many': True}),
            'maps': (MapSerializer, {'many': True}),
            'parent': (SingleFolderSerializer, {'many': False})
        }


    def get_path(self,obj):
        def add_path(depth,folder):
            if folder.name != "root" and depth < 10:
                depth=depth+1
                try:
                    parent=Folder.objects.get(id=folder.parent.id) 
                    return f" {add_path(depth+1,parent)} {folder.name} /"               
                    
                except:
                    return f" {folder.name} /"
            else:
                return f"/"
        depth=0
        return add_path(depth,obj) 
        


