from rest_framework import serializers
from .models import Chapter, Question, MCQOption

class MCQOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCQOption
        fields = ['id', 'option_text', 'is_correct', 'created_at']
        read_only_fields = ['id', 'created_at']

class QuestionSerializer(serializers.ModelSerializer):
    options = MCQOptionSerializer(many=True, read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'chapter', 'chapter_name', 'question_text', 'options', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class QuestionListSerializer(serializers.ModelSerializer):
    options_count = serializers.SerializerMethodField()
    correct_answers_count = serializers.SerializerMethodField()
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'chapter', 'chapter_name', 'question_text', 'options_count', 'correct_answers_count', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_options_count(self, obj):
        return obj.options.count()
    
    def get_correct_answers_count(self, obj):
        return obj.options.filter(is_correct=True).count()

class ChapterSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_logo = serializers.SerializerMethodField()
    questions_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Chapter
        fields = [
            'id', 'department', 'department_name', 'department_logo',
            'name', 'subtitle', 'description', 'image', 'image_url',
            'questions_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_department_logo(self, obj):
        if obj.department.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.department.logo.url)
            return obj.department.logo.url
        return None
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_questions_count(self, obj):
        return obj.questions.count()

class ChapterDetailSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_logo = serializers.SerializerMethodField()
    questions = QuestionListSerializer(many=True, read_only=True)
    questions_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Chapter
        fields = [
            'id', 'department', 'department_name', 'department_logo',
            'name', 'subtitle', 'description', 'image', 'image_url',
            'questions_count', 'questions', 'created_at', 'updated_at'
        ]
    
    def get_department_logo(self, obj):
        if obj.department.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.department.logo.url)
            return obj.department.logo.url
        return None
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_questions_count(self, obj):
        return obj.questions.count()

class ChapterCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ['name', 'subtitle', 'description', 'image']

class QuestionCreateSerializer(serializers.ModelSerializer):
    options = MCQOptionSerializer(many=True)
    
    class Meta:
        model = Question
        fields = ['chapter', 'question_text', 'options']
    
    def validate_options(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("A question must have at least 2 options")
        if len(value) > 5:
            raise serializers.ValidationError("A question can have maximum 5 options")
        
        # Check if at least one option is correct
        has_correct = any(option.get('is_correct', False) for option in value)
        if not has_correct:
            raise serializers.ValidationError("At least one option must be marked as correct")
        
        return value
    
    def create(self, validated_data):
        options_data = validated_data.pop('options')
        question = Question.objects.create(**validated_data)
        
        for option_data in options_data:
            MCQOption.objects.create(question=question, **option_data)
        
        return question
    
    def update(self, instance, validated_data):
        options_data = validated_data.pop('options', None)
        
        instance.question_text = validated_data.get('question_text', instance.question_text)
        instance.chapter = validated_data.get('chapter', instance.chapter)
        instance.save()
        
        if options_data is not None:
            # Delete existing options
            instance.options.all().delete()
            
            # Create new options
            for option_data in options_data:
                MCQOption.objects.create(question=instance, **option_data)
        
        return instance
    


class QuestionForTestSerializer(serializers.ModelSerializer):
    """
    Serializer for questions during test (without correct answer)
    """
    options = MCQOptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'options']