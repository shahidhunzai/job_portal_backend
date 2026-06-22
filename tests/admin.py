from django.contrib import admin
from .models import Chapter, Question, MCQOption

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'subtitle', 'created_at']
    list_filter = ['department', 'created_at']
    search_fields = ['name', 'subtitle', 'description', 'department__name']
    readonly_fields = ['created_at', 'updated_at']

class MCQOptionInline(admin.TabularInline):
    model = MCQOption
    extra = 4
    max_num = 5

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'chapter', 'created_at']
    list_filter = ['chapter', 'created_at']
    search_fields = ['question_text', 'chapter__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [MCQOptionInline]

@admin.register(MCQOption)
class MCQOptionAdmin(admin.ModelAdmin):
    list_display = ['option_text', 'question', 'is_correct']
    list_filter = ['is_correct', 'created_at']
    search_fields = ['option_text', 'question__question_text']