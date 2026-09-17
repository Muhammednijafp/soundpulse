from rest_framework import serializers

class TrackSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    artist = serializers.CharField(allow_blank=True, required=False)
    channelUrl = serializers.CharField(allow_null=True, required=False)
    duration = serializers.IntegerField(required=False)
    durationFormatted = serializers.CharField(required=False)
    views = serializers.IntegerField(required=False)
    viewsFormatted = serializers.CharField(required=False)
    thumbnail = serializers.CharField(allow_blank=True, required=False)
    url = serializers.CharField()
    isVerified = serializers.BooleanField(default=False)

class SearchResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    query = serializers.CharField()
    count = serializers.IntegerField()
    tracks = TrackSerializer(many=True)

class TrackInfoRequestSerializer(serializers.Serializer):
    url = serializers.CharField(required=False, allow_blank=True)
    id = serializers.CharField(required=False, allow_blank=True)

class TrackDetailSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    artist = serializers.CharField()
    album = serializers.CharField(allow_null=True, required=False)
    channel = serializers.CharField()
    duration = serializers.IntegerField()
    durationFormatted = serializers.CharField()
    views = serializers.IntegerField()
    viewsFormatted = serializers.CharField()
    thumbnail = serializers.CharField()
    uploadDate = serializers.CharField(allow_null=True, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    url = serializers.CharField()
    formatsAvailable = serializers.ListField(child=serializers.CharField())

class TrendingCategorySerializer(serializers.Serializer):
    category = serializers.CharField()
    query = serializers.CharField()
    tag = serializers.CharField()

