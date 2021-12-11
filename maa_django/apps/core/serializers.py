from rest_framework import serializers
from configurateur.models import ConfigMAA, Region, Station

class RegionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'

class RegionsShortSerializer(serializers.ModelSerializer):
    def to_representation(self, value):
        return value.tag
    class Meta:
        model = Region
        fields = ['tag']

class StationsSerializer(serializers.ModelSerializer):
    region = RegionsShortSerializer(read_only=True)
    class Meta:
        model = Station
        fields = '__all__'

class StationConfigMAASerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigMAA
        fields = '__all__'

class ConfigsMAASerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigMAA
        fields = '__all__'


"""
class ParametreMeteoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParametreMeteo
        fields = ('nom')

class ProductionSerializer(serializers.ModelSerializer):
    echeances = serializers.ReadOnlyField()
    produits = serializers.ReadOnlyField()
    #produits = ProduitsSerializer(many=True, read_only=True)

    class Meta:
        fields = (
            'id',
            'nom',
            'lat',
            'lon',
            'timeprod',
            'produits',
            'echeances'
            )
        model = Production

class ProductionsSerializer(serializers.ModelSerializer):
    #echeances = serializers.ReadOnlyField()
    #produits = serializers.ReadOnlyField()
    #produits = ProduitsSerializer(many=True, read_only=True)

    class Meta:
        fields = ('id',
            'nom',
            'lat',
            'lon',
            'url_details',
            #'timeprod',
            #'produits',
            #'echeances'
            )
        model = Production
        """