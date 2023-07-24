from django.contrib import admin
from .models import Category, Post, Location, Comment

admin.site.empty_value_display = 'Не задано'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'description',
        'is_published',
    )
    list_editable = (
        'is_published',
    )


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        'name',
    )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'text',
        'author',
        'location',
        'category',
        'is_published',
    )
    list_editable = (
        'category',
        'is_published',

    )
    search_fields = ('title',)
    list_display_links = ('title',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'post', 'created_at', 'author')
    search_fields = ('text',)
