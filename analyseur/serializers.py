from rest_framework import serializers
from analyseur.models import EnvoiMAA
from configurateur.models import ConfigMAA, Station

class EnvoiMAASerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvoiMAA
        fields = (
            'numero', 'date_envoi', 'date_debut', 'date_fin',
            'entete_transmet', 'message'
            )

class ConfigMAASerializer(serializers.ModelSerializer):
    maa_emis = EnvoiMAASerializer(many=True)
    class Meta:
        model = ConfigMAA
        fields = (
            'type_maa', 'seuil', 'auto', 'maa_emis',
            )

class StationSerializer(serializers.ModelSerializer):
    configmaa = ConfigMAASerializer(many=True)

    class Meta:
        model = Station
        fields = ( 'oaci', 'nom', 'configmaa')
    

"""class RegionsShortSerializer(serializers.ModelSerializer):
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